"""Jobs of this app, registered from outside the jobs package (like rdm-records does).

They log ids and counts only. Logging an email or a name here would copy it into
the job logs index, and the job logs canary test would fail.
"""

from flask import current_app

from jobs.registry import register_job

from .db import db
from .models import User
from .related_data_models import Post


def send_digest():
    """Pretend to email every active user a digest of new posts."""
    users = db.session.scalars(db.select(User).filter_by(active=True)).all()
    for user in users:
        current_app.logger.info(f"Sent digest to user {user.id}")
    current_app.logger.info(f"Sent {len(users)} digests")


def count_posts():
    """Log how many posts exist."""
    total = db.session.scalar(db.select(db.func.count(Post.id)))
    current_app.logger.info(f"There are {total} posts")


register_job("send_digest", send_digest)
register_job("count_posts", count_posts)
