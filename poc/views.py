"""Pages that show everything linked to a user."""

from flask import Blueprint, render_template

from .db import db
from .models import Record, User

bp = Blueprint("poc", __name__)


@bp.route("/")
def index():
    users = db.session.scalars(db.select(User).order_by(User.id)).all()
    return render_template("index.html", users=users)


@bp.route("/users/<int:user_id>")
def user_detail(user_id):
    user = db.get_or_404(User, user_id)
    records = Record.owned_by(user.id).all()
    return render_template("user.html", user=user, records=records)
