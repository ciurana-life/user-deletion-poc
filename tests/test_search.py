"""OpenSearch: the direct-write check, the unknown-index check, and the canary tests.

Start OpenSearch first with ``docker compose up -d``. Without it, the tests
that need it are skipped.
"""

import io
import json
import zipfile
from pathlib import Path

import pytest

from jobs.logging import JOB_LOGS_INDEX
from jobs.registry import REGISTERED_JOBS, register_job, run_job
from poc import create_app
from poc.cli import seed_data
from poc.db import db
from poc.models import User
from poc.related_data_models import Comment, Post
from poc.user_data import delete_user_data, download_user_data
from search.client import is_search_available, prefix_index, search_client
from search.indexer import rebuild_all_indexes
from search.prevention import find_direct_writes, find_unknown_indexes

REPO_ROOT = Path(__file__).parent.parent
PACKAGES = ["poc", "audit_logs", "search", "jobs"]

CANARY_EMAIL = "canary-s4k@canary.invalid"
CANARY_USERNAME = "canary-s4k"
CANARY_FULL_NAME = "Canary Person S4K"
CANARY_POST_BODY = "canary post body s4k"

CANARY_VALUES = (CANARY_EMAIL, CANARY_USERNAME, CANARY_FULL_NAME, CANARY_POST_BODY)
"""Personal data that must not be in any index after deletion. Ids are kept, so they are not here."""

MAX_DOCUMENTS = 10_000


@pytest.fixture
def app():
    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "TESTING": True,
            "SEARCH_INDEX_PREFIX": "poc-test-",
        }
    )
    with app.app_context():
        if not is_search_available():
            pytest.skip("OpenSearch is not running. Start it with `docker compose up -d`.")

        delete_test_indexes()
        seed_data()
        yield app
        delete_test_indexes()


@pytest.fixture
def canary_user(app):
    """A user with a post and a comment, all holding canary values."""
    user = User(email=CANARY_EMAIL, username=CANARY_USERNAME, full_name=CANARY_FULL_NAME)
    db.session.add(user)
    db.session.flush()

    post = Post(author=user, title="A canary post", body=CANARY_POST_BODY)
    db.session.add(post)
    db.session.flush()

    db.session.add(Comment(author=user, post=post, body="A comment"))
    db.session.commit()
    return user


def delete_test_indexes():
    """Delete every index with the test prefix, one by one by name."""
    client = search_client()
    existing_indexes = client.indices.get(index=prefix_index("*"), ignore=404)
    if "error" in existing_indexes:
        return
    for index_name in existing_indexes:
        client.indices.delete(index=index_name)


def find_canary_values_in_search(canary_values):
    """Return every index that still holds a canary value.

    It reads every document of every index with our prefix, so it also finds
    indexes nobody registered. For example: ["poc-test-users: canary-s4k"]
    """
    client = search_client()
    pattern = prefix_index("*")
    client.indices.refresh(index=pattern)

    response = client.search(index=pattern, body={"query": {"match_all": {}}, "size": MAX_DOCUMENTS})

    leaks = []
    for hit in response["hits"]["hits"]:
        text = json.dumps(hit["_source"])
        for canary_value in canary_values:
            if canary_value in text:
                leaks.append(f"{hit['_index']}: {canary_value}")
    return leaks


def find_document(index_name, document_id):
    """Return the source of one document, or None if it doesn't exist."""
    response = search_client().get(index=prefix_index(index_name), id=str(document_id), ignore=404)
    if not response.get("found"):
        return None
    return response["_source"]


def run_every_job(user_id):
    """Run every registered job as this user."""
    for job_id in REGISTERED_JOBS:
        run_job(job_id, user_id)
    search_client().indices.refresh(index=prefix_index(JOB_LOGS_INDEX))


#
# Prevention layer (CI)
#


def test_no_direct_writes_outside_the_allowlist():
    assert find_direct_writes(REPO_ROOT, PACKAGES) == []


def test_direct_write_check_catches_a_new_writer(tmp_path):
    new_module = tmp_path / "notes" / "views.py"
    new_module.parent.mkdir()
    new_module.write_text(
        "from search.client import search_client\n"
        "\n"
        "def save_note(note):\n"
        "    client = search_client()\n"
        "    client.index(index='notes', body={'email': note.email})\n"
        "\n"
        "def merge(a, b):\n"
        "    a.update(b)  # not the search client: not reported\n"
    )

    problems = find_direct_writes(tmp_path, ["notes"])

    assert problems == ["notes/views.py:5 writes to OpenSearch directly"]


def test_every_index_is_known(app):
    rebuild_all_indexes()
    run_every_job(user_id=1)

    assert find_unknown_indexes() == []


def test_unknown_index_check_catches_a_new_index(app):
    search_client().indices.create(index=prefix_index("notes"))

    assert find_unknown_indexes() == [prefix_index("notes")]


#
# Canary tests (CI)
#


def test_canary(app, canary_user):
    rebuild_all_indexes()
    run_every_job(canary_user.id)
    canary_post_id = canary_user.posts[0].id

    # The scan must see the canary before deletion, or it proves nothing.
    assert find_canary_values_in_search(CANARY_VALUES)

    delete_user_data(db.session, canary_user.id)

    assert find_canary_values_in_search(CANARY_VALUES) == []

    # The documents of anonymized rows are still there, with ids but without personal data.
    user_document = find_document("users", canary_user.id)
    assert user_document["email"] is None

    post_document = find_document("posts", canary_post_id)
    assert post_document["author"] == {"id": canary_user.id, "username": None}


def test_job_logs_canary(app, canary_user):
    """Every job runs while the canary user exists. None may log its personal data."""
    run_every_job(canary_user.id)

    assert find_canary_values_in_search(CANARY_VALUES) == []


def test_job_logs_canary_catches_a_job_that_logs_an_email(app, canary_user):
    def leaky_job():
        from flask import current_app

        users = db.session.scalars(db.select(User)).all()
        for user in users:
            current_app.logger.info(f"Sent digest to {user.email}")

    register_job("leaky_job", leaky_job)
    try:
        run_every_job(canary_user.id)
    finally:
        del REGISTERED_JOBS["leaky_job"]

    leaks = find_canary_values_in_search(CANARY_VALUES)

    # The username is part of the email, so it shows up too.
    assert f"{prefix_index(JOB_LOGS_INDEX)}: {CANARY_EMAIL}" in leaks


#
# Download
#


def test_download_includes_job_logs(app, canary_user):
    run_job("count_posts", canary_user.id)
    search_client().indices.refresh(index=prefix_index(JOB_LOGS_INDEX))

    zip_bytes = download_user_data(db.session, canary_user.id)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
        job_logs = json.loads(zip_file.read("job_logs.json"))

    assert len(job_logs) == 1
    assert job_logs[0]["context"] == {"job_id": "count_posts", "identity_id": str(canary_user.id)}
