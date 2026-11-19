# User deletion PoC

A minimal Flask + Flask-SQLAlchemy app (the same stack as Invenio) for prototyping how to find, export and delete everything that belongs to a user.

This repo aims to do a PoC of:
1. Preventing future changes to continue without the correct data labeling (Postgres).
2. Preventing future changes to continue without the correct data labeling (Opensearch).
3. Canary test.

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

It is still a PoC, so some things are missing:
1. Error shows the name of parent class instead of child.
2. Error shows `etc etc` instead of a useful message.
3. Error can be formatted in a more user friendly way.
4. `__table_args__` not defined.
5. Anotations of types.

## Run

```bash
uv sync
uv run flask --app poc seed     # reset DB + demo data
uv run flask --app poc run      # http://127.0.0.1:5000
uv run pytest
```