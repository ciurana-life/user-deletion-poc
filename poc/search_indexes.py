"""The indexes of this app, like the users, records and community members indexes in Zenodo.

Each one is built from a table by a dump function. Some documents copy user
data from another table, like the community members index copies the member's
email and username in Zenodo. Here posts and comments copy the author's username.
"""

from search.indexes import register_index

from .models import User
from .related_data_models import Comment, Post


def dump_author(user):
    """Return the author part of a document.

    For example: {"id": 1, "username": "alice"}
    """
    return {"id": user.id, "username": user.username}


def dump_user(user):
    """Return the document of a user, like Zenodo's users index.

    For example:
        {"id": 1, "email": "alice@example.org", "username": "alice",
         "full_name": "Alice Liddell", "affiliation": "CERN", "active": True}
    """
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "affiliation": user.affiliation,
        "active": user.active,
    }


def dump_post(post):
    """Return the document of a post.

    For example:
        {"id": 1, "title": "Hello from Alice", "body": "My first post.",
         "author": {"id": 1, "username": "alice"}}
    """
    return {
        "id": post.id,
        "title": post.title,
        "body": post.body,
        "author": dump_author(post.author),
    }


def dump_comment(comment):
    """Return the document of a comment.

    For example:
        {"id": 1, "body": "Welcome Alice!", "post_id": 1,
         "author": {"id": 2, "username": "bob"}}
    """
    return {
        "id": comment.id,
        "body": comment.body,
        "post_id": comment.post_id,
        "author": dump_author(comment.author),
    }


register_index("users", User, dump_user)
register_index("posts", Post, dump_post)
register_index("comments", Comment, dump_comment)
