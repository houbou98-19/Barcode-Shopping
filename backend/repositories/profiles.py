from datetime import datetime, timedelta, timezone

from werkzeug.security import check_password_hash, generate_password_hash

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _now():
    return datetime.now(timezone.utc)


def _parse(ts):
    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)


def _public(row):
    """Profile shape safe to return over the API - never includes pin_hash."""
    return {
        "id": row["id"],
        "name": row["name"],
        "created_at": row["created_at"],
    }


def get_all(conn):
    rows = conn.execute("SELECT * FROM profiles ORDER BY name").fetchall()
    return [_public(row) for row in rows]


def get_by_id(conn, profile_id):
    row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    return row


def name_exists(conn, name):
    row = conn.execute("SELECT 1 FROM profiles WHERE name = ?", (name,)).fetchone()
    return row is not None


def create(conn, name, pin):
    pin_hash = generate_password_hash(pin)
    cur = conn.execute(
        "INSERT INTO profiles (name, pin_hash) VALUES (?, ?)",
        (name, pin_hash),
    )
    conn.commit()
    return _public(get_by_id(conn, cur.lastrowid))


def is_locked(profile_row):
    if profile_row["locked_until"] is None:
        return False
    return _parse(profile_row["locked_until"]) > _now()


def _register_failure(conn, profile_row):
    attempts = profile_row["failed_attempts"] + 1
    locked_until = None
    if attempts >= MAX_FAILED_ATTEMPTS:
        locked_until = (_now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
        attempts = 0
    conn.execute(
        "UPDATE profiles SET failed_attempts = ?, locked_until = ? WHERE id = ?",
        (attempts, locked_until, profile_row["id"]),
    )
    conn.commit()


def _reset_failures(conn, profile_id):
    conn.execute(
        "UPDATE profiles SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
        (profile_id,),
    )
    conn.commit()


def verify_pin(conn, profile_id, pin):
    """Returns True/False for whether `pin` matches the profile's stored PIN.
    Locking out and attempt-counting is handled here rather than by the
    caller, since it must happen atomically with the check itself."""
    profile_row = get_by_id(conn, profile_id)
    if profile_row is None:
        return False
    if is_locked(profile_row):
        return False

    if check_password_hash(profile_row["pin_hash"], pin):
        _reset_failures(conn, profile_id)
        return True

    _register_failure(conn, profile_row)
    return False
