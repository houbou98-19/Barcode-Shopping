import hashlib
import secrets
from datetime import datetime, timedelta, timezone

SESSION_DAYS = 7


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create(conn, profile_id):
    """Returns the raw token (only place it exists outside the client) and
    its expiry. Only the SHA-256 hash is stored, so a leaked DB file alone
    can't be used to replay a session (same rationale as profiles.pin_hash)."""
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    conn.execute(
        "INSERT INTO sessions (token_hash, profile_id, expires_at) VALUES (?, ?, ?)",
        (_hash(token), profile_id, expires_at),
    )
    conn.commit()
    return {"token": token, "expires_at": expires_at}
