"""Startup: send job log lines to OpenSearch and register the download."""

import logging

from poc.user_data.policy import register_external_download_function

from .logging import JobLogHandler
from .policy import download_job_logs


def init_jobs(app):
    """Install the job log handler on the app logger and register the job logs download."""
    app.config.setdefault("JOBS_LOGGING_RETENTION_DAYS", 30)

    # Creating the app twice (for example in tests) must not add a second handler.
    has_handler = False
    for handler in app.logger.handlers:
        if isinstance(handler, JobLogHandler):
            has_handler = True

    if not has_handler:
        app.logger.addHandler(JobLogHandler())

    # Without this, INFO lines never reach the handler (the default level is WARNING).
    app.logger.setLevel(logging.INFO)

    register_external_download_function("job_logs", download_job_logs)
