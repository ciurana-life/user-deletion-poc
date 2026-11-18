"""Models covering the ways user data is linked in Invenio.

- User      -> the account (like invenio-accounts' accounts_user).
- Post      -> direct foreign key to the user.
- Comment   -> foreign key to the user AND to someone else's post.
- Record    -> NO foreign key: the owner lives inside JSON as {"user": "<id>"},
               like RDM's parent.access.owned_by. Its metadata can also hold
               personal data (creator names) with no id at all.
"""

from .db import Timestamp, db


class User(db.Model, Timestamp):
    __tablename__ = "accounts_user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(255), unique=True)
    full_name = db.Column(db.String(255))
    affiliation = db.Column(db.String(255))
    last_login_ip = db.Column(db.String(64))
    active = db.Column(db.Boolean, default=True, nullable=False)

    posts = db.relationship("Post", back_populates="author")
    comments = db.relationship("Comment", back_populates="author")

    def __repr__(self):
        return f"<User {self.id} {self.email}>"


class Post(db.Model, Timestamp):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text)

    author = db.relationship(User, back_populates="posts")
    comments = db.relationship("Comment", back_populates="post")


class Comment(db.Model, Timestamp):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey(Post.id), nullable=False)
    body = db.Column(db.Text, nullable=False)

    author = db.relationship(User, back_populates="comments")
    post = db.relationship(Post, back_populates="comments")


class Record(db.Model, Timestamp):
    __tablename__ = "records"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.JSON, nullable=False, default=dict)

    @classmethod
    def owned_by(cls, user_id):
        """Records whose JSON says {"access": {"owned_by": {"user": "<id>"}}}."""
        owner = cls.data["access"]["owned_by"]["user"].as_string()
        return cls.query.filter(owner == str(user_id))

    @property
    def title(self):
        return self.data.get("metadata", {}).get("title", "")
