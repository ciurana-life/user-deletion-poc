"""The OpenSearch client, like ``current_search_client`` in invenio-search."""

from flask import current_app
from opensearchpy import OpenSearch


def search_client():
    """Return the OpenSearch client of the current app.

    It is created on first use, so the app starts even when OpenSearch is down.
    """
    client = current_app.extensions.get("search_client")
    if client is None:
        client = OpenSearch(hosts=[current_app.config["SEARCH_HOST"]])
        current_app.extensions["search_client"] = client
    return client


def prefix_index(name):
    """Return the real index name, with the prefix from the config.

    For example, "users" returns "poc-users". Tests use another prefix, so
    they don't touch the indexes of the running app.
    """
    return current_app.config["SEARCH_INDEX_PREFIX"] + name


def is_search_available():
    """Return True if OpenSearch answers."""
    return search_client().ping()
