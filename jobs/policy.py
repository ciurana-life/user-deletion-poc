"""Policy layer for job logs.

* Download: the user's job logs, found by the id of the user who started the job.
* Delete: nothing on user deletion. The logs only hold ids (checked by the
  canary test), and every log is deleted after ``JOBS_LOGGING_RETENTION_DAYS``
  anyway.
"""

from flask import current_app

from search.client import prefix_index, search_client

from .logging import JOB_LOGS_INDEX

MAX_DOWNLOADED_LOGS = 10_000
"""Enough for the PoC. A real export would page through the results with ``search_after``."""


def download_job_logs(user_id):
    """Return the job logs of the jobs this user started.

    For example:
        [{"@timestamp": "...", "level": "INFO", "message": "Sent 3 digests",
          "context": {"job_id": "send_digest", "identity_id": "1"}}]
    """
    # Only for tests that run without OpenSearch.
    if not current_app.config["SEARCH_ENABLED"]:
        return []

    query = {"term": {"context.identity_id.keyword": str(user_id)}}
    response = search_client().search(
        index=prefix_index(JOB_LOGS_INDEX),
        body={"query": query, "size": MAX_DOWNLOADED_LOGS},
        ignore=404,
    )

    # No job has run yet, so the index doesn't exist.
    if "error" in response:
        return []

    documents = []
    for hit in response["hits"]["hits"]:
        documents.append(hit["_source"])
    return documents


def delete_old_logs():
    """Delete job logs older than ``JOBS_LOGGING_RETENTION_DAYS``. Runs daily in Invenio."""
    retention_days = current_app.config["JOBS_LOGGING_RETENTION_DAYS"]
    query = {"range": {"@timestamp": {"lt": f"now-{retention_days}d/d"}}}

    search_client().delete_by_query(
        index=prefix_index(JOB_LOGS_INDEX),
        body={"query": query},
        ignore=404,
    )
