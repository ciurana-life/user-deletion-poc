"""Audit log actions and their registry."""

from marshmallow import fields

from .schema import AuditLogSchema, MetadataSchema

REGISTERED_ACTIONS = {}
"""Actions that can be logged, keyed by action id. Stand-in for the entry point."""

ALL_ACTION_CLASSES = []
"""Every concrete action class that was defined, registered or not.

A CI test compares it with ``REGISTERED_ACTIONS``: an action that is used but
not registered falls back to the default schema and skips the label check.
"""


def register_action(action_cls):
    """Register an action so it can be logged.

    For example: ``register_action(PostCreateAuditLog)``.
    """
    REGISTERED_ACTIONS[action_cls.id] = action_cls
    return action_cls


class AuditLogAction:
    """Base class for audit log actions.

    Subclasses set ``id``, ``resource_type``, ``context`` (callables that add
    data, for example the user and the IP address) and ``metadata_schema``
    (a dict of marshmallow fields, each with a ``user_data`` label).
    """

    id = None
    resource_type = None
    context = []
    metadata_schema = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Base classes like BaseAuditLog have no id: they are never logged.
        if cls.id is not None:
            ALL_ACTION_CLASSES.append(cls)

    @classmethod
    def build(cls, user, resource_id, **kwargs):
        """Return the data for one audit log, before it is loaded by the schema.

        For example:
            {"action": "post.create", "resource": {"id": "1", "type": "post"},
             "user_id": "1", "resource_type": "post",
             "user": {"id": "1", "username": "alice", "email": "alice@example.org"},
             "metadata": {"ip_address": "10.0.0.1", "title": "Hello"}}
        """
        data = {
            "action": cls.id,
            "resource": {"id": str(resource_id), "type": cls.resource_type},
            "user_id": str(user.id),
            "resource_type": cls.resource_type,
        }
        for context in cls.context:
            context(data, user=user, **kwargs)
        return data

    @classmethod
    def marshmallow_schema(cls):
        """Return the full schema for this action: the shared fields plus its metadata."""
        if cls.metadata_schema is None:
            return AuditLogSchema

        metadata_schema = MetadataSchema.from_dict(cls.metadata_schema)
        extra_fields = {
            "metadata": fields.Nested(metadata_schema, required=True),
        }
        return AuditLogSchema.from_dict(extra_fields)
