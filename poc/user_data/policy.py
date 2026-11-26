"""Policy layer: use the labels to build the SQL that deletes or downloads a user's data.

On app startup all the user-linked tables are walked once (see
``events.check_user_data``) to build the statements. Deleting or downloading a
user only runs them with the user's id.

What happens to a user's rows, for each table policy and column label:

+-----------------------+--------------+-----------------------------+-------------------------------+
| Table policy          | Column label | On delete                   | On download                   |
+=======================+==============+=============================+===============================+
| ``"delete"``          | any          | The whole row is deleted.   | The whole row is exported.    |
+-----------------------+--------------+-----------------------------+-------------------------------+
| ``"anonymize"``       | ``"ref"``    | Kept. Used to find the rows.| Exported.                     |
|                       +--------------+-----------------------------+-------------------------------+
|                       | ``"scrub"``  | Set to NULL.                | Exported.                     |
|                       +--------------+-----------------------------+-------------------------------+
|                       | ``"keep"``   | Kept as it is.              | Exported.                     |
+-----------------------+--------------+-----------------------------+-------------------------------+
| ``"anonymize"`` with  | ``"ref"`` or | No statement: nothing       | Exported.                     |
| no ``"scrub"`` column | ``"keep"``   | changes (for example        |                               |
|                       |              | comments).                  |                               |
+-----------------------+--------------+-----------------------------+-------------------------------+
| none (only the user   | as above     | Treated as ``"anonymize"``: | Exported.                     |
| table, see            |              | the row stays so foreign    |                               |
| ``USER_TABLE``)       |              | keys keep working.          |                               |
+-----------------------+--------------+-----------------------------+-------------------------------+

How the user's rows are found in a table:

* The user table: ``id = <user id>``.
* A table with a ``"ref"`` straight to the user table: only those columns are
  used. For example comments are found by ``comments.user_id``, not by
  ``comments.post_id``, so other people's comments on the user's posts are not
  deleted or exported.
* A table with no direct ref: through its parents, for example
  ``thumbnail.post IN (SELECT posts.id FROM posts WHERE posts.user_id = <user id>)``.

Statements run children first, so a child's subquery still finds the parent
rows before they are deleted.
"""

import csv
import io
import json
import zipfile

import sqlalchemy as sa

from .common import USER_TABLE, classify, get_table_policy

USER_ID = sa.bindparam("target_user_id")
"""Placeholder for the user id. The real value is passed when the statements run.

It can't be called "user_id": in an UPDATE, SQLAlchemy reserves bind names that
match a column name, and tables like posts have a "user_id" column.
"""

DELETE_STATEMENTS = []
"""DELETE and UPDATE statements, children first. Filled at startup."""

DOWNLOAD_QUERIES = {}
"""One SELECT per table, keyed by table name. Filled at startup."""

EXTERNAL_DELETE_STATEMENTS = {}
"""Statements added by other packages for data the foreign keys can't see,
keyed by a name. For example the audit logs, which store the user id without
a foreign key. The startup hook doesn't clear them.
"""

EXTERNAL_DOWNLOAD_QUERIES = {}
"""Download queries added by other packages, keyed by file name."""


def register_external_delete(name, statement):
    """Add a statement that runs when a user is deleted.

    Registering the same name again replaces it, so creating the app twice
    (for example in tests) doesn't run it twice.
    """
    EXTERNAL_DELETE_STATEMENTS[name] = statement


def register_external_download(name, query):
    """Add a query whose rows are exported when a user downloads their data."""
    EXTERNAL_DOWNLOAD_QUERIES[name] = query


EXTERNAL_DOWNLOAD_FUNCTIONS = {}
"""Downloads of data that is not in the database, keyed by file name.
For example the job logs, which only live in OpenSearch.
"""

AFTER_DELETE_HOOKS = {}
"""Functions that run after the deletion is committed, keyed by a name.
For example the search package, which reindexes the user's documents.
"""


def register_external_download_function(name, function):
    """Add a function whose result is exported as ``<name>.json``.

    The function takes the user id and returns a list of dicts.
    """
    EXTERNAL_DOWNLOAD_FUNCTIONS[name] = function


def register_after_delete(name, hook):
    """Add a function that runs after a user's data is deleted.

    The function gets the ids of every row the deletion touched, by table. For example:
        {"accounts_user": [1], "posts": [1, 2], "thumbnail": [4]}
    """
    AFTER_DELETE_HOOKS[name] = hook


def build_policy_strategy(metadata, user_linked_tables):
    """Return what to do with each user-linked table, children first.

    For example, one item of the returned list:
        {
            "table": "thumbnail",
            "policy": "delete",
            "refs": [{"column": "post", "points_to": "posts", "target_column": "id"}],
            "scrub": [],
            "keep": ["id", "img", "created", "updated"],
        }
    """
    strategy = []

    tables_parents_first = metadata.sorted_tables
    tables_children_first = reversed(tables_parents_first)

    for table in tables_children_first:
        if table.name not in user_linked_tables:
            continue

        refs = []
        scrub = []
        keep = []
        for column in table.columns:
            label = classify(column, user_linked_tables)

            if label == "scrub":
                scrub.append(column.key)
                continue

            if label == "keep":
                keep.append(column.key)
                continue

            # label == "ref": write down where it points, the WHERE clause needs it.
            for foreign_key in column.foreign_keys:
                refs.append({
                    "column": column.key,
                    "points_to": foreign_key.column.table.name,
                    "target_column": foreign_key.column.key,
                })

        strategy.append({
            "table": table.name,
            "policy": get_table_policy(table),
            "refs": refs,
            "scrub": scrub,
            "keep": keep,
        })

    return strategy


def index_by_table(strategy):
    """Return the strategy as a dict keyed by table name."""
    strategy_by_table = {}
    for item in strategy:
        strategy_by_table[item["table"]] = item
    return strategy_by_table


def build_where(table_name, strategy_by_table, metadata):
    """Return a WHERE clause that selects one user's rows in this table.

    For example, for "thumbnail" it returns:
        thumbnail.post IN (SELECT posts.id FROM posts WHERE posts.user_id = :target_user_id)
    """
    table = metadata.tables[table_name]

    if table_name == USER_TABLE:
        return table.c.id == USER_ID

    refs = strategy_by_table[table_name]["refs"]

    direct_refs = []
    for ref in refs:
        if ref["points_to"] == USER_TABLE:
            direct_refs.append(ref)

    conditions = []

    # The table points straight at the user: only use those columns.
    if direct_refs:
        for ref in direct_refs:
            column = table.c[ref["column"]]
            conditions.append(column == USER_ID)
        return sa.or_(*conditions)

    # No direct ref: select the parent's rows for this user first,
    # then match this column against their ids.
    for ref in refs:
        column = table.c[ref["column"]]
        parent_table = metadata.tables[ref["points_to"]]
        parent_column = parent_table.c[ref["target_column"]]

        parent_where = build_where(ref["points_to"], strategy_by_table, metadata)
        parent_ids = sa.select(parent_column).where(parent_where)
        conditions.append(column.in_(parent_ids))

    return sa.or_(*conditions)


def build_delete_statements(strategy, metadata):
    """Return the DELETE and UPDATE statements, children first.

    For example, for the PoC models:
        DELETE FROM meta_thumbnail WHERE meta_thumbnail.post IN (SELECT thumbnail.id ...)
        DELETE FROM thumbnail WHERE thumbnail.post IN (SELECT posts.id ...)
        UPDATE posts SET body=NULL WHERE posts.user_id = :target_user_id
        UPDATE accounts_user SET email=NULL, ... WHERE accounts_user.id = :target_user_id
    """
    strategy_by_table = index_by_table(strategy)
    statements = []

    for item in strategy:
        table = metadata.tables[item["table"]]
        where = build_where(item["table"], strategy_by_table, metadata)

        if item["policy"] == "delete":
            statements.append(sa.delete(table).where(where))
            continue

        # For example comments: kept, nothing to scrub.
        if not item["scrub"]:
            continue

        empty_values = {}
        for column_name in item["scrub"]:
            empty_values[column_name] = None
        statements.append(sa.update(table).where(where).values(empty_values))

    return statements


def build_download_queries(strategy, metadata):
    """Return one SELECT per table, keyed by table name, parents first.

    For example:
        {"accounts_user": SELECT ... FROM accounts_user WHERE accounts_user.id = :target_user_id,
         "posts": SELECT ... FROM posts WHERE posts.user_id = :target_user_id, ...}
    """
    strategy_by_table = index_by_table(strategy)
    queries = {}

    strategy_parents_first = reversed(strategy)
    for item in strategy_parents_first:
        table = metadata.tables[item["table"]]
        where = build_where(item["table"], strategy_by_table, metadata)
        queries[item["table"]] = sa.select(table).where(where)

    return queries


def primary_key_name(query):
    """Return the name of the primary key column of the table a download query reads.

    For example, the query for "posts" returns "id".
    """
    table = query.get_final_froms()[0]
    primary_key_columns = list(table.primary_key.columns)
    return primary_key_columns[0].key


def find_user_row_ids(session, user_id):
    """Return the ids of the user's rows in every user-linked table.

    It reuses the download queries, because they find exactly the rows the
    deletion touches. For example:
        {"accounts_user": [1], "posts": [1, 2], "comments": [2], "thumbnail": [4]}
    """
    parameters = {"target_user_id": user_id}
    row_ids_by_table = {}

    for table_name, query in DOWNLOAD_QUERIES.items():
        id_column = primary_key_name(query)
        rows = session.execute(query, parameters).mappings()

        row_ids = []
        for row in rows:
            row_ids.append(row[id_column])
        row_ids_by_table[table_name] = row_ids

    return row_ids_by_table


def delete_user_data(session, user_id):
    """Run every delete statement for one user, in one transaction, then the after-delete hooks."""
    parameters = {"target_user_id": user_id}

    # Find the rows first: once deleted, they can't be found anymore.
    user_row_ids = find_user_row_ids(session, user_id)

    # External statements first: they only update their own tables (for
    # example audit logs) and don't depend on the foreign-key ones.
    for statement in EXTERNAL_DELETE_STATEMENTS.values():
        session.execute(statement, parameters)

    for statement in DELETE_STATEMENTS:
        session.execute(statement, parameters)

    session.commit()

    # After the commit, so the hooks read the anonymized rows, not the old ones.
    # The SQL ran with Core statements, so the session may still hold old copies.
    session.expire_all()
    for hook in AFTER_DELETE_HOOKS.values():
        hook(user_row_ids)


def download_user_data(session, user_id):
    """Return a zip file (bytes) with one CSV per table.

    Each table has different columns, so each gets its own CSV.
    """
    parameters = {"target_user_id": user_id}
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        all_queries = {}
        all_queries.update(DOWNLOAD_QUERIES)
        all_queries.update(EXTERNAL_DOWNLOAD_QUERIES)

        for table_name, query in all_queries.items():
            result = session.execute(query, parameters)

            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(result.keys())
            for row in result:
                writer.writerow(row)

            zip_file.writestr(f"{table_name}.csv", csv_buffer.getvalue())

        # Data outside the database has no fixed columns, so it is exported as JSON.
        for name, function in EXTERNAL_DOWNLOAD_FUNCTIONS.items():
            documents = function(user_id)
            zip_file.writestr(f"{name}.json", json.dumps(documents, indent=2, default=str))

    return zip_buffer.getvalue()
