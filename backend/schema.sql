CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    image_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_products_barcode ON products (barcode);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    pin_hash TEXT NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    -- NULL for a profile's own personal list (auto-created, single-member
    -- by construction) - structurally not joinable, rather than a flag to
    -- check. Shared lists always have a code.
    join_code TEXT UNIQUE,
    created_by_profile_id INTEGER NOT NULL REFERENCES profiles (id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS list_memberships (
    list_id INTEGER NOT NULL REFERENCES lists (id),
    profile_id INTEGER NOT NULL REFERENCES profiles (id),
    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (list_id, profile_id)
);

CREATE INDEX IF NOT EXISTS idx_list_memberships_profile_id ON list_memberships (profile_id);

CREATE TABLE IF NOT EXISTS shopping_list_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products (id),
    quantity INTEGER NOT NULL DEFAULT 1,
    checked INTEGER NOT NULL DEFAULT 0,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    list_id INTEGER NOT NULL REFERENCES lists (id),
    added_by_profile_id INTEGER NOT NULL REFERENCES profiles (id)
);

CREATE INDEX IF NOT EXISTS idx_shopping_list_items_list_id ON shopping_list_items (list_id);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles (id),
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_profile_id ON sessions (profile_id);
