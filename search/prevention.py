"""Prevention layer for OpenSearch: find data that skips Postgres.

The registered indexes are copies of Postgres rows, so the Postgres labels
already cover them. The risk is code that writes to OpenSearch directly: that
data never passes the label check. Two CI checks catch it:

1. ``find_direct_writes``: reads the source code and lists every call that
   writes to OpenSearch. Only the modules in ``ALLOWED_DIRECT_WRITERS`` may
   write. In Invenio this check would live in invenio-app-rdm, because its CI
   installs the whole RDM stack.
2. ``find_unknown_indexes``: lists the indexes that exist in OpenSearch but
   that nobody declared, for example one created by hand or by a new package.

Neither check runs at startup: the first one reads files and the second one
needs OpenSearch to be running.
"""

import ast
from pathlib import Path

from .client import prefix_index, search_client
from .indexes import REGISTERED_INDEXES

ALLOWED_DIRECT_WRITERS = {
    "search.indexer": [],
    "jobs.logging": ["job-logs"],
    "jobs.policy": ["job-logs"],
}
"""Modules that may write to OpenSearch, and the indexes they own besides the registered ones.

* ``search.indexer`` writes the registered indexes from Postgres.
* ``jobs.logging`` writes job logs straight to OpenSearch. They must only hold
  ids. The job logs canary test checks that.
* ``jobs.policy`` deletes job logs older than the retention period.

Adding a module here means someone decided how its data is handled on user deletion.
"""

WRITE_METHODS = (
    "index",
    "create",
    "update",
    "delete",
    "bulk",
    "update_by_query",
    "delete_by_query",
)
"""Client methods that change data, on the client or on ``client.indices``."""


def find_client_variables(tree):
    """Return the names of variables that hold the search client.

    For example, ``client = search_client()`` returns {"client"}.
    """
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if ast.unparse(node.value) != "search_client()":
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def is_search_client(expression, client_variables):
    """Return True if the expression is the search client or its ``indices`` part.

    For example: ``search_client()``, ``search_client().indices`` or ``client``
    when ``client = search_client()``.
    """
    text = ast.unparse(expression)
    if text.startswith("search_client()"):
        return True

    first_name = text.split(".")[0]
    return first_name in client_variables


def is_bulk_helper(call):
    """Return True for ``helpers.bulk(...)`` from opensearch-py, which writes without the client methods."""
    return ast.unparse(call.func) in ("helpers.bulk", "opensearchpy.helpers.bulk")


def find_writes_in_file(path):
    """Return the line numbers where this file writes to OpenSearch.

    For example: [12, 30]
    """
    tree = ast.parse(Path(path).read_text())
    client_variables = find_client_variables(tree)

    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if is_bulk_helper(node):
            lines.append(node.lineno)
            continue

        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in WRITE_METHODS:
            continue
        if is_search_client(node.func.value, client_variables):
            lines.append(node.lineno)

    return sorted(lines)


def module_name(path, root):
    """Return the dotted module name of a file.

    For example, "<root>/jobs/logging.py" returns "jobs.logging".
    """
    relative_path = Path(path).relative_to(root).with_suffix("")
    return ".".join(relative_path.parts)


def find_direct_writes(root, packages):
    """Return every OpenSearch write outside the allowed modules.

    For example: ["poc/views.py:42 writes to OpenSearch directly"]
    """
    problems = []

    for package in packages:
        for path in sorted(Path(root, package).rglob("*.py")):
            name = module_name(path, root)
            if name in ALLOWED_DIRECT_WRITERS:
                continue

            for line in find_writes_in_file(path):
                relative_path = Path(path).relative_to(root)
                problems.append(f"{relative_path}:{line} writes to OpenSearch directly")

    return problems


def known_index_names():
    """Return the full names of every index we know about: registered or owned by an allowed module."""
    names = set()

    for index_name in REGISTERED_INDEXES:
        names.add(prefix_index(index_name))

    for owned_indexes in ALLOWED_DIRECT_WRITERS.values():
        for index_name in owned_indexes:
            names.add(prefix_index(index_name))

    return names


def find_unknown_indexes():
    """Return the indexes with our prefix that exist in OpenSearch but nobody declared.

    For example: ["poc-test-notes"]
    """
    pattern = prefix_index("*")
    existing_indexes = search_client().indices.get(index=pattern, ignore=404)

    # A 404 answer is a dict with an "error" key, not a list of indexes.
    if "error" in existing_indexes:
        return []

    known_names = known_index_names()

    unknown = []
    for index_name in sorted(existing_indexes):
        if index_name not in known_names:
            unknown.append(index_name)
    return unknown
