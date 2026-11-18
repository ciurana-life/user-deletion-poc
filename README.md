# User deletion PoC

A minimal Flask + Flask-SQLAlchemy app (the same stack as Invenio) for prototyping how to find, export and delete everything that belongs to a user.

## Data model

| Table           | How it points at the user                              | Invenio equivalent                       |
|-----------------|--------------------------------------------------------|------------------------------------------|
| `accounts_user` | is the user                                            | `invenio_accounts.models.User`           |
| `posts`         | foreign key `user_id`                                  | any model with an FK to `accounts_user`  |
| `comments`      | foreign key `user_id`, attached to *anyone's* post     | request comments, community members      |
| `records`       | **no FK**: JSON `access.owned_by.user = "<id>"`        | RDM `parent.access.owned_by`             |

Records also contain personal data with no id at all (`metadata.creators[].name`).

All models use a `Timestamp` mixin (`created`, `updated`) like invenio-db's.

## Run

```bash
uv sync
uv run flask --app poc seed     # reset DB + demo data
uv run flask --app poc run      # http://127.0.0.1:5000
uv run pytest
```