import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "machines.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and insert the default fields on first run."""
    conn = get_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            required INTEGER NOT NULL DEFAULT 0,
            options TEXT NOT NULL DEFAULT '[]'
        )"""
    )
    # values are stored as JSON: {"<field_id>": value}
    conn.execute(
        """CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL DEFAULT '{}'
        )"""
    )

    defaults = [
        ("Machine Name", "text", 1, "[]"),
        ("Temperature", "number", 1, "[]"),
        ("Pressure", "number", 1, "[]"),
        ("Vibration", "dropdown", 1, '["Low", "Medium", "High"]'),
    ]
    existing = {row[0] for row in conn.execute("SELECT name FROM fields").fetchall()}
    missing = [field for field in defaults if field[0] not in existing]
    if missing:
        conn.executemany(
            "INSERT INTO fields (name, type, required, options) VALUES (?, ?, ?, ?)",
            missing,
        )
    conn.commit()
    conn.close()
