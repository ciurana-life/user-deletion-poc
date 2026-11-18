"""Database object and shared mixins (stand-in for invenio-db)."""

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


class Timestamp:
    """Same idea as invenio_db's Timestamp mixin."""

    created = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
