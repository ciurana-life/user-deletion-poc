"""Models covering the ways user data is linked in Invenio.

- User      -> the account (like invenio-accounts' accounts_user).
- Post      -> direct foreign key to the user.
- Comment   -> foreign key to the user AND to someone else's post.
- Record    -> NO foreign key: the owner lives inside JSON as {"user": "<id>"},
               like RDM's parent.access.owned_by. Its metadata can also hold
               personal data (creator names) with no id at all.
"""

from .db import Timestamp, db
from . import user_data   # noqa: E402,F401  registers the mapper listener for every model
# from .user_data import UserData

# # Not realy working for every scenario
# # TODO - move to another file
# # TODO - enum ?
# POLICIES = ("delete", "anonymize")

# class UserData():
#     """ Aims to keep track all data related to the user in the db, so that
#     it can easily be deleted (or anonymized) or downloaded for that user.

#     Every class that inherits from ``UserData`` must set a ``user_data_policy`` attribute,
#     this is enforced with the ``__init_subclass__`` method that runs at class definition time:
#     if the attribute is missing or not on the ``POLICIES`` a TypeError is raised and
#     the module defining the class fails to import.
#     """

#     def __init_subclass__(cls, **kwargs):
#         super().__init_subclass__(**kwargs)
#         if not hasattr(cls, "user_data_policy"):
#             # TODO - more informative error message?
#             raise TypeError(f"{cls.__name__}: set user_data_policy to one of {POLICIES} [1]")
#         if cls.user_data_policy not in POLICIES:
#             # TODO - more informative error message?
#             raise TypeError(f"{cls.__name__}: set user_data_policy to one of {POLICIES} [2]")


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

