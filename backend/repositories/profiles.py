from datetime import datetime, timedelta, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from repositories import lists as lists_repo

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


def get_all_admin(conn):
    """Admin overview shape: still never includes pin_hash, but adds the
    lockout state a regular profile listing has no business exposing."""
    rows = conn.execute("SELECT * FROM profiles ORDER BY name").fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "failed_attempts": row["failed_attempts"],
            "locked_until": row["locked_until"],
            "is_locked": is_locked(row),
        }
        for row in rows
    ]


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
    lists_repo.create_personal(conn, cur.lastrowid, f"{name}'s list")
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


def reset_pin(conn, profile_id, pin):
    """Also clears any lockout - a freshly-set PIN shouldn't still be
    blocked by attempts made against the old one."""
    pin_hash = generate_password_hash(pin)
    conn.execute(
        "UPDATE profiles SET pin_hash = ?, failed_attempts = 0, locked_until = NULL WHERE id = ?",
        (pin_hash, profile_id),
    )
    conn.commit()


def clear_lockout(conn, profile_id):
    _reset_failures(conn, profile_id)


def delete(conn, profile_id):
    """Cascades manually (no ON DELETE CASCADE in schema.sql):
    - sessions: logs them out everywhere.
    - their memberships: removed from every list they were in; a list left
      with no members (their personal list, always; a shared list if they
      were the last one in it) is deleted along with its items.
    - items they personally added to any list they *don't* end up removing
      (a shared list other members remain in) - deleted individually so no
      shopping_list_items.added_by_profile_id is left dangling.
    - the profile row itself.
    """
    conn.execute("DELETE FROM sessions WHERE profile_id = ?", (profile_id,))

    list_ids = [
        row["list_id"]
        for row in conn.execute(
            "SELECT list_id FROM list_memberships WHERE profile_id = ?", (profile_id,)
        ).fetchall()
    ]
    conn.execute("DELETE FROM list_memberships WHERE profile_id = ?", (profile_id,))
    conn.commit()
    for list_id in list_ids:
        lists_repo.delete_if_orphaned(conn, list_id)

    conn.execute("DELETE FROM shopping_list_items WHERE added_by_profile_id = ?", (profile_id,))
    conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    conn.commit()
