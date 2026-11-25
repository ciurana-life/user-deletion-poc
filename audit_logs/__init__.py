"""Stand-in for invenio-audit-logs.

* ``models``:   the one table that stores audit logs, plus the guard that
                stops other packages from subclassing it.
* ``schema``:   the shared schema. Every field has a ``user_data`` label.
* ``actions``:  ``AuditLogAction`` and the registry of actions. Other packages
                define actions and register them (Invenio uses the
                ``invenio_audit_logs.actions`` entry point).
* ``labels``:   prevention layer: refuse to start if a field has no label.
* ``policy``:   build the SQL that scrubs or downloads one user's audit logs.
* ``service``:  write an audit log.
* ``ext``:      ``init_audit_logs(app)``, runs the label check and builds the SQL.
"""
