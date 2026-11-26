"""Startup: connect the OpenSearch policy to user deletion."""

from poc.user_data.policy import register_after_delete

from .policy import reindex_after_user_deletion


def init_search(app):
    """Reindex the user's documents after every user deletion.

    Like audit logs, this package calls into the user data module, and the user
    data module never imports it.
    """
    app.config.setdefault("SEARCH_HOST", "http://localhost:19200")
    app.config.setdefault("SEARCH_INDEX_PREFIX", "poc-")
    app.config.setdefault("SEARCH_ENABLED", True)

    register_after_delete("search", reindex_after_user_deletion)
