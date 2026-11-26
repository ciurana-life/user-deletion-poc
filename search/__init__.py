"""Stand-in for invenio-search and invenio-indexer.

* ``client``:     the OpenSearch client and index name prefix.
* ``indexes``:    the registry of indexes built from Postgres. Other packages
                  register their indexes here, with a function that turns a
                  row into a document.
* ``indexer``:    reads rows from Postgres and writes them to OpenSearch. The
                  only module that writes the registered indexes.
* ``prevention``: the CI checks: who may write to OpenSearch directly, and
                  which indexes may exist.
* ``policy``:     after a user is deleted, reindex or delete their documents.
* ``ext``:        ``init_search(app)``, hands the policy to the user data module.
"""
