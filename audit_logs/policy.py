"""Policy layer: build the SQL that scrubs or downloads one user's audit logs.

What happens to each field when a user is deleted:

+-------------+------------------------------------------------------------+
| Label       | On delete                                                  |
+=============+============================================================+
| ``"ref"``   | Kept. ``user_id`` finds the rows where the user is the     |
|             | actor. Ids stay because the account row is anonymized.    |
+-------------+------------------------------------------------------------+
| ``"scrub"`` | Removed from the JSON, in the rows where the user is the   |
|             | actor.                                                     |
+-------------+------------------------------------------------------------+
| ``"keep"``  | Left untouched.                                            |
+-------------+------------------------------------------------------------+

Rows where the user only appears as a ``ref`` inside someone else's log (for
example as the subject of a grant) are not changed: the id is all they hold.

One UPDATE covers every action: removing a JSON path that a row doesn't have
does nothing, so the paths of all actions are removed together.
"""

import sqlalchemy as sa

from poc.user_data.policy import USER_ID

from .models import AuditLog
from .schema import COLUMN_FIELDS


def collect_scrub_paths(labels_by_action):
    """Return the JSON paths to remove, for all actions together.

    For example: ["$.metadata.ip_address", "$.metadata.session", "$.user.email", "$.user.username"]
    """
    scrub_paths = set()

    for labels in labels_by_action.values():
        for path, label in labels.items():
            if label != "scrub":
                continue

            # Fields with their own column hold only ids and types today.
            # Scrubbing a column would need an UPDATE of that column instead.
            top_level_field = path.split(".")[0]
            if top_level_field in COLUMN_FIELDS:
                raise TypeError(f"{path}: 'scrub' on a column field is not supported yet")

            scrub_paths.add("$." + path)

    return sorted(scrub_paths)


def rows_of_user():
    """Return the WHERE clause for the rows where the user is the actor.

    ``user_id`` is a string column, so the id is cast to match it.
    """
    return AuditLog.user_id == sa.cast(USER_ID, sa.String)


def build_delete_statement(labels_by_action):
    """Return the UPDATE that removes the scrub paths from the user's rows.

    For example (SQLite):
        UPDATE audit_logs_metadata
        SET json=json_remove(audit_logs_metadata.json, '$.metadata.ip_address', ...)
        WHERE audit_logs_metadata.user_id = CAST(:target_user_id AS VARCHAR)

    The Postgres version would use ``json #- '{metadata,ip_address}'`` instead.
    """
    scrub_paths = collect_scrub_paths(labels_by_action)
    if not scrub_paths:
        return None

    scrubbed_json = sa.func.json_remove(AuditLog.json, *scrub_paths)
    return sa.update(AuditLog).where(rows_of_user()).values(json=scrubbed_json)


def build_download_query():
    """Return the SELECT for every audit log where the user is the actor."""
    return sa.select(AuditLog.__table__).where(rows_of_user())
