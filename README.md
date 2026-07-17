# Personal Doctor

A Streamlit app that lets a user log bloodwork results over time, flags
out-of-range values against standard clinical reference ranges, and uses the
Claude API to generate a plain-language summary and general diet/lifestyle
suggestions — always flagging when a result should be discussed with a doctor.

**⚠️ Not medical advice.** This is an educational/portfolio project. It does
not diagnose or treat any condition, and "consult a doctor" flags are always
computed with local rule-based logic (`reference_ranges.py`), independent of
the AI — the model is only responsible for the explanatory text, never for
deciding what's urgent.

## Features

- Email/password accounts (bcrypt-hashed), Google sign-in, or a guest mode
  that needs no account
- Manual entry of a lipid panel, glucose/HbA1c, and blood pressure
- Rule-based flagging against standard adult reference ranges (NCEP ATP III
  cholesterol guidelines, ADA glucose/A1c thresholds, AHA blood pressure
  categories)
- AI-generated plain-language summary and lifestyle suggestions (Claude API)
- Trend charts across entries, scoped per account, stored locally in SQLite

## Setup

```
pip install -r requirements.txt
cp .env.example .env        # then edit .env and add your own Anthropic API key
streamlit run app.py
```

Without an API key configured, the app still works — it shows the rule-based
results and flags, just without the AI-generated summary.

### Accounts

- **Email/password**: sign up directly in the app. Passwords need 8+
  characters, one number, and one uppercase letter.
- **Guest**: try the app with no account — data is kept only in that browser
  session and is gone once the tab is closed.
- **Google sign-in** (optional): requires your own Google OAuth credentials.
  1. In [Google Cloud Console](https://console.cloud.google.com/), create an
     OAuth 2.0 Client ID (type: Web application).
  2. Add `http://localhost:8501` as an authorized redirect URI.
  3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and
     fill in your own `client_id` and `client_secret`.

  Note on how Google sign-in is verified: rather than a JWT/OIDC library
  (which needs the `cryptography` package — not buildable in this dev
  environment without a Rust toolchain), the ID token is verified by calling
  Google's own `tokeninfo` endpoint. That's a Google-documented approach and
  fine at this app's scale, though a high-traffic production app should
  verify signatures locally instead.

## Project structure

```
app.py                  Streamlit UI (auth gate + main app)
auth.py                  password hashing/validation, Google OAuth flow
reference_ranges.py      reference ranges + flagging rules
ai_advice.py             Claude API prompt + call
db.py                    local SQLite storage: users + entry history
```

## Scope note

This is a working prototype demonstrating the full pipeline (data entry →
rule-based analysis → AI explanation → trend visualization) using data you
enter yourself. It intentionally does **not** implement file uploads, user
accounts, or storage of real patient records — turning this into something
a healthcare company could deploy with real patient data would require
HIPAA/PIPEDA-compliant infrastructure (encryption at rest, access controls,
audit logging, BAAs with any third-party APIs used) that's out of scope here.
