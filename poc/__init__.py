"""Minimal app to prototype user-data deletion."""
import sqlalchemy as sa
from flask import Flask

from .db import db

def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite:///poc.db",
        SECRET_KEY="dev",
    )
    if config:
        app.config.update(config)

    db.init_app(app)


    from . import models, related_data_models  # noqa: F401  load every model
    from . import user_data   # noqa: E402,F401  registers the mapper listener for every model
    sa.orm.configure_mappers()  # This is what InvenioDB does before starting.

    from . import cli, views

    app.register_blueprint(views.bp)
    cli.register(app)

    with app.app_context():
        db.create_all()

    return app
