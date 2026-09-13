def get_all(conn):
    rows = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    return [dict(row) for row in rows]


def get_by_id(conn, product_id):
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return dict(row) if row else None


def get_by_barcode(conn, barcode):
    """A barcode is not guaranteed globally unique (e.g. GS1 restricted
    circulation numbers reused by different stores/manufacturers), so this
    can return more than one product."""
    rows = conn.execute(
        "SELECT * FROM products WHERE barcode = ? ORDER BY id", (barcode,)
    ).fetchall()
    return [dict(row) for row in rows]


def create(conn, barcode, name, category):
    cur = conn.execute(
        "INSERT INTO products (barcode, name, category) VALUES (?, ?, ?)",
        (barcode, name, category),
    )
    conn.commit()
    return get_by_id(conn, cur.lastrowid)


def update(conn, product_id, barcode=None, name=None, category=None):
    fields = []
    values = []
    if barcode is not None:
        fields.append("barcode = ?")
        values.append(barcode)
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if category is not None:
        fields.append("category = ?")
        values.append(category)
    if not fields:
        return get_by_id(conn, product_id)

    values.append(product_id)
    conn.execute(f"UPDATE products SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    return get_by_id(conn, product_id)


def delete(conn, product_id):
    """Cascades manually (no ON DELETE CASCADE in schema.sql): removes any
    shopping_list_items referencing this product first - moderating a bad
    product entry should also clean up its (now meaningless) references on
    everyone's lists, not leave them orphaned or block the deletion."""
    conn.execute("DELETE FROM shopping_list_items WHERE product_id = ?", (product_id,))
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
