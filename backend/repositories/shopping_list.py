def get_all(conn):
    rows = conn.execute(
        """
        SELECT shopping_list_items.*, products.name, products.category
        FROM shopping_list_items
        JOIN products ON products.id = shopping_list_items.product_id
        ORDER BY shopping_list_items.added_at
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_by_id(conn, item_id):
    row = conn.execute("SELECT * FROM shopping_list_items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def product_exists(conn, product_id):
    row = conn.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone()
    return row is not None


def get_unchecked_by_product(conn, product_id):
    row = conn.execute(
        "SELECT * FROM shopping_list_items WHERE product_id = ? AND checked = 0",
        (product_id,),
    ).fetchone()
    return dict(row) if row else None


def create(conn, product_id, quantity):
    """Merges into an existing unchecked entry for the same product (bumps
    its quantity) instead of creating a duplicate row. A re-scan of a
    product that's already checked off starts a fresh entry instead, since
    that means "need to buy again", not "add more to this trip"."""
    existing = get_unchecked_by_product(conn, product_id)
    if existing is not None:
        return update(conn, existing["id"], quantity=existing["quantity"] + quantity)

    cur = conn.execute(
        "INSERT INTO shopping_list_items (product_id, quantity) VALUES (?, ?)",
        (product_id, quantity),
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
