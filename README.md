# Health Services Portal

A multi-service health app built with Streamlit. Users sign up, land on a
services hub, and open individual tools — currently **Personal Doctor**
(bloodwork tracking + AI insights) and **Wellness Coach** (diet/exercise
plans personalized from that bloodwork). More services can be added as new
cards on the landing page.

**⚠️ Not medical advice.** This is an educational/portfolio project. It does
not diagnose or treat any condition. "Consult a doctor" flags are always
computed with local rule-based logic (`reference_ranges.py`), independent of
the AI — the model only writes explanatory text, never decides what's urgent.

## Features

- **Accounts**: email/password (with name, age, country of residence),
  Google sign-in, or a guest mode that needs no account. "Keep me logged in"
  persists a session via a browser cookie for 30 days.
- **Personal Doctor**: log a lipid panel, glucose/HbA1c, and blood pressure;
  get rule-based flags against standard adult reference ranges (NCEP ATP III
  cholesterol guidelines, ADA glucose/A1c thresholds, AHA blood pressure
  categories), an AI-generated plain-language summary, and trend charts.
- **Wellness Coach**: a diet + exercise plan from the Claude API, informed by
  your latest Personal Doctor bloodwork when available (falls back to a
  short questionnaire otherwise). Recommends medical clearance before
  exercise whenever bloodwork has a "consult a doctor" flag.
- **AI search bar**: ask anything on the landing page (Claude API).
- **Help & Support sidebar**: an AI chat for navigation/technical questions,
  plus a "report a technical issue" form that logs to the admin dashboard.
- **Admin dashboard** (for admin accounts): manage users (grant/revoke admin,
  delete), edit the clinical reference ranges used by Personal Doctor and
  Wellness Coach, post a site-wide announcement, and review reported issues.
  Admins can click "View as User" to preview the normal experience.

## Setup

```
pip install -r requirements.txt
cp .env.example .env        # then edit .env and add your own Anthropic API key
streamlit run app.py
```

Without an API key configured, the app still works — it shows rule-based
results and flags, just without AI-generated text (summaries, plans, search,
help chat).

### Accounts

- **Email/password**: sign up directly in the app with first/last name, age,
  country, email, and a password (8+ characters, one number, one uppercase
  letter).
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

### Becoming an admin

There's no signup toggle for admin — the first admin account is promoted
directly in the database (`db.set_admin(user_id, True)`). Admins can grant
or revoke admin for other accounts from the Users tab in the dashboard.

## Project structure

```
app.py                    Portal shell: auth gate, landing page, sidebar
                           help chat, admin dashboard, routing between services
auth.py                    password hashing/validation, Google OAuth flow,
                            "keep me logged in" tokens
db.py                      local SQLite storage: users, entries, settings,
                            issues
reference_ranges.py        reference ranges + flagging rules (admin-editable)
ai_advice.py                Claude API: Personal Doctor bloodwork summaries
ai_wellness.py               Claude API: Wellness Coach diet/exercise plans
ai_assistant.py              Claude API: site search bar + help chat
services/personal_doctor.py  Personal Doctor service UI
services/wellness_coach.py   Wellness Coach service UI
```

## Scope note

This is a working prototype demonstrating a full multi-service pipeline
(auth → service routing → rule-based analysis → AI explanation → trend
visualization) using data you enter yourself. It intentionally does **not**
implement file uploads or storage of real patient records — turning this
into something a healthcare company could deploy with real patient data
would require HIPAA/PIPEDA-compliant infrastructure (encryption at rest,
access controls, audit logging, BAAs with any third-party APIs used) that's
out of scope here.
