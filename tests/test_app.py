import pytest

from poc import create_app
from poc.cli import seed_data
from poc.db import db
from poc.models import User
from poc.related_data_models import Comment, Post, Record


@pytest.fixture
def app():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "TESTING": True})
    with app.app_context():
        seed_data()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_seed_counts(app):
    assert db.session.query(User).count() == 3
    assert db.session.query(Post).count() == 3
    assert db.session.query(Comment).count() == 3
    assert db.session.query(Record).count() == 3


def test_records_found_by_json_owner(app):
    alice = db.session.scalar(db.select(User).filter_by(username="alice"))
    titles = sorted(r.title for r in Record.owned_by(alice.id))
    assert titles == ["Alice's dataset", "Joint paper"]


def test_pages_render(client):
    assert b"alice@example.org" in client.get("/").data
    page = client.get("/users/1").data
    assert b"Hello from Alice" in page
    assert b"Nice notes, Bob." in page
    assert b"Alice&#39;s dataset" in page or b"Alice's dataset" in page
