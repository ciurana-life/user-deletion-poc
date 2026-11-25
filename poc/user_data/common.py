"""Parts shared by the prevention layer and the policy layer.

Every table that leads to the user (directly or through other tables via
foreign keys) must say what to do with its data:

* Table policy, set with ``__table_args__ = {"info": {"user_data": ...}}``:
    - ``"delete"``:    the user's rows are removed.
    - ``"anonymize"``: the rows are kept, personal columns are scrubbed.

* Column label, set with ``db.Column(..., info={"user_data": ...})``:
    - ``"ref"``:    points at the user (or at another user-linked table).
    - ``"scrub"``:  personal data, emptied on delete/anonymize.
    - ``"keep"``:   not personal, left untouched.

Foreign keys to user-linked tables are labeled ``"ref"`` automatically, and the
columns in ``DEFAULTS`` are ``"keep"``. **Everything else must be labeled**.

Both ``info`` dicts are plain SQLAlchemy metadata: they live only in Python,
never reach the database and need no migration.
"""

DEFAULTS = {"id": "keep", "created": "keep", "updated": "keep"}
"""Labels for common columns that don't need annotating."""

USER_TABLE = "accounts_user"
"""Table name of the user object."""

LABELS = ("ref", "scrub", "keep")
"""Allowed column labels: ``db.Column(..., info={"user_data": <label>})``."""

POLICIES = ("delete", "anonymize")
"""Allowed table policies: ``__table_args__ = {"info": {"user_data": <policy>}}``."""


def parents(table_or_column):
    """Return the names of the tables that a table or column points to via FKs."""
    return {fk.target_fullname.split(".")[0] for fk in table_or_column.foreign_keys}


def classify(col, linked):  # TODO - might be good to annotate types here -> (LABELS | None)
    """Return the label of a column, or None if it is not classified."""
    if "user_data" in col.info:
        return col.info["user_data"]
    if parents(col) & linked:
        return "ref"
    return DEFAULTS.get(col.key)


def get_table_policy(table):
    """Return "delete" or "anonymize" for a table.

    The user table has no policy label. It is always anonymized, because its
    row must stay for foreign keys (for example from comments).
    """
    if table.name == USER_TABLE:
        return "anonymize"
    return table.info["user_data"]


def find_user_linked_tables(metadata):
    """Return the names of every table that leads to the user, at any depth."""
    linked = {USER_TABLE}
    changed = True
    while changed:
        changed = False
        for table in metadata.tables.values():
            if table.name not in linked and (parents(table) & linked or "user_data" in table.info):
                linked.add(table.name)
                changed = True
    return linked
