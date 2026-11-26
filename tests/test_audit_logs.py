"""Audit logs: label check, model guard, and the canary test that CI runs."""

import copy
import json

import pytest
import sqlalchemy as sa
from flask import session
from marshmallow import fields

from audit_logs.actions import ALL_ACTION_CLASSES, REGISTERED_ACTIONS
from audit_logs.ext import LABELS_BY_ACTION
from audit_logs.labels import check_registered_actions, collect_labels
from audit_logs.models import AuditLog
from audit_logs.policy import build_delete_statement
from audit_logs.schema import AuditLogSchema, MetadataSchema
from audit_logs.service import create_audit_log
from poc import create_app
from poc.cli import seed_data
from poc.db import db
from poc.models import User
from poc.user_data import delete_user_data
from poc.user_data.policy import EXTERNAL_DELETE_STATEMENTS, register_external_delete

# Values that can't show up in the database by accident.
CANARY_EMAIL = "canary-x7q@canary.invalid"
CANARY_USERNAME = "canary-x7q"
CANARY_FULL_NAME = "Canary Person X7Q"
CANARY_IP = "203.0.113.77"
CANARY_SESSION = "canary-session-x7q"

CANARY_VALUES = (CANARY_EMAIL, CANARY_USERNAME, CANARY_FULL_NAME, CANARY_IP, CANARY_SESSION)
"""Personal data that must be gone after deletion. The user id is not here: ids are kept."""


@pytest.fixture
def app():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "TESTING": True, "SEARCH_ENABLED": False})
    with app.app_context():
        seed_data()
        yield app


@pytest.fixture
def canary_user(app):
    user = User(
        email=CANARY_EMAIL,
        username=CANARY_USERNAME,
        full_name=CANARY_FULL_NAME,
        last_login_ip=CANARY_IP,
    )
    db.session.add(user)
    db.session.commit()
    return user


def canary_kwargs(canary_user):
    """Return the extra arguments each action needs, keyed by action id.

    Every registered action needs an entry here, or ``test_canary`` fails.
    """
    grant_for_canary = {"subject": {"id": str(canary_user.id), "type": "user"}, "permission": "view"}
    return {
        "post.create": {"title": "A post"},
        "post.delete": {},
        "comment.create": {"post_id": "1"},
        "post.grant_update": {"before": [], "after": [grant_for_canary]},
    }


def write_audit_log(app, action_cls, user, ip_address, session_id, **kwargs):
    """Write one audit log as if ``user`` did the action from this IP address and session."""
    with app.test_request_context(environ_base={"REMOTE_ADDR": ip_address}):
        session["_id"] = session_id
        create_audit_log(action_cls, user, resource_id=1, **kwargs)
    db.session.commit()


def find_canary_values(canary_values):
    """Return every place in the database that still holds a canary value.

    It reads every column of every table, so it also finds tables nobody
    labelled. For example: ["audit_logs_metadata.json: 203.0.113.77"]
    """
    leaks = []
    for table in db.metadata.sorted_tables:
        rows = db.session.execute(sa.select(table)).mappings()
        for row in rows:
            for column_name, value in row.items():
                text = json.dumps(value, default=str)
                for canary_value in canary_values:
                    if canary_value in text:
                        leaks.append(f"{table.name}.{column_name}: {canary_value}")
    return leaks


def write_every_action(app, canary_user):
    """Write one audit log of every registered action with the canary user.

    The canary is the actor of every log. It is also named as the subject of a
    grant made by another user (alice).
    """
    kwargs_by_action = canary_kwargs(canary_user)

    for action_id, action_cls in REGISTERED_ACTIONS.items():
        write_audit_log(
            app, action_cls, canary_user, CANARY_IP, CANARY_SESSION, **kwargs_by_action[action_id]
        )

    # Alice uses her own IP and session: this row is hers, only the grant names the canary.
    alice = db.session.scalar(db.select(User).filter_by(username="alice"))
    grant_action = REGISTERED_ACTIONS["post.grant_update"]
    write_audit_log(
        app, grant_action, alice, "198.51.100.1", "alice-session", **kwargs_by_action["post.grant_update"]
    )


#
# Prevention layer
#


def test_unlabelled_field_is_reported():
    metadata_schema = MetadataSchema.from_dict({"note": fields.Str()})
    schema_cls = AuditLogSchema.from_dict({"metadata": fields.Nested(metadata_schema)})

    labels, errors = collect_labels(schema_cls())

    assert errors == ["metadata.note: missing metadata={'user_data': ...}"]
    assert labels["user.email"] == "scrub"


def test_app_refuses_to_start_with_an_unlabelled_action():
    # A stand-in action. It doesn't subclass AuditLogAction, so it doesn't end
    # up in ALL_ACTION_CLASSES and break the registration test.
    class UnlabelledAction:
        @classmethod
        def marshmallow_schema(cls):
            metadata_schema = MetadataSchema.from_dict({"note": fields.Str()})
            return AuditLogSchema.from_dict({"metadata": fields.Nested(metadata_schema)})

    with pytest.raises(TypeError, match="unlabelled: metadata.note: missing"):
        check_registered_actions({"unlabelled": UnlabelledAction})


def test_every_action_class_is_registered(app):
    # An unregistered action falls back to the default schema and skips the label check.
    for action_cls in ALL_ACTION_CLASSES:
        assert REGISTERED_ACTIONS.get(action_cls.id) is action_cls, f"{action_cls.id} is not registered"


def test_audit_log_model_cannot_be_subclassed_outside_the_package():
    with pytest.raises(TypeError, match="Audit log storage must be defined in the audit_logs package"):

        class MyAuditLog(AuditLog):
            extra = db.Column(db.String(255))


#
# Canary test (CI)
#


def test_canary(app, canary_user):
    # Every registered action must have a canary case, or a new action would pass untested.
    missing = set(REGISTERED_ACTIONS) - set(canary_kwargs(canary_user))
    assert not missing, f"Add a canary case for: {sorted(missing)}"

    write_every_action(app, canary_user)

    # The scan must see the canary before deletion, or it proves nothing.
    assert find_canary_values(CANARY_VALUES)

    delete_user_data(db.session, canary_user.id)
    db.session.expire_all()

    assert find_canary_values(CANARY_VALUES) == []

    # Ids are kept: the rows still point at the (now anonymized) account.
    canary_rows = db.session.scalars(db.select(AuditLog).filter_by(user_id=str(canary_user.id))).all()
    assert len(canary_rows) == len(REGISTERED_ACTIONS)


def test_canary_catches_a_wrong_label(app, canary_user):
    """If someone labels the IP address "keep", the canary must fail."""
    write_every_action(app, canary_user)

    wrong_labels = copy.deepcopy(LABELS_BY_ACTION)
    for labels in wrong_labels.values():
        labels["metadata.ip_address"] = "keep"

    correct_statement = EXTERNAL_DELETE_STATEMENTS["audit_logs_metadata"]
    register_external_delete("audit_logs_metadata", build_delete_statement(wrong_labels))
    try:
        delete_user_data(db.session, canary_user.id)
    finally:
        register_external_delete("audit_logs_metadata", correct_statement)

    db.session.expire_all()
    leaks = find_canary_values(CANARY_VALUES)

    assert "audit_logs_metadata.json: 203.0.113.77" in leaks
    assert not any(CANARY_EMAIL in leak for leak in leaks)
