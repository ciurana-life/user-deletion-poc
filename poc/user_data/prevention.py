"""Prevention layer: tell the developer they forgot to classify user data.

The check runs once all models are loaded (see ``events.check_user_data``) and
raises a TypeError listing every table or column that is missing a
classification. The labels themselves are explained in ``common``.
"""

from .common import LABELS, POLICIES, USER_TABLE, classify


def check_all_user_data(metadata, user_linked_tables):
    """Return a list of human-readable errors for unclassified user data."""
    errors = []
    for name in sorted(user_linked_tables):
        table = metadata.tables.get(name)
        if table is None:
            continue
        if name != USER_TABLE and table.info.get("user_data") not in POLICIES:
            errors.append(f"{name}: set the arguments etc etc")
        for col in table.columns:
            label = classify(col, user_linked_tables)
            if label is None:
                errors.append(f"{name}.{col.key}: missing info= etc etc")
            elif label not in LABELS:
                errors.append(f"{name}.{col.key}: unknown label {label!r}, use one of {LABELS}")
    return errors
