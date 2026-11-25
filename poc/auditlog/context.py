"""Context resolvers: they add data to an audit log before it is stored."""

from flask import has_request_context, request, session


class UserContext:
    """Copy the user who did the action into ``user``."""

    def __call__(self, data, user=None, **kwargs):
        data["user"] = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
        }


class RequestContext:
    """Add the IP address and the session id of the current request."""

    def __call__(self, data, **kwargs):
        metadata = data.setdefault("metadata", {})

        # No HTTP request, for example in a background task.
        if not has_request_context():
            metadata["ip_address"] = "N/A"
            return

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            metadata["ip_address"] = forwarded_for.split(",")[0].strip()
        else:
            metadata["ip_address"] = request.remote_addr or "untrackable"

        session_id = session.get("_id")
        if session_id:
            metadata["session"] = session_id


class ValuesContext:
    """Copy keyword arguments into ``metadata``, for example the post title."""

    def __init__(self, *names):
        self.names = names

    def __call__(self, data, **kwargs):
        metadata = data.setdefault("metadata", {})
        for name in self.names:
            if name in kwargs:
                metadata[name] = kwargs[name]
