"""Write the registered indexes from Postgres, like invenio-indexer.

This is the only module that writes the registered indexes. The CI check in
``prevention`` allows it to write to OpenSearch directly.
"""

from poc.db import db

from .client import prefix_index, search_client
from .indexes import REGISTERED_INDEXES, find_indexes_for_table


def index_row(index, row):
    """Write the document of one row, replacing the old one."""
    document = index.dump(row)
    search_client().index(index=prefix_index(index.name), id=str(row.id), body=document)


def delete_document(index, row_id):
    """Delete the document of a row that no longer exists.

    A missing document is fine: the row may never have been indexed.
    """
    search_client().delete(index=prefix_index(index.name), id=str(row_id), ignore=404)


def refresh(index):
    """Make the latest writes visible to searches. Only needed so tests and the demo see them at once."""
    search_client().indices.refresh(index=prefix_index(index.name))


def rebuild_index(index):
    """Delete the index and write every row again. Like ``invenio index reindex``."""
    client = search_client()
    index_name = prefix_index(index.name)

    client.indices.delete(index=index_name, ignore=404)
    client.indices.create(index=index_name)

    rows = db.session.scalars(db.select(index.model)).all()
    for row in rows:
        index_row(index, row)

    refresh(index)


def rebuild_all_indexes():
    """Rebuild every registered index."""
    for index in REGISTERED_INDEXES.values():
        rebuild_index(index)


def reindex_rows(table_name, row_ids):
    """Bring the documents of these rows in line with Postgres.

    A row that still exists is indexed again, so a scrubbed column disappears
    from its document too. A row that was deleted gets its document deleted.
    """
    indexes = find_indexes_for_table(table_name)

    for index in indexes:
        for row_id in row_ids:
            row = db.session.get(index.model, row_id)

            if row is None:
                delete_document(index, row_id)
                continue

            index_row(index, row)

        refresh(index)
