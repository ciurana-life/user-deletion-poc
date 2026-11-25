"""Audit log actions of the PoC app.

They live outside the ``audit_logs`` package on purpose, like the actions of
invenio-drafts-resources and invenio-rdm-records live outside invenio-audit-logs.
Every field has a ``user_data`` label, or the app refuses to start.
"""

from marshmallow import Schema, fields

from audit_logs.actions import AuditLogAction

from .context import RequestContext, UserContext, ValuesContext


class BaseAuditLog(AuditLogAction):
    """Shared by every action: who did it and from where."""

    context = [UserContext(), RequestContext()]

    metadata_schema = {
        "ip_address": fields.Str(required=True, metadata={"user_data": "scrub"}),
        "session": fields.Str(required=False, metadata={"user_data": "scrub"}),
    }


class PostCreateAuditLog(BaseAuditLog):
    """A user created a post."""

    id = "post.create"
    resource_type = "post"
    context = BaseAuditLog.context + [ValuesContext("title")]

    metadata_schema = {
        **BaseAuditLog.metadata_schema,
        # Record content, like a record title.
        "title": fields.Str(required=True, metadata={"user_data": "keep"}),
    }


class PostDeleteAuditLog(BaseAuditLog):
    """A user deleted a post."""

    id = "post.delete"
    resource_type = "post"


class CommentCreateAuditLog(BaseAuditLog):
    """A user commented on a post."""

    id = "comment.create"
    resource_type = "comment"
    context = BaseAuditLog.context + [ValuesContext("post_id")]

    metadata_schema = {
        **BaseAuditLog.metadata_schema,
        "post_id": fields.Str(required=True, metadata={"user_data": "keep"}),
    }


class GrantSubjectSchema(Schema):
    """Who got access. ``id`` is a user id when ``type`` is "user"."""

    id = fields.Str(required=True, metadata={"user_data": "ref"})
    type = fields.Str(required=True, metadata={"user_data": "keep"})


class GrantSchema(Schema):
    """One access grant."""

    subject = fields.Nested(GrantSubjectSchema, required=True)
    permission = fields.Str(required=True, metadata={"user_data": "keep"})


class PostGrantAuditLog(BaseAuditLog):
    """A user changed who can access a post. Names another user in the grants."""

    id = "post.grant_update"
    resource_type = "post"
    context = BaseAuditLog.context + [ValuesContext("before", "after")]

    metadata_schema = {
        **BaseAuditLog.metadata_schema,
        "before": fields.List(fields.Nested(GrantSchema), required=True),
        "after": fields.List(fields.Nested(GrantSchema), required=True),
    }
