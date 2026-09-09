import sqlite3
from pathlib import Path

from flask import g

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path):
    conn = _connect(db_path)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def get_db(db_path):
    if "db" not in g:
        g.db = _connect(db_path)
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
