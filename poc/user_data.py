"""Classify user data in the database so it can be deleted, anonymized or exported.

Every table that leads to the user (directly or through other tables via
foreign keys) must say what to do with its data:

* Table policy, set with ``__table_args__`` = {"info": {"user_data": ...}}``:
    - ``"delete"``:    the user's rows are removed.
    - ``"anonymize"``: the rows are kept, personal columns are scrubbed.

* Colum lable, set with ``db.Column(..., info={"user_data": ...})``:
    - ``"ref"``:    points at the user (or at another user-linked table).
    - ``"scrub``:   personal data, emptied on delete/anonymize.
    - ``"keep"``:   not personal, left untouched.

Foreign keys to user-linked tables are labeled ``"ref"`` automatically, and the
columns in ``DEFAULTS`` are ``"keep"``. **Everything else must be labeled**.

Both ``info`` dicts are plain SQLAlchemy metadata: they live only in Python,
never reach the database and need no migration.

The check runs once all models are loaded (see ``check_user_data``) and raises a
TypeError listing every table or column that is missing a classification.
"""

from sqlalchemy import event
from sqlalchemy.orm import Mapper
from .db import db

DEFAULTS = {"id": "keep", "created": "keep", "updated": "keep"}
"""Labels for common columns that don't need annotating."""

USER_TABLE = "accounts_user"
"""Table name of the user object."""

LABELS = ("ref", "scrub", "keep")
"""Allowed column labels: ``db.Column(..., info={"user_data": <label>})``."""

POLICIES = ("delete", "anonymize")
"""Allowed table policies: ``__table_args__ = {"info": "user_data": <policy>}}``."""

def parents(table_or_column):
    """Return the names of the tables that a table or column points via FKs."""
    return {fk.target_fullname.split(".")[0] for fk in table_or_column.foreign_keys}


def classify(col, linked): # TODO - might be good to annotate types here -> (LABELS | None)
    """Return the label of a column, or None if it is not classified."""
    if "user_data" in col.info:
        return col.info["user_data"]
    if parents(col) & linked:
        return "ref"
    return DEFAULTS.get(col.key)

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

def check_all_user_data(metadata):
    """Return a list of human-readable errors for unclassified user data."""
    linked = find_user_linked_tables(metadata)
    errors = []
    for name in sorted(linked):
        table = metadata.tables.get(name)
        if table is None:
            continue
        if name != USER_TABLE and table.info.get("user_data") not in POLICIES:
            errors.append(f"{name}: set the arguments etc etc")
        for col in table.columns:
            label = classify(col, linked)
            if label is None:
                errors.append(f"{name}.{col.key}: missing info= etc etc")
            elif label not in LABELS:
                errors.append(f"{name}.{col.key}: unknown label {label!r}, use one of {LABELS}")
    return errors


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
def cehck_user_data():
    """Refuse to start if any user data is unclassified.
    
    Note: it fires only once per process, so ina  test run only the first
    ttest that creates the app resports the error.
    """
    if errors := check_all_user_data(db.metadata):
        # TODO - make it a way nicer print.
        raise TypeError("Unclassified user data:\n " + "\n ".join(errors) + "\n Please visit ... for more info")
    