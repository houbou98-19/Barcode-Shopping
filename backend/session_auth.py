from functools import wraps

from flask import current_app, g, jsonify, request

from db import get_db
from repositories import sessions as sessions_repo


def require_session(fn):
    """Requires a valid `Authorization: Bearer <token>` header, refreshing
    the session's sliding expiry on use. Sets g.profile_id for the route."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "authentication required"}), 401

        token = auth_header[len("Bearer ") :]
        conn = get_db(current_app.config["DATABASE_PATH"])
        profile_id = sessions_repo.get_valid_profile_id(conn, token)
        if profile_id is None:
            return jsonify({"error": "invalid or expired session"}), 401

        g.profile_id = profile_id
        return fn(*args, **kwargs)

    return wrapper
