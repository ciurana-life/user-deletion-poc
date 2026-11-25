"""Schema shared by every audit log.

Every field carries a ``user_data`` label in its marshmallow ``metadata``:

* ``"ref"``:   a user id. Used to find the user's rows, and kept after deletion
               because the account row is anonymized, not deleted.
* ``"scrub"``: personal data, removed when the user is deleted.
* ``"keep"``:  not personal, left untouched.

``Nested`` and ``List`` fields don't need a label: their inner fields have one.
Unknown keys are dropped (``unknown = EXCLUDE``), so the labelled fields are the
full list of what can be stored.
"""

from marshmallow import EXCLUDE, Schema, fields


class ResourceSchema(Schema):
    """The resource the action was done on."""

    class Meta:
        unknown = EXCLUDE

    type = fields.Str(required=True, metadata={"user_data": "keep"})
    id = fields.Str(required=True, metadata={"user_data": "keep"})


class UserSchema(Schema):
    """Copy of the user who did the action, taken when the log is written."""

    class Meta:
        unknown = EXCLUDE

    id = fields.Str(required=True, metadata={"user_data": "ref"})
    username = fields.Str(required=False, metadata={"user_data": "scrub"})
    email = fields.Email(required=True, metadata={"user_data": "scrub"})


class MetadataSchema(Schema):
    """Base for each action's metadata. Actions add their own fields."""

    class Meta:
        unknown = EXCLUDE


class AuditLogSchema(Schema):
    """Main schema for one audit log."""

    class Meta:
        unknown = EXCLUDE

    action = fields.Str(required=True, metadata={"user_data": "keep"})
    resource = fields.Nested(ResourceSchema, required=True)
    user = fields.Nested(UserSchema, required=True)
    metadata = fields.Nested(MetadataSchema, required=False)

    # Stored in their own columns, not in the JSON.
    user_id = fields.Str(required=True, metadata={"user_data": "ref"})
    resource_type = fields.Str(required=True, metadata={"user_data": "keep"})


COLUMN_FIELDS = ("action", "user_id", "resource_type")
"""Fields stored in their own column. Everything else goes in the ``json`` column."""
