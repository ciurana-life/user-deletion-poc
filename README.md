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