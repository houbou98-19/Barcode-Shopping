import hmac
from functools import wraps

from flask import current_app, jsonify, request


def require_admin(fn):
    """Requires an X-Admin-Password header matching the ADMIN_PASSWORD env
    var - a single shared secret (obscurity of the /admin URL is the actual
    gate, per plan.md's "small trusted household" model; no per-profile
    admin role exists). If ADMIN_PASSWORD isn't configured, admin endpoints
    are disabled entirely rather than accepting any/no password."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        configured = current_app.config.get("ADMIN_PASSWORD")
        if not configured:
            return jsonify({"error": "admin access is not configured"}), 404

        provided = request.headers.get("X-Admin-Password", "")
        if not hmac.compare_digest(provided, configured):
            return jsonify({"error": "invalid admin password"}), 401

        return fn(*args, **kwargs)

    return wrapper
