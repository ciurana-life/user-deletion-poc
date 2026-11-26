"""Policy layer for OpenSearch: what happens to indexed copies when a user is deleted.

The registered indexes only hold copies of Postgres rows, so there is nothing
to label here. After the deletion SQL has run, the documents of the user's
rows are rebuilt from Postgres:

+--------------------------------+------------------------------------------+
| The row after the deletion SQL | Its document                             |
+================================+==========================================+
| Anonymized (still there)       | Indexed again, without the scrubbed data |
+--------------------------------+------------------------------------------+
| Deleted                        | Deleted                                  |
+--------------------------------+------------------------------------------+

Download needs nothing from these indexes: the data is the same as in Postgres,
which is already exported.
"""

from flask import current_app

from .indexer import reindex_rows


def reindex_after_user_deletion(user_row_ids):
    """Reindex or delete the documents of every row the deletion touched.

    ``user_row_ids`` is collected before the SQL runs, because deleted rows
    can't be found afterwards. For example:
        {"accounts_user": [1], "posts": [1, 2], "comments": [2], "thumbnail": [4]}
    """
    # Only for tests that run without OpenSearch.
    if not current_app.config["SEARCH_ENABLED"]:
        return

    for table_name, row_ids in user_row_ids.items():
        reindex_rows(table_name, row_ids)
