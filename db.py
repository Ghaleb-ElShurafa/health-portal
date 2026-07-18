"""Storage: registered users, their lab entries, and site settings.

Uses a local SQLite file by default. If TURSO_DATABASE_URL and
TURSO_AUTH_TOKEN are set (e.g. for a hosted deployment where local disk
storage isn't reliably persistent), it transparently switches to a remote
Turso (libSQL) database instead — same SQL, same query patterns throughout
this file, via the small compatibility wrapper below.
"""

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from reference_ranges import DEFAULT_THRESHOLDS

load_dotenv()

DB_PATH = Path(__file__).parent / "data" / "personal_doctor.db"

TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")
USE_REMOTE_DB = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)

COLUMNS = [
    "total_cholesterol", "ldl", "hdl", "triglycerides",
    "glucose_fasting", "hba1c", "systolic", "diastolic",
]

ANNOUNCEMENT_KEY = "announcement"


class _RemoteCursor:
    """Makes a libsql_client ResultSet look like a sqlite3 cursor."""

    def __init__(self, result_set):
        self._rs = result_set
        self.lastrowid = result_set.last_insert_rowid

    def fetchone(self):
        return self._rs.rows[0].asdict() if self._rs.rows else None

    def fetchall(self):
        return [row.asdict() for row in self._rs.rows]


class _RemoteConn:
    """Makes a libsql_client ClientSync look like a sqlite3 connection."""

    def __init__(self, client):
        self._client = client

    def execute(self, sql, params=()):
        return _RemoteCursor(self._client.execute(sql, list(params)))

    def commit(self):
        pass  # each statement over the Hrana/HTTP protocol is auto-committed

    def close(self):
        self._client.close()


def _connect():
    if USE_REMOTE_DB:
        import libsql_client

        # Use HTTP (Hrana-over-HTTP) rather than the libsql:// WebSocket
        # scheme: each call here is a short, one-off request/response, and
        # the WebSocket handshake was unreliable in testing.
        http_url = TURSO_DATABASE_URL.replace("libsql://", "https://", 1)
        return _RemoteConn(libsql_client.create_client_sync(url=http_url, auth_token=TURSO_AUTH_TOKEN))

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
            is_admin INTEGER NOT NULL DEFAULT 0,
            first_name TEXT,
            last_name TEXT,
            age INTEGER,
            country TEXT,
            remember_token TEXT,
            remember_token_expires TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    migrations = {
        "is_admin": "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0",
        "first_name": "ALTER TABLE users ADD COLUMN first_name TEXT",
        "last_name": "ALTER TABLE users ADD COLUMN last_name TEXT",
        "age": "ALTER TABLE users ADD COLUMN age INTEGER",
        "country": "ALTER TABLE users ADD COLUMN country TEXT",
        "remember_token": "ALTER TABLE users ADD COLUMN remember_token TEXT",
        "remember_token_expires": "ALTER TABLE users ADD COLUMN remember_token_expires TEXT",
    }
    for column, statement in migrations.items():
        if column not in existing_columns:
            conn.execute(statement)

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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            description TEXT NOT NULL,
            chat_context TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def create_user(
    email,
    password_hash=None,
    auth_provider="password",
    google_sub=None,
    first_name=None,
    last_name=None,
    age=None,
    country=None,
):
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, auth_provider, google_sub, first_name, last_name, age, country) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (email, password_hash, auth_provider, google_sub, first_name, last_name, age, country),
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


def list_users():
    conn = _connect()
    rows = conn.execute(
        "SELECT id, email, auth_provider, is_admin, first_name, last_name, age, country, created_at "
        "FROM users ORDER BY created_at ASC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_admin(user_id, is_admin: bool):
    conn = _connect()
    conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if is_admin else 0, user_id))
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = _connect()
    conn.execute("DELETE FROM entries WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


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


def get_setting(key, default=None):
    conn = _connect()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = _connect()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


def get_thresholds():
    conn = _connect()
    rows = conn.execute("SELECT key, value FROM settings WHERE key LIKE 'threshold.%'").fetchall()
    conn.close()
    overrides = {row["key"][len("threshold."):]: float(row["value"]) for row in rows}
    return {**DEFAULT_THRESHOLDS, **overrides}


def set_threshold(key, value):
    set_setting(f"threshold.{key}", str(value))


def get_announcement():
    return get_setting(ANNOUNCEMENT_KEY, "")


def set_announcement(text):
    set_setting(ANNOUNCEMENT_KEY, text)


def create_issue(user_email, description, chat_context=""):
    conn = _connect()
    conn.execute(
        "INSERT INTO issues (user_email, description, chat_context) VALUES (?, ?, ?)",
        (user_email, description, chat_context),
    )
    conn.commit()
    conn.close()


def list_issues():
    conn = _connect()
    rows = conn.execute("SELECT * FROM issues ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_issue_status(issue_id, status):
    conn = _connect()
    conn.execute("UPDATE issues SET status = ? WHERE id = ?", (status, issue_id))
    conn.commit()
    conn.close()


def set_remember_token(user_id, token, expires_at_iso):
    conn = _connect()
    conn.execute(
        "UPDATE users SET remember_token = ?, remember_token_expires = ? WHERE id = ?",
        (token, expires_at_iso, user_id),
    )
    conn.commit()
    conn.close()


def get_user_by_remember_token(token):
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE remember_token = ?", (token,)).fetchone()
    conn.close()
    return dict(row) if row else None


def clear_remember_token(user_id):
    conn = _connect()
    conn.execute(
        "UPDATE users SET remember_token = NULL, remember_token_expires = NULL WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
