"""Startup hook: check the labels, then build the delete and download SQL."""

from sqlalchemy import event
from sqlalchemy.orm import Mapper

from ..db import db
from .common import find_user_linked_tables
from .policy import (
    DELETE_STATEMENTS,
    DOWNLOAD_QUERIES,
    build_delete_statements,
    build_download_queries,
    build_policy_strategy,
)
from .prevention import check_all_user_data

# TODO - remove this comment block in final version.
"""
``after_configured``
SQLAlchemy will fire that event at the end of ``configure_mappers()``
that is called at app startup.
InvenioDB init_db:
```python
        # All models should be loaded by now.
        sa.orm.configure_mappers()
```
"""


@event.listens_for(Mapper, "after_configured")
def check_user_data():
    """Refuse to start if any user data is unclassified, then build the SQL.

    Note: it fires only once per process, so in a test run, only the first
    test that creates the app reports the error.
    """
    user_linked_tables = find_user_linked_tables(db.metadata)

    # Prevention layer: stop if data is not classified.
    errors = check_all_user_data(db.metadata, user_linked_tables)
    if errors:
        # TODO - make it a way nicer print.
        raise TypeError("Unclassified user data:\n " + "\n ".join(errors) + "\n Please visit ... for more info")

    # Policy layer: build the delete and download SQL once.
    # The lists are filled in place, so modules that already imported them see the result.
    strategy = build_policy_strategy(db.metadata, user_linked_tables)

    DELETE_STATEMENTS.clear()
    DELETE_STATEMENTS.extend(build_delete_statements(strategy, db.metadata))

    DOWNLOAD_QUERIES.clear()
    DOWNLOAD_QUERIES.update(build_download_queries(strategy, db.metadata))
