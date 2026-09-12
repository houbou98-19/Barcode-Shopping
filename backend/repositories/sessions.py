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


def get_valid_profile_id(conn, token):
    """Returns the session's profile_id if `token` is valid and unexpired,
    else None. Refreshes expires_at on every successful use (sliding
    expiry), so a profile used at least once a week never sees a prompt."""
    row = conn.execute(
        "SELECT profile_id, expires_at FROM sessions WHERE token_hash = ?", (_hash(token),)
    ).fetchone()
    if row is None:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        return None

    new_expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE token_hash = ?", (new_expires_at, _hash(token))
    )
    conn.commit()
    return row["profile_id"]
