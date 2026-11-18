from sqlalchemy import event
from sqlalchemy.orm import Mapper
from .db import db

DEFAULTS = {"id": "keep", "created": "keep", "updated": "keep"}

USER_TABLE = "accounts_user"
"""Table name of the user object."""

LABELS = ("ref", "scrub", "keep")
POLICIES = ("delete", "anonymize")

def parents(table_or_column):
    return {fk.target_fullname.split(".")[0] for fk in table_or_column.foreign_keys}


def classify(col, linked):
    if "user_data" in col.info:
        return col.info["user_data"]
    if parents(col) & linked:
        return "ref"
    return DEFAULTS.get(col.key)

def find_user_linked_tables(metadata):
    """Every table that leads to the user via FKs (any depth, any load order)."""
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
    if errors := check_all_user_data(db.metadata):
        raise TypeError("Unclassified user data:\n " + "\n ".join(errors) + "\n Please visit ... for more info")
    