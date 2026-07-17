"""SQLite storage: registered users and their lab entries over time."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "personal_doctor.db"

COLUMNS = [
    "total_cholesterol", "ldl", "hdl", "triglycerides",
    "glucose_fasting", "hba1c", "systolic", "diastolic",
]


def _connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            auth_provider TEXT NOT NULL,
            google_sub TEXT UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    columns_sql = ", ".join(f"{c} REAL" for c in COLUMNS)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            entry_date TEXT NOT NULL,
            sex TEXT NOT NULL,
            {columns_sql}
        )
        """
    )
    conn.commit()
    conn.close()


def create_user(email, password_hash=None, auth_provider="password", google_sub=None):
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, auth_provider, google_sub) VALUES (?, ?, ?, ?)",
        (email, password_hash, auth_provider, google_sub),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_google_sub(google_sub):
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE google_sub = ?", (google_sub,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_entry(user_id, entry_date, sex, values: dict):
    conn = _connect()
    cols = ["user_id", "entry_date", "sex"] + list(values.keys())
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(
        f"INSERT INTO entries ({', '.join(cols)}) VALUES ({placeholders})",
        [user_id, entry_date, sex] + list(values.values()),
    )
    conn.commit()
    conn.close()


def get_entries_for_user(user_id):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM entries WHERE user_id = ? ORDER BY entry_date ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
