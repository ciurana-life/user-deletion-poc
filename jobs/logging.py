"""Write job logs straight to OpenSearch, like ``invenio_jobs/logging/jobs.py``.

Only the message text and the job context are stored. The context holds ids
only, so it is fine to keep. The message is free text: a job could log an
email. The job logs canary test checks that none does.
"""

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

from search.client import prefix_index, search_client

JOB_LOGS_INDEX = "job-logs"

job_context = ContextVar("job_context", default=None)
"""Set while a job runs. For example: {"job_id": "send_digest", "identity_id": "3"}."""


@contextmanager
def set_job_context(context):
    """Mark the code inside the ``with`` block as part of a job run."""
    token = job_context.set(context)
    try:
        yield
    finally:
        job_context.reset(token)


class JobLogHandler(logging.Handler):
    """Logging handler that writes log lines to OpenSearch while a job runs."""

    def emit(self, record):
        context = job_context.get()

        # Outside a job, log lines only go to the console.
        if context is None:
            return

        document = {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "context": context,
        }
        search_client().index(index=prefix_index(JOB_LOGS_INDEX), body=document)
