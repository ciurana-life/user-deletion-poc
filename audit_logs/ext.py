"""Startup: check the labels of every registered action, then build the SQL."""

from poc.user_data.policy import register_external_delete, register_external_download

from .actions import REGISTERED_ACTIONS
from .labels import check_registered_actions
from .policy import build_delete_statement, build_download_query

LABELS_BY_ACTION = {}
"""Labels of every registered action, filled at startup. Used by the CI canary."""


def init_audit_logs(app):
    """Refuse to start if an audit log field is unlabelled, then build the SQL.

    Call it after every package has registered its actions.
    """
    # Prevention layer: raises TypeError if any field has no label.
    labels_by_action = check_registered_actions(REGISTERED_ACTIONS)
    LABELS_BY_ACTION.clear()
    LABELS_BY_ACTION.update(labels_by_action)

    # Policy layer: hand the SQL to the user data module, so deleting or
    # downloading a user also covers audit logs.
    delete_statement = build_delete_statement(labels_by_action)
    if delete_statement is not None:
        register_external_delete("audit_logs_metadata", delete_statement)
    register_external_download("audit_logs_metadata", build_download_query())
