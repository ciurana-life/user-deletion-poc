from .db import Timestamp, db

class User(db.Model, Timestamp):
    __tablename__ = "accounts_user"
    user_data_policy = "anonymize"

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

class ChildUser(User):
    """Example of child class
    """
    something = db.Column(db.String(255))

class GrandChild(ChildUser):
    """Example of more deep inheritance
    """
    something_else = db.Column(db.String(255))

class UnrelatedDataOne(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
