"""Registered jobs, and running one with a job context."""

from .logging import set_job_context

REGISTERED_JOBS = {}
"""Jobs that can be run, keyed by job id. Stand-in for the ``invenio_jobs.jobs`` entry point."""


def register_job(job_id, function):
    """Register a job. The function takes no arguments and logs with ``current_app.logger``.

    For example: ``register_job("send_digest", send_digest)``.
    """
    REGISTERED_JOBS[job_id] = function


def run_job(job_id, identity_id):
    """Run a job as the given user. Its log lines go to the job logs index."""
    function = REGISTERED_JOBS[job_id]
    context = {"job_id": job_id, "identity_id": str(identity_id)}

    with set_job_context(context):
        function()
