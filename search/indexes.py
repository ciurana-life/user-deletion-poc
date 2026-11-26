"""The registry of indexes that are built from Postgres.

Each index is built from one table, like the records, users and community
members indexes in Zenodo. A ``dump`` function turns one row into one document.
The document may copy data from other tables too, for example the author's
username in a post document.

Because every document is made from a row, Postgres stays the source of truth:
reindexing a row overwrites its document with what is in the database now.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class IndexDefinition:
    """One index built from Postgres.

    For example:
        IndexDefinition(name="posts", model=Post, dump=dump_post)
    """

    name: str
    model: type
    dump: Callable


REGISTERED_INDEXES = {}
"""Indexes built from Postgres, keyed by index name (without the prefix)."""


def register_index(name, model, dump):
    """Register an index that is built from the rows of ``model``.

    For example: ``register_index("posts", Post, dump_post)``.
    """
    REGISTERED_INDEXES[name] = IndexDefinition(name=name, model=model, dump=dump)


def find_indexes_for_table(table_name):
    """Return the indexes built from this table.

    For example, "posts" returns [IndexDefinition(name="posts", ...)].
    A table nobody indexes returns [].
    """
    indexes = []
    for index in REGISTERED_INDEXES.values():
        if index.model.__table__.name == table_name:
            indexes.append(index)
    return indexes
