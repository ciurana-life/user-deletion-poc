"""Register the PoC's audit log actions.

Stand-in for the ``invenio_audit_logs.actions`` entry point in ``pyproject.toml``.
"""

from audit_logs.actions import register_action

from .actions import (
    CommentCreateAuditLog,
    PostCreateAuditLog,
    PostDeleteAuditLog,
    PostGrantAuditLog,
)

register_action(PostCreateAuditLog)
register_action(PostDeleteAuditLog)
register_action(CommentCreateAuditLog)
register_action(PostGrantAuditLog)
