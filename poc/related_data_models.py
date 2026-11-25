from .db import Timestamp, db
from .models import User

class Post(db.Model, Timestamp):
    """Example of ForeignKey data related to user
    """
    __tablename__ = "posts"
    # Anonymize, not delete: other users' comments point at the posts.
    __table_args__ = {"info": {"user_data": "anonymize"}}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    title = db.Column(db.String(255), nullable=False, info={"user_data": "keep"})
    body = db.Column(db.Text, info={"user_data": "scrub"})

    author = db.relationship(User, back_populates="posts")
    comments = db.relationship("Comment", back_populates="post")


class Thumbnail(db.Model, Timestamp):
    __tablename__ = "thumbnail"
    __table_args__ = {"info": {"user_data": "delete"}}

    id = db.Column(db.Integer, primary_key=True)
    img = db.Column(db.Integer, info={"user_data": "keep"})
    post = db.Column(db.Integer, db.ForeignKey(Post.id), nullable=False)
    ...
    # TODO

class MetaThumbnail(db.Model, Timestamp):
    __tablename__ = "meta_thumbnail"
    __table_args__ = {"info": {"user_data": "delete"}}

    id = db.Column(db.Integer, primary_key=True)
    img = db.Column(db.Integer, info={"user_data": "keep"})
    post = db.Column(db.Integer, db.ForeignKey(Thumbnail.id), nullable=False)

class Comment(db.Model, Timestamp):
    __tablename__ = "comments"
    # Kept like on GitHub: the comment stays and the author shows as "Deleted user".
    __table_args__ = {"info": {"user_data": "anonymize"}}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey(Post.id), nullable=False)
    body = db.Column(db.Text, nullable=False, info={"user_data": "keep"})

    author = db.relationship(User, back_populates="comments")
    post = db.relationship(Post, back_populates="comments")

class UnrelatedDataTwo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)

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
