import random

JOIN_CODE_ATTEMPTS = 20


def _generate_join_code(conn):
    """3-digit numeric code per plan.md/#43 - small collision space (1000
    codes) is fine at household scale; retries on collision with an
    already-active shared list's code."""
    for _ in range(JOIN_CODE_ATTEMPTS):
        code = f"{random.randint(0, 999):03d}"
        exists = conn.execute("SELECT 1 FROM lists WHERE join_code = ?", (code,)).fetchone()
        if not exists:
            return code
    raise RuntimeError("could not generate a unique join code")


def _row_to_dict(row, is_member=None):
    result = {
        "id": row["id"],
        "name": row["name"],
        "join_code": row["join_code"],
        "is_personal": row["join_code"] is None,
        "created_by_profile_id": row["created_by_profile_id"],
        "created_at": row["created_at"],
    }
    if is_member is not None:
        result["is_member"] = is_member
    return result


def get_by_id(conn, list_id):
    row = conn.execute("SELECT * FROM lists WHERE id = ?", (list_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_by_join_code(conn, join_code):
    row = conn.execute("SELECT * FROM lists WHERE join_code = ?", (join_code,)).fetchone()
    return _row_to_dict(row) if row else None


def get_all_admin(conn):
    rows = conn.execute(
        """
        SELECT lists.*, profiles.name AS created_by_name,
               (SELECT COUNT(*) FROM list_memberships WHERE list_memberships.list_id = lists.id) AS member_count
        FROM lists
        JOIN profiles ON profiles.id = lists.created_by_profile_id
        ORDER BY lists.created_at
        """
    ).fetchall()
    return [
        {**_row_to_dict(row), "created_by_name": row["created_by_name"], "member_count": row["member_count"]}
        for row in rows
    ]


def get_for_profile(conn, profile_id):
    rows = conn.execute(
        """
        SELECT lists.* FROM lists
        JOIN list_memberships ON list_memberships.list_id = lists.id
        WHERE list_memberships.profile_id = ?
        ORDER BY lists.created_at
        """,
        (profile_id,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def is_member(conn, list_id, profile_id):
    row = conn.execute(
        "SELECT 1 FROM list_memberships WHERE list_id = ? AND profile_id = ?",
        (list_id, profile_id),
    ).fetchone()
    return row is not None


def _add_membership(conn, list_id, profile_id):
    conn.execute(
        "INSERT OR IGNORE INTO list_memberships (list_id, profile_id) VALUES (?, ?)",
        (list_id, profile_id),
    )


def create_personal(conn, profile_id, name):
    """A profile's own list, auto-created alongside the profile itself.
    join_code stays NULL - not joinable by anyone else."""
    cur = conn.execute(
        "INSERT INTO lists (name, join_code, created_by_profile_id) VALUES (?, NULL, ?)",
        (name, profile_id),
    )
    _add_membership(conn, cur.lastrowid, profile_id)
    conn.commit()
    return get_by_id(conn, cur.lastrowid)


def create_shared(conn, profile_id, name):
    join_code = _generate_join_code(conn)
    cur = conn.execute(
        "INSERT INTO lists (name, join_code, created_by_profile_id) VALUES (?, ?, ?)",
        (name, join_code, profile_id),
    )
    _add_membership(conn, cur.lastrowid, profile_id)
    conn.commit()
    return get_by_id(conn, cur.lastrowid)


def join(conn, profile_id, join_code):
    """Returns the joined list, or None if no shared list has that code."""
    list_row = get_by_join_code(conn, join_code)
    if list_row is None:
        return None
    _add_membership(conn, list_row["id"], profile_id)
    conn.commit()
    return list_row


def leave(conn, list_id, profile_id):
    conn.execute(
        "DELETE FROM list_memberships WHERE list_id = ? AND profile_id = ?",
        (list_id, profile_id),
    )
    conn.commit()


def delete_if_orphaned(conn, list_id):
    """Deletes a list (and its items) if it has no members left - called
    after removing a membership, so a shared list a departing member
    happened to be the last one in doesn't linger forever."""
    remaining = conn.execute(
        "SELECT 1 FROM list_memberships WHERE list_id = ?", (list_id,)
    ).fetchone()
    if remaining is None:
        conn.execute("DELETE FROM shopping_list_items WHERE list_id = ?", (list_id,))
        conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))
        conn.commit()


def delete(conn, list_id):
    """Force-deletes a list outright, regardless of remaining members -
    distinct from leave()/delete_if_orphaned(), which only clean up a list
    once nobody's left in it. Callers must check the requester is the
    list's creator first."""
    conn.execute("DELETE FROM shopping_list_items WHERE list_id = ?", (list_id,))
    conn.execute("DELETE FROM list_memberships WHERE list_id = ?", (list_id,))
    conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))
    conn.commit()
