# User deletion PoC

A minimal Flask + Flask-SQLAlchemy app (the same stack as Invenio) for prototyping how to find, export and delete everything that belongs to a user.

This repo aims to do a PoC of:
1. Preventing future changes to continue without the correct data labeling (Postgres).
2. Preventing future changes to continue without the correct data labeling (Opensearch).
3. Preventing future changes to continue without the correct data labeling (audit Log).
4. Canary test.

## 1. Preventing future changes to continue without the correct data labeling (Postgres).

This is important because in the future a new developer might not know that the data he is
adding is related to the user in a way that he needs to keep track of and decide how 
to treat that data in the event of a user requesting deletion or download of it. This data
labeling will inform the future delete/download functions on what to do with it.

If you run `uv run pytest` or `uv run flask --app poc run` both will fail, because most of
the defined classes are missing attributes that will inform the application on how to 
deal with data related to the user.

The error that will be shown right now:
```bash
TypeError: Unclassified user data:
 accounts_user.email: missing info= etc etc
 accounts_user.username: missing info= etc etc
 ...
 thumbnail: set the arguments etc etc
 thumbnail.img: missing info= etc etc
 Please visit ... for more info
```

TODO POC:
build the deletion strategy when the first pass to check labels is done.

It is still a PoC, so some things are missing:
1. Error shows the name of parent class instead of child.
2. Error shows `etc etc` instead of a useful message.
3. Error can be formatted in a more user friendly way.
4. `__table_args__` not defined.
5. Anotations of types.

## 2. Preventing future changes to continue without the correct data labeling (Opensearch).

Most of what is in OpenSearch is indexed from Postgres. So if the Postgres columns are labeled, we
already know what user data ends up in those indexes, and a reindex after deleting the user cleans them.

The problem is code that writes straight to OpenSearch without going through Postgres. That data
never passes the label check from #1, so we can't see it. Right now these are the direct writers:
- invenio-jobs job logs: every `current_app.logger` call made during a job run is indexed, at DEBUG
  level by default, together with the id of the user that started the run. Only the message text is
  stored. Today the jobs in Zenodo log record ids, counts and, for the vocabulary imports, ORCID
  entries (public data, not Zenodo accounts), so no emails or names of our users. The risk is error
  messages that include the exception text, and future jobs that log user data in the message.

- invenio-stats events: already anonymized before indexing, so nothing to do.
- invenio-indexer, invenio-search and invenio-audit-logs: they write to OpenSearch but the data
  comes from Postgres or is covered in #3.

A document that only holds the user id is fine, because the account row is anonymized and the ids are kept.
Only copies of email, name, IP and similar need action.


To stop new direct writers from showing up unnoticed, CI will scan the installed invenio packages
for direct `current_search_client` writes and compare them against an allowlist. If someone adds a new
one, CI fails and they have to decide how that data is labeled before it gets added to the list.
This check will live in invenio-app-rdm, because its CI installs the whole RDM stack.

invenio-jobs is on that allowlist, so the check above won't notice if a job starts logging user data.
Jobs need their own check for that. Like the canary test in #3, CI will create a test user with a
known email and name, run every registered job, and then search the job logs index for that email
and name. If they show up, CI fails.

TODO POC:
1. Build the allowlist check.
2. Build the job logs canary check.
3. Set `JOBS_LOGGING_RETENTION_DAYS` explicitly.


## 3. Preventing future changes to continue without the correct data labeling (audit Log).

Here the task of tracking what is related to the user gets a bit harder because of the lack of foreign keys; tho right now most of the logs have user data.

The same strategy of labeling every field as with postgress will be used here, and the app won't run unless all the data has a label. The label check on startup also keeps track of all trables and labels so that later the deletion action might be done easily.

To ensure that the data is correctly labeld CI will run a canary test that will write one of every auditLog that exists, and then run the action to delete the user, after that we will check if user identifiable data is still in the database.
(plus opensearch indexes)

And finally models will implement a new `__init_subclass__` that will check that no one creates an audit-log model outisde of invenio-audit-log, this is needed because if a developer creates an audit-log model outside of invenio-audit-log our canary test won't be able to know it even exists.


TODO: 
PoC + first pass deletion strategy like in #1

## Run

```bash
uv sync
uv run flask --app poc seed     # reset DB + demo data
uv run flask --app poc run      # http://127.0.0.1:5000
uv run pytest
```