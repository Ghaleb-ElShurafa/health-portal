"""
Authentication: email/password accounts (bcrypt-hashed), guest mode, Google
sign-in, and "keep me logged in" persistent sessions.

Google OAuth is implemented manually with plain HTTP calls (via `requests`)
rather than a JWT/OIDC library, because this environment can't build the
`cryptography` package those libraries depend on (no Rust toolchain). Instead
of verifying the ID token's signature locally, we send it to Google's
`tokeninfo` endpoint and let Google verify it and hand back the decoded
claims. This is a documented, Google-supported pattern that's fine for an
app at this scale; it does mean each login makes an extra call to Google
rather than verifying the signature offline.

"Keep me logged in" stores a random bearer token (like a session ID, not a
password) in a browser cookie set client-side by app.py. It doesn't need
password-style hashing since it's high-entropy and never user-chosen.
"""

import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
import streamlit as st

import db

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"

REMEMBER_TOKEN_DAYS = 30
MIN_AGE = 13
MAX_AGE = 120


def _google_config():
    try:
        cfg = st.secrets["google_oauth"]
        return cfg["client_id"], cfg["client_secret"], cfg["redirect_uri"]
    except Exception:
        return None, None, None


def google_configured():
    client_id, client_secret, redirect_uri = _google_config()
    return bool(client_id and client_secret and redirect_uri)


def validate_password_strength(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"\d", password):
        return False, "Password must include at least one number."
    if not re.search(r"[A-Z]", password):
        return False, "Password must include at least one uppercase letter."
    return True, ""


def validate_profile(first_name, last_name, age, country):
    if not first_name.strip():
        return False, "First name is required."
    if not last_name.strip():
        return False, "Last name is required."
    if not country.strip():
        return False, "Country of residence is required."
    if age is None or age < MIN_AGE or age > MAX_AGE:
        return False, f"Age must be between {MIN_AGE} and {MAX_AGE}."
    return True, ""


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def validate_username(username, exclude_user_id=None):
    username = username.strip()
    if not USERNAME_PATTERN.match(username):
        return False, "Username must be 3-20 characters: letters, numbers, and underscores only."
    existing = db.get_user_by_username(username)
    if existing and existing["id"] != exclude_user_id:
        return False, "That username is already taken."
    return True, ""


def _generate_username(seed):
    base = re.sub(r"[^A-Za-z0-9_]", "", seed)[:15] or "user"
    candidate = base
    suffix = 0
    while db.get_user_by_username(candidate):
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


def _public_user(row):
    return {
        "id": row["id"],
        "email": row["email"],
        "auth_provider": row["auth_provider"],
        "is_admin": bool(row["is_admin"]),
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "age": row["age"],
        "country": row["country"],
        "dark_mode": bool(row["dark_mode"]) if row["dark_mode"] is not None else False,
        "language": row["language"] or "English",
        "community_public": bool(row["community_public"]) if row["community_public"] is not None else True,
        "username": row["username"],
    }


def sign_up(email, password, first_name, last_name, age, country, username):
    import bcrypt

    if db.get_user_by_email(email):
        return None, "An account with that email already exists."

    ok, message = validate_password_strength(password)
    if not ok:
        return None, message

    ok, message = validate_profile(first_name, last_name, age, country)
    if not ok:
        return None, message

    ok, message = validate_username(username)
    if not ok:
        return None, message

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = db.create_user(
        email,
        password_hash=password_hash,
        auth_provider="password",
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        age=age,
        country=country.strip(),
        username=username.strip(),
    )
    return _public_user(db.get_user_by_email(email)), ""


def log_in(email, password):
    import bcrypt

    user = db.get_user_by_email(email)
    if not user or user["auth_provider"] != "password":
        return None, "No account found with that email and password."

    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return None, "No account found with that email and password."

    return _public_user(user), ""


def build_google_auth_url():
    client_id, _, redirect_uri = _google_config()
    state = secrets.token_urlsafe(16)
    st.session_state["_oauth_state"] = state
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"


def complete_google_login(code, state):
    if state != st.session_state.get("_oauth_state"):
        return None, "Login request expired or invalid — please try again."

    client_id, client_secret, redirect_uri = _google_config()

    token_resp = requests.post(
        GOOGLE_TOKEN_ENDPOINT,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if not token_resp.ok:
        return None, "Google sign-in failed while exchanging the authorization code."

    id_token = token_resp.json().get("id_token")
    if not id_token:
        return None, "Google sign-in did not return an identity token."

    info_resp = requests.get(GOOGLE_TOKENINFO_ENDPOINT, params={"id_token": id_token}, timeout=10)
    if not info_resp.ok:
        return None, "Google could not verify the sign-in token."

    claims = info_resp.json()
    if claims.get("aud") != client_id:
        return None, "Token audience mismatch — rejecting sign-in."
    if claims.get("email_verified") not in ("true", True):
        return None, "Your Google email is not verified."

    google_sub = claims["sub"]
    email = claims["email"]

    user = db.get_user_by_google_sub(google_sub)
    if not user:
        existing = db.get_user_by_email(email)
        if existing:
            return None, "An account with this email already exists using password sign-in."
        username = _generate_username(claims.get("given_name") or email.split("@")[0])
        user_id = db.create_user(
            email,
            auth_provider="google",
            google_sub=google_sub,
            first_name=claims.get("given_name"),
            last_name=claims.get("family_name"),
            username=username,
        )
        user = db.get_user_by_email(email)

    return _public_user(user), ""


def create_remember_token(user_id):
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=REMEMBER_TOKEN_DAYS)).isoformat()
    db.set_remember_token(user_id, token, expires_at)
    return token


def get_user_by_remember_token(token):
    row = db.get_user_by_remember_token(token)
    if not row:
        return None
    expires_at = row["remember_token_expires"]
    if not expires_at or datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
        db.clear_remember_token(row["id"])
        return None
    return _public_user(row)


def clear_remember_token(user_id):
    db.clear_remember_token(user_id)


def change_password(user_id, current_password, new_password):
    import bcrypt

    user = db.get_user_by_id(user_id)
    if not user or user["auth_provider"] != "password":
        return False, "Password changes aren't available for this sign-in method."
    if not bcrypt.checkpw(current_password.encode(), user["password_hash"].encode()):
        return False, "Current password is incorrect."
    ok, message = validate_password_strength(new_password)
    if not ok:
        return False, message
    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    db.update_password_hash(user_id, new_hash)
    return True, ""


def change_email(user_id, current_password, new_email):
    import bcrypt

    user = db.get_user_by_id(user_id)
    if not user or user["auth_provider"] != "password":
        return False, "Email changes aren't available for this sign-in method."
    if not bcrypt.checkpw(current_password.encode(), user["password_hash"].encode()):
        return False, "Current password is incorrect."
    new_email = new_email.strip()
    if not new_email:
        return False, "Enter a new email address."
    existing = db.get_user_by_email(new_email)
    if existing and existing["id"] != user_id:
        return False, "An account with that email already exists."
    db.update_email(user_id, new_email)
    return True, ""


def change_display_name(user_id, first_name, last_name):
    first_name, last_name = first_name.strip(), last_name.strip()
    if not first_name or not last_name:
        return False, "First and last name are required."
    db.update_display_name(user_id, first_name, last_name)
    return True, ""


def change_username(user_id, new_username):
    ok, message = validate_username(new_username, exclude_user_id=user_id)
    if not ok:
        return False, message
    db.update_username(user_id, new_username.strip())
    return True, ""
