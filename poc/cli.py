"""`flask seed` fills the database with demo data."""

import click

from jobs.registry import run_job
from search.indexer import rebuild_all_indexes
from search.indexes import REGISTERED_INDEXES

from .db import db
from .models import User
from .related_data_models import Comment, Post, Record


def seed_data():
    db.drop_all()
    db.create_all()

    alice = User(
        email="alice@example.org",
        username="alice",
        full_name="Alice Liddell",
        affiliation="CERN",
        last_login_ip="10.0.0.1",
    )
    bob = User(
        email="bob@example.org",
        username="bob",
        full_name="Bob Builder",
        affiliation="EPFL",
        last_login_ip="10.0.0.2",
    )
    carol = User(email="carol@example.org", username="carol", full_name="Carol Danvers")
    db.session.add_all([alice, bob, carol])
    db.session.flush()

    p1 = Post(author=alice, title="Hello from Alice", body="My first post.")
    p2 = Post(author=alice, title="Datasets I like", body="Some links.")
    p3 = Post(author=bob, title="Bob's notes", body="Building things.")
    db.session.add_all([p1, p2, p3])

    db.session.add_all(
        [
            Comment(author=bob, post=p1, body="Welcome Alice!"),
            Comment(author=alice, post=p3, body="Nice notes, Bob."),
            Comment(author=carol, post=p1, body="Hi both."),
        ]
    )

    def record(owner, title, creators):
        return Record(
            data={
                "access": {"owned_by": {"user": str(owner.id)}},
                "metadata": {
                    "title": title,
                    "creators": [{"name": n} for n in creators],
                },
            }
        )

    db.session.add_all(
        [
            record(alice, "Alice's dataset", ["Liddell, Alice"]),
            record(alice, "Joint paper", ["Liddell, Alice", "Builder, Bob"]),
            record(bob, "Bob's software", ["Builder, Bob"]),
        ]
    )
    db.session.commit()


def register(app):
    @app.cli.command("seed")
    def seed():
        """Reset the database and insert demo data."""
        seed_data()
        click.echo("Seeded: 3 users, 3 posts, 3 comments, 3 records.")

    @app.cli.command("reindex")
    def reindex():
        """Rebuild every OpenSearch index from the database."""
        rebuild_all_indexes()
        click.echo(f"Rebuilt: {', '.join(REGISTERED_INDEXES)}.")

    @app.cli.command("run-job")
    @click.argument("job_id")
    @click.option("--user-id", default=1, help="The user who starts the job.")
    def run_job_command(job_id, user_id):
        """Run a job. Its log lines are written to the job logs index."""
        run_job(job_id, user_id)
        click.echo(f"Ran {job_id} as user {user_id}.")
