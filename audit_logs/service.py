"""Write audit logs."""

from poc.db import db

from .actions import REGISTERED_ACTIONS
from .models import AuditLog
from .schema import AuditLogSchema, COLUMN_FIELDS


def get_schema(action_id):
    """Return the schema for an action, or the default schema if it is not registered.

    Like in Invenio: an unregistered action still stores the shared fields
    (user, resource), but all its metadata is dropped.
    """
    action_cls = REGISTERED_ACTIONS.get(action_id)
    if action_cls is None:
        return AuditLogSchema()
    return action_cls.marshmallow_schema()()


def create_audit_log(action_cls, user, resource_id, **kwargs):
    """Build, validate and store one audit log. Return the new row."""
    data = action_cls.build(user, resource_id, **kwargs)

    schema = get_schema(action_cls.id)
    loaded = schema.load(data)

    column_values = {}
    json_values = {}
    for key, value in loaded.items():
        if key in COLUMN_FIELDS:
            column_values[key] = value
        else:
            json_values[key] = value

    audit_log = AuditLog(json=json_values, **column_values)
    db.session.add(audit_log)
    return audit_log
