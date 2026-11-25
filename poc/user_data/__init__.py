"""Classify user data in the database so it can be deleted, anonymized or exported.

* ``common``:     labels, policies and helpers used by both layers.
* ``prevention``: refuses to start the app if user data is unclassified.
* ``policy``:     builds the SQL that deletes or downloads a user's data.
* ``events``:     the startup hook that runs both.

Importing this package registers the startup hook.
"""

from . import events  # noqa: F401  registers the after_configured listener
from .policy import delete_user_data, download_user_data

__all__ = ("delete_user_data", "download_user_data")
