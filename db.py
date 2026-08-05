"""Storage: registered users, their lab entries, and site settings.

Uses a local SQLite file by default. If TURSO_DATABASE_URL and
TURSO_AUTH_TOKEN are set (e.g. for a hosted deployment where local disk
storage isn't reliably persistent), it transparently switches to a remote
Turso (libSQL) database instead — same SQL, same query patterns throughout
this file, via the small compatibility wrapper below.
"""

import json
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from reference_ranges import DEFAULT_THRESHOLDS

load_dotenv()


def _config(key):
    """Reads from the environment first (local .env), falling back to
    st.secrets (Streamlit Community Cloud puts secrets there, not
    necessarily into os.environ)."""
    value = os.environ.get(key)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(key)
    except Exception:
        return None


DB_PATH = Path(__file__).parent / "data" / "personal_doctor.db"

TURSO_DATABASE_URL = _config("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = _config("TURSO_AUTH_TOKEN")
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
            diagnosis TEXT,
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
        "diagnosis": "ALTER TABLE users ADD COLUMN diagnosis TEXT",
        "goal": "ALTER TABLE users ADD COLUMN goal TEXT",
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS uc_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            entry_date TEXT NOT NULL,
            flared INTEGER NOT NULL DEFAULT 0,
            severity TEXT,
            foods TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS login_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            display_name TEXT,
            auth_provider TEXT NOT NULL,
            login_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS patient_profiles (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            conditions TEXT NOT NULL DEFAULT '[]',
            other_condition TEXT,
            medications TEXT,
            supplements TEXT,
            goals TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            entry_date TEXT NOT NULL,
            food_items TEXT NOT NULL,
            calories REAL,
            protein_g REAL,
            carbs_g REAL,
            fat_g REAL,
            health_score REAL,
            assessment TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tracked_conditions (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            conditions TEXT NOT NULL DEFAULT '[]',
            other_condition TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS condition_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            condition TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            symptom_occurred INTEGER NOT NULL DEFAULT 0,
            severity TEXT,
            triggers TEXT,
            notes TEXT,
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


def log_activity(email, display_name, auth_provider):
    conn = _connect()
    conn.execute(
        "INSERT INTO login_activity (email, display_name, auth_provider) VALUES (?, ?, ?)",
        (email, display_name, auth_provider),
    )
    conn.commit()
    conn.close()


def list_activity(limit=500):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM login_activity ORDER BY login_at DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_meal_entry(user_id, entry_date, food_items, calories, protein_g, carbs_g, fat_g, health_score, assessment):
    conn = _connect()
    conn.execute(
        "INSERT INTO meal_entries (user_id, entry_date, food_items, calories, protein_g, carbs_g, fat_g, health_score, assessment) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, entry_date, food_items, calories, protein_g, carbs_g, fat_g, health_score, assessment),
    )
    conn.commit()
    conn.close()


def get_meal_entries_for_user(user_id):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM meal_entries WHERE user_id = ? ORDER BY entry_date ASC, id ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


EMPTY_PATIENT_PROFILE = {"conditions": [], "other_condition": "", "medications": "", "supplements": "", "goals": []}


def get_patient_profile(user_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM patient_profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return dict(EMPTY_PATIENT_PROFILE)
    row = dict(row)
    return {
        "conditions": json.loads(row["conditions"]),
        "other_condition": row["other_condition"] or "",
        "medications": row["medications"] or "",
        "supplements": row["supplements"] or "",
        "goals": json.loads(row["goals"]),
    }


def set_patient_profile(user_id, conditions, other_condition, medications, supplements, goals):
    conn = _connect()
    conn.execute(
        "INSERT INTO patient_profiles (user_id, conditions, other_condition, medications, supplements, goals, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(user_id) DO UPDATE SET conditions = excluded.conditions, other_condition = excluded.other_condition, "
        "medications = excluded.medications, supplements = excluded.supplements, goals = excluded.goals, "
        "updated_at = CURRENT_TIMESTAMP",
        (user_id, json.dumps(conditions), other_condition, medications, supplements, json.dumps(goals)),
    )
    conn.commit()
    conn.close()


EMPTY_TRACKED_CONDITIONS = {"conditions": [], "other_condition": ""}


def get_tracked_conditions(user_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM tracked_conditions WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return dict(EMPTY_TRACKED_CONDITIONS)
    row = dict(row)
    return {"conditions": json.loads(row["conditions"]), "other_condition": row["other_condition"] or ""}


def set_tracked_conditions(user_id, conditions, other_condition):
    conn = _connect()
    conn.execute(
        "INSERT INTO tracked_conditions (user_id, conditions, other_condition, updated_at) "
        "VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(user_id) DO UPDATE SET conditions = excluded.conditions, "
        "other_condition = excluded.other_condition, updated_at = CURRENT_TIMESTAMP",
        (user_id, json.dumps(conditions), other_condition),
    )
    conn.commit()
    conn.close()


def add_condition_entry(user_id, condition, entry_date, symptom_occurred, severity, triggers, notes):
    conn = _connect()
    conn.execute(
        "INSERT INTO condition_entries (user_id, condition, entry_date, symptom_occurred, severity, triggers, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, condition, entry_date, 1 if symptom_occurred else 0, severity, triggers, notes),
    )
    conn.commit()
    conn.close()


def update_condition_entry(entry_id, symptom_occurred, severity, triggers, notes):
    conn = _connect()
    conn.execute(
        "UPDATE condition_entries SET symptom_occurred = ?, severity = ?, triggers = ?, notes = ? WHERE id = ?",
        (1 if symptom_occurred else 0, severity, triggers, notes, entry_id),
    )
    conn.commit()
    conn.close()


def get_condition_entries(user_id, condition):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM condition_entries WHERE user_id = ? AND condition = ? ORDER BY entry_date ASC, id ASC",
        (user_id, condition),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
