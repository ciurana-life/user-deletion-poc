"""Stand-in for invenio-jobs, the one package that writes to OpenSearch directly.

* ``registry``: jobs register here and run with a job context (who started them).
* ``logging``:  while a job runs, every ``current_app.logger`` call is written
                to the job logs index, with the id of the user who started it.
                Like invenio-jobs, it skips Postgres.
* ``policy``:   download of a user's job logs, and the retention cleanup.
* ``ext``:      ``init_jobs(app)``, installs the log handler and registers the download.
"""
