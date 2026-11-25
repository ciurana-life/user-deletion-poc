"""The audit log table."""

from poc.db import db, utcnow

AUDIT_LOGS_PACKAGE = "audit_logs"
"""Only classes defined in this package may subclass the audit log model."""


def is_defined_in_audit_logs_package(cls):
    """Return True if the class is defined inside the audit logs package.

    For example, "audit_logs.models" returns True and "poc.models" returns False.
    """
    module_name = cls.__module__
    is_the_package = module_name == AUDIT_LOGS_PACKAGE
    is_a_submodule = module_name.startswith(AUDIT_LOGS_PACKAGE + ".")
    return is_the_package or is_a_submodule


class AuditLog(db.Model):
    """One audit log row.

    ``user_id`` has no foreign key on purpose (like in Invenio), so the
    foreign-key based user data check can't see this table. Its data is
    labelled in ``schema.AuditLogSchema`` instead.
    """

    __tablename__ = "audit_logs_metadata"

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=utcnow, nullable=False)
    action = db.Column(db.String(255), nullable=False)
    resource_type = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.String(255), nullable=False)
    json = db.Column(db.JSON, nullable=False, default=dict)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # User deletion relies on all audit log data living in this one table,
        # labelled through AuditLogSchema. A subclass somewhere else could add
        # a table or columns that the deletion code and the canary test don't
        # know about.
        if not is_defined_in_audit_logs_package(cls):
            raise TypeError(
                f"{cls.__module__}.{cls.__name__} subclasses the AuditLog model. "
                "Audit log storage must be defined in the audit_logs package. "
                "To log a new kind of event, register an AuditLogAction instead."
            )
