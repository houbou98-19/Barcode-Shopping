def get_all(conn, list_id):
    rows = conn.execute(
        """
        SELECT shopping_list_items.*, products.name, products.category, products.barcode,
               profiles.name AS added_by_name
        FROM shopping_list_items
        JOIN products ON products.id = shopping_list_items.product_id
        JOIN profiles ON profiles.id = shopping_list_items.added_by_profile_id
        WHERE shopping_list_items.list_id = ?
        ORDER BY shopping_list_items.added_at
        """,
        (list_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_by_id(conn, item_id):
    row = conn.execute("SELECT * FROM shopping_list_items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def product_exists(conn, product_id):
    row = conn.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone()
    return row is not None


def get_unchecked_by_product(conn, product_id, list_id):
    row = conn.execute(
        "SELECT * FROM shopping_list_items WHERE product_id = ? AND list_id = ? AND checked = 0",
        (product_id, list_id),
    ).fetchone()
    return dict(row) if row else None


def create(conn, product_id, quantity, list_id, added_by_profile_id):
    """Merges into an existing unchecked entry for the same product on the
    same list (bumps its quantity) instead of creating a duplicate row,
    regardless of which member added either one - it's one shared list. A
    re-scan of a product that's already checked off starts a fresh entry
    instead, since that means "need to buy again", not "add more to this
    trip"."""
    existing = get_unchecked_by_product(conn, product_id, list_id)
    if existing is not None:
        return update(conn, existing["id"], quantity=existing["quantity"] + quantity)

    cur = conn.execute(
        "INSERT INTO shopping_list_items (product_id, quantity, list_id, added_by_profile_id) "
        "VALUES (?, ?, ?, ?)",
        (product_id, quantity, list_id, added_by_profile_id),
    )
    conn.commit()
    return get_by_id(conn, cur.lastrowid)


def update(conn, item_id, quantity=None, checked=None):
    fields = []
    values = []
    if quantity is not None:
        fields.append("quantity = ?")
        values.append(quantity)
    if checked is not None:
        fields.append("checked = ?")
        values.append(1 if checked else 0)
    if not fields:
        return get_by_id(conn, item_id)

    values.append(item_id)
    conn.execute(f"UPDATE shopping_list_items SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    return get_by_id(conn, item_id)


def delete(conn, item_id):
    conn.execute("DELETE FROM shopping_list_items WHERE id = ?", (item_id,))
    conn.commit()


def get_checked(conn, list_id):
    rows = conn.execute(
        """
        SELECT shopping_list_items.*, products.name
        FROM shopping_list_items
        JOIN products ON products.id = shopping_list_items.product_id
        WHERE shopping_list_items.list_id = ? AND shopping_list_items.checked = 1
        ORDER BY shopping_list_items.added_at
        """,
        (list_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def delete_checked(conn, list_id):
    """Returns the deleted rows (name + quantity) so the caller can show a
    receipt of what was cleared - the whole point of this over deleting
    items one at a time."""
    cleared = get_checked(conn, list_id)
    conn.execute(
        "DELETE FROM shopping_list_items WHERE list_id = ? AND checked = 1", (list_id,)
    )
    conn.commit()
    return cleared


def move_items(conn, item_ids, target_list_id):
    """Same merge rule as create(): an unchecked item moving into a list
    that already has an unchecked entry for the same product merges into
    it (bumping quantity) instead of creating a duplicate row. A checked
    item moves over as-is - it represents a separate, already-completed
    entry, not more of what's still needed."""
    for item_id in item_ids:
        item = get_by_id(conn, item_id)
        if item is None or item["list_id"] == target_list_id:
            continue

        if not item["checked"]:
            existing = get_unchecked_by_product(conn, item["product_id"], target_list_id)
            if existing is not None:
                update(conn, existing["id"], quantity=existing["quantity"] + item["quantity"])
                delete(conn, item_id)
                continue

        conn.execute(
            "UPDATE shopping_list_items SET list_id = ? WHERE id = ?", (target_list_id, item_id)
        )
    conn.commit()
