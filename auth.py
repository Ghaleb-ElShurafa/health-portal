"""
Authentication: email/password accounts (bcrypt-hashed), guest mode, and
Google sign-in.

Google OAuth is implemented manually with plain HTTP calls (via `requests`)
rather than a JWT/OIDC library, because this environment can't build the
`cryptography` package those libraries depend on (no Rust toolchain). Instead
of verifying the ID token's signature locally, we send it to Google's
`tokeninfo` endpoint and let Google verify it and hand back the decoded
claims. This is a documented, Google-supported pattern that's fine for an
app at this scale; it does mean each login makes an extra call to Google
rather than verifying the signature offline.
"""

import re
import secrets
from urllib.parse import urlencode

import requests
import streamlit as st

import db

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"


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


def sign_up(email, password):
    import bcrypt

    if db.get_user_by_email(email):
        return None, "An account with that email already exists."

    ok, message = validate_password_strength(password)
    if not ok:
        return None, message

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = db.create_user(email, password_hash=password_hash, auth_provider="password")
    return {"id": user_id, "email": email, "auth_provider": "password"}, ""


def log_in(email, password):
    import bcrypt

    user = db.get_user_by_email(email)
    if not user or user["auth_provider"] != "password":
        return None, "No account found with that email and password."

    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return None, "No account found with that email and password."

    return {"id": user["id"], "email": user["email"], "auth_provider": "password"}, ""


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
        user_id = db.create_user(email, auth_provider="google", google_sub=google_sub)
    else:
        user_id = user["id"]

    return {"id": user_id, "email": email, "auth_provider": "google"}, ""
