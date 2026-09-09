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
