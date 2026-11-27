```python
class AccessRequestToken(db.Model):
    __tablename__ = "rdm_records_access_request_tokens"
    __table_args__ = {"info": {"user_data": "delete"}}

    email = db.Column(
        db.String,
        info={"user_data": "scrub", "copy_of": "accounts_user.email"},
    )
    full_name = db.Column(db.String, info={"user_data": "scrub"})
```

Will need indexes, comparing with lower() etc.

And enforce EVERY table has to at least have:
```python
__table_args__ = {"info": {"user_data": "none"}}       # no personal data, no link to a user
__table_args__ = {"info": {"user_data": "anonymize"}}
__table_args__ = {"info": {"user_data": "delete"}}
```
none tables dont get every column scanned.