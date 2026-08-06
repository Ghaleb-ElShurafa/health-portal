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
        "dark_mode": "ALTER TABLE users ADD COLUMN dark_mode INTEGER NOT NULL DEFAULT 0",
        "language": "ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'English'",
        "community_public": "ALTER TABLE users ADD COLUMN community_public INTEGER NOT NULL DEFAULT 1",
        "username": "ALTER TABLE users ADD COLUMN username TEXT",
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
            height_cm REAL,
            weight_kg REAL,
            sex TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    existing_profile_columns = {row["name"] for row in conn.execute("PRAGMA table_info(patient_profiles)").fetchall()}
    profile_migrations = {
        "height_cm": "ALTER TABLE patient_profiles ADD COLUMN height_cm REAL",
        "weight_kg": "ALTER TABLE patient_profiles ADD COLUMN weight_kg REAL",
        "sex": "ALTER TABLE patient_profiles ADD COLUMN sex TEXT",
    }
    for column, statement in profile_migrations.items():
        if column not in existing_profile_columns:
            conn.execute(statement)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS body_metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            recorded_at TEXT NOT NULL,
            height_cm REAL,
            weight_kg REAL,
            bmi REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fitness_settings (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            facility TEXT NOT NULL DEFAULT 'Both',
            days_per_week INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            log_date TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            muscle_group TEXT NOT NULL,
            duration_min REAL,
            intensity TEXT,
            calories_burned REAL,
            completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            email TEXT NOT NULL,
            display_name TEXT,
            feedback TEXT NOT NULL,
            admin_reply TEXT,
            replied_at TEXT,
            user_seen_reply INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS welcome_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            content TEXT NOT NULL,
            seen INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS community_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            display_name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_id INTEGER NOT NULL REFERENCES users(id),
            addressee_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS direct_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER NOT NULL REFERENCES users(id),
            to_user_id INTEGER NOT NULL REFERENCES users(id),
            content TEXT NOT NULL,
            read_at TEXT,
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
    username=None,
):
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, auth_provider, google_sub, first_name, last_name, age, country, username) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (email, password_hash, auth_provider, google_sub, first_name, last_name, age, country, username),
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


def get_user_by_username(username):
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_username(user_id, username):
    conn = _connect()
    conn.execute("UPDATE users SET username = ? WHERE id = ?", (username, user_id))
    conn.commit()
    conn.close()


def get_user_by_google_sub(google_sub):
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE google_sub = ?", (google_sub,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_password_hash(user_id, password_hash):
    conn = _connect()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    conn.commit()
    conn.close()


def update_email(user_id, new_email):
    conn = _connect()
    conn.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id))
    conn.commit()
    conn.close()


def update_display_name(user_id, first_name, last_name):
    conn = _connect()
    conn.execute(
        "UPDATE users SET first_name = ?, last_name = ? WHERE id = ?", (first_name, last_name, user_id),
    )
    conn.commit()
    conn.close()


def update_user_preferences(user_id, dark_mode, language):
    conn = _connect()
    conn.execute(
        "UPDATE users SET dark_mode = ?, language = ? WHERE id = ?",
        (1 if dark_mode else 0, language, user_id),
    )
    conn.commit()
    conn.close()


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


EMPTY_PATIENT_PROFILE = {
    "conditions": [], "other_condition": "", "medications": "", "supplements": "", "goals": [],
    "height_cm": None, "weight_kg": None, "sex": "",
}


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
        "height_cm": row.get("height_cm"),
        "weight_kg": row.get("weight_kg"),
        "sex": row.get("sex") or "",
    }


def set_patient_profile(
    user_id, conditions, other_condition, medications, supplements, goals,
    height_cm=None, weight_kg=None, sex="",
):
    conn = _connect()
    conn.execute(
        "INSERT INTO patient_profiles (user_id, conditions, other_condition, medications, supplements, goals, "
        "height_cm, weight_kg, sex, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(user_id) DO UPDATE SET conditions = excluded.conditions, other_condition = excluded.other_condition, "
        "medications = excluded.medications, supplements = excluded.supplements, goals = excluded.goals, "
        "height_cm = excluded.height_cm, weight_kg = excluded.weight_kg, sex = excluded.sex, "
        "updated_at = CURRENT_TIMESTAMP",
        (user_id, json.dumps(conditions), other_condition, medications, supplements, json.dumps(goals),
         height_cm, weight_kg, sex),
    )
    conn.commit()
    conn.close()


def add_body_metrics_entry(user_id, recorded_at, height_cm, weight_kg, bmi):
    conn = _connect()
    conn.execute(
        "INSERT INTO body_metrics_history (user_id, recorded_at, height_cm, weight_kg, bmi) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, recorded_at, height_cm, weight_kg, bmi),
    )
    conn.commit()
    conn.close()


def get_body_metrics_history(user_id):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM body_metrics_history WHERE user_id = ? ORDER BY recorded_at ASC, id ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


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


EMPTY_FITNESS_SETTINGS = {"facility": "Both", "days_per_week": None}


def get_fitness_settings(user_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM fitness_settings WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return dict(EMPTY_FITNESS_SETTINGS)
    row = dict(row)
    return {"facility": row["facility"], "days_per_week": row["days_per_week"]}


def set_fitness_settings(user_id, facility, days_per_week):
    conn = _connect()
    conn.execute(
        "INSERT INTO fitness_settings (user_id, facility, days_per_week, updated_at) "
        "VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(user_id) DO UPDATE SET facility = excluded.facility, "
        "days_per_week = excluded.days_per_week, updated_at = CURRENT_TIMESTAMP",
        (user_id, facility, days_per_week),
    )
    conn.commit()
    conn.close()


def add_workout_log_entry(user_id, log_date, exercise_name, muscle_group, duration_min, intensity, calories_burned, completed):
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO workout_log (user_id, log_date, exercise_name, muscle_group, duration_min, intensity, "
        "calories_burned, completed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, log_date, exercise_name, muscle_group, duration_min, intensity, calories_burned, 1 if completed else 0),
    )
    conn.commit()
    entry_id = cur.lastrowid
    conn.close()
    return entry_id


def update_workout_log_entry(entry_id, duration_min, intensity, calories_burned, completed):
    conn = _connect()
    conn.execute(
        "UPDATE workout_log SET duration_min = ?, intensity = ?, calories_burned = ?, completed = ? WHERE id = ?",
        (duration_min, intensity, calories_burned, 1 if completed else 0, entry_id),
    )
    conn.commit()
    conn.close()


def delete_workout_log_entry(entry_id):
    conn = _connect()
    conn.execute("DELETE FROM workout_log WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def get_workout_log(user_id):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM workout_log WHERE user_id = ? ORDER BY log_date ASC, id ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_review(user_id, email, display_name, feedback):
    conn = _connect()
    conn.execute(
        "INSERT INTO reviews (user_id, email, display_name, feedback) VALUES (?, ?, ?, ?)",
        (user_id, email, display_name, feedback),
    )
    conn.commit()
    conn.close()


def list_reviews():
    conn = _connect()
    rows = conn.execute("SELECT * FROM reviews ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_reviews_for_user(user_id):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM reviews WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def reply_to_review(review_id, reply_text):
    conn = _connect()
    conn.execute(
        "UPDATE reviews SET admin_reply = ?, replied_at = CURRENT_TIMESTAMP, user_seen_reply = 0 WHERE id = ?",
        (reply_text, review_id),
    )
    conn.commit()
    conn.close()


def mark_review_seen(review_id):
    conn = _connect()
    conn.execute("UPDATE reviews SET user_seen_reply = 1 WHERE id = ?", (review_id,))
    conn.commit()
    conn.close()


def count_unseen_replies(user_id):
    conn = _connect()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM reviews WHERE user_id = ? AND admin_reply IS NOT NULL AND user_seen_reply = 0",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row)["c"] if row else 0


def update_community_privacy(user_id, public: bool):
    conn = _connect()
    conn.execute("UPDATE users SET community_public = ? WHERE id = ?", (1 if public else 0, user_id))
    conn.commit()
    conn.close()


def create_post(user_id, display_name, content):
    conn = _connect()
    conn.execute(
        "INSERT INTO community_posts (user_id, display_name, content) VALUES (?, ?, ?)",
        (user_id, display_name, content),
    )
    conn.commit()
    conn.close()


def list_public_posts(limit=100):
    conn = _connect()
    rows = conn.execute(
        """
        SELECT community_posts.* FROM community_posts
        JOIN users ON users.id = community_posts.user_id
        WHERE users.community_public = 1
        ORDER BY community_posts.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_post(post_id, user_id):
    conn = _connect()
    conn.execute("DELETE FROM community_posts WHERE id = ? AND user_id = ?", (post_id, user_id))
    conn.commit()
    conn.close()


def search_users(query, exclude_user_id):
    conn = _connect()
    like = f"%{query}%"
    rows = conn.execute(
        """
        SELECT id, email, first_name, last_name, username FROM users
        WHERE id != ? AND auth_provider != 'guest'
        AND (email LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR username LIKE ?)
        LIMIT 10
        """,
        (exclude_user_id, like, like, like, like),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_friendship(user_a, user_b):
    conn = _connect()
    row = conn.execute(
        """
        SELECT * FROM friendships
        WHERE (requester_id = ? AND addressee_id = ?) OR (requester_id = ? AND addressee_id = ?)
        """,
        (user_a, user_b, user_b, user_a),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def send_friend_request(requester_id, addressee_id):
    conn = _connect()
    conn.execute(
        "INSERT INTO friendships (requester_id, addressee_id, status) VALUES (?, ?, 'pending')",
        (requester_id, addressee_id),
    )
    conn.commit()
    conn.close()


def respond_friend_request(request_id, accept):
    conn = _connect()
    if accept:
        conn.execute("UPDATE friendships SET status = 'accepted' WHERE id = ?", (request_id,))
    else:
        conn.execute("DELETE FROM friendships WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()


def remove_friend(user_a, user_b):
    conn = _connect()
    conn.execute(
        """
        DELETE FROM friendships
        WHERE (requester_id = ? AND addressee_id = ?) OR (requester_id = ? AND addressee_id = ?)
        """,
        (user_a, user_b, user_b, user_a),
    )
    conn.commit()
    conn.close()


def list_pending_requests(user_id):
    """Incoming requests awaiting this user's response."""
    conn = _connect()
    rows = conn.execute(
        """
        SELECT friendships.id AS request_id, users.id AS user_id, users.email,
               users.first_name, users.last_name, users.username
        FROM friendships JOIN users ON users.id = friendships.requester_id
        WHERE friendships.addressee_id = ? AND friendships.status = 'pending'
        ORDER BY friendships.created_at DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_sent_request_ids(user_id):
    """IDs of users this user has already sent a still-pending request to."""
    conn = _connect()
    rows = conn.execute(
        "SELECT addressee_id FROM friendships WHERE requester_id = ? AND status = 'pending'",
        (user_id,),
    ).fetchall()
    conn.close()
    return {row["addressee_id"] for row in rows}


def list_friends(user_id):
    conn = _connect()
    rows = conn.execute(
        """
        SELECT users.id AS user_id, users.email, users.first_name, users.last_name, users.username
        FROM friendships JOIN users ON users.id = friendships.addressee_id
        WHERE friendships.status = 'accepted' AND friendships.requester_id = ?
        UNION
        SELECT users.id AS user_id, users.email, users.first_name, users.last_name, users.username
        FROM friendships JOIN users ON users.id = friendships.requester_id
        WHERE friendships.status = 'accepted' AND friendships.addressee_id = ?
        ORDER BY first_name
        """,
        (user_id, user_id),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def send_message(from_id, to_id, content):
    conn = _connect()
    conn.execute(
        "INSERT INTO direct_messages (from_user_id, to_user_id, content) VALUES (?, ?, ?)",
        (from_id, to_id, content),
    )
    conn.commit()
    conn.close()


def list_conversation(user_id, other_id):
    conn = _connect()
    rows = conn.execute(
        """
        SELECT * FROM direct_messages
        WHERE (from_user_id = ? AND to_user_id = ?) OR (from_user_id = ? AND to_user_id = ?)
        ORDER BY created_at ASC
        """,
        (user_id, other_id, other_id, user_id),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_messages_read(user_id, from_id):
    conn = _connect()
    conn.execute(
        "UPDATE direct_messages SET read_at = CURRENT_TIMESTAMP "
        "WHERE to_user_id = ? AND from_user_id = ? AND read_at IS NULL",
        (user_id, from_id),
    )
    conn.commit()
    conn.close()


def count_unread_from(user_id, from_id):
    conn = _connect()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM direct_messages WHERE to_user_id = ? AND from_user_id = ? AND read_at IS NULL",
        (user_id, from_id),
    ).fetchone()
    conn.close()
    return dict(row)["c"] if row else 0


def count_unread_messages(user_id):
    conn = _connect()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM direct_messages WHERE to_user_id = ? AND read_at IS NULL",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row)["c"] if row else 0


def create_welcome_message(user_id, content):
    """Idempotent -- safe to call on every login, only inserts once per user."""
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO welcome_messages (user_id, content) VALUES (?, ?)",
        (user_id, content),
    )
    conn.commit()
    conn.close()


def get_welcome_message(user_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM welcome_messages WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_welcome_seen(user_id):
    conn = _connect()
    conn.execute("UPDATE welcome_messages SET seen = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
