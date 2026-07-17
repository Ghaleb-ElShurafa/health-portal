"""SQLite storage for a single demo user's lab entries over time."""

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
    columns_sql = ", ".join(f"{c} REAL" for c in COLUMNS)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            sex TEXT NOT NULL,
            {columns_sql}
        )
        """
    )
    conn.commit()
    conn.close()


def add_entry(entry_date, sex, values: dict):
    conn = _connect()
    cols = ["entry_date", "sex"] + list(values.keys())
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(
        f"INSERT INTO entries ({', '.join(cols)}) VALUES ({placeholders})",
        [entry_date, sex] + list(values.values()),
    )
    conn.commit()
    conn.close()


def get_all_entries():
    conn = _connect()
    rows = conn.execute("SELECT * FROM entries ORDER BY entry_date ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]
