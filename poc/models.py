from .db import Timestamp, db

class User(db.Model, Timestamp):
    __tablename__ = "accounts_user"

    id = db.Column(db.Integer, primary_key=True)
    # Nullable, like in invenio-accounts, so deletion can set it to NULL.
    email = db.Column(db.String(255), unique=True, info={"user_data": "scrub"})
    username = db.Column(db.String(255), unique=True, info={"user_data": "scrub"})
    full_name = db.Column(db.String(255), info={"user_data": "scrub"})
    affiliation = db.Column(db.String(255), info={"user_data": "scrub"})
    last_login_ip = db.Column(db.String(64), info={"user_data": "scrub"})
    # TODO: deletion should set this to False. That needs a "replace_with"
    # label, because the column is NOT NULL and can't be scrubbed to NULL.
    active = db.Column(db.Boolean, default=True, nullable=False, info={"user_data": "keep"})

    posts = db.relationship("Post", back_populates="author")
    comments = db.relationship("Comment", back_populates="author")

    def __repr__(self):
        return f"<User {self.id} {self.email}>"

class ChildUser(User):
    """Example of child class
    """
    something = db.Column(db.String(255), info={"user_data": "scrub"})

class GrandChild(ChildUser):
    __tablename__ = "grand_child"
    """Example of more deep inheritance
    """
    something_else = db.Column(db.String(255), info={"user_data": "scrub"})

class UnrelatedDataOne(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
