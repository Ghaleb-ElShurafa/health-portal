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
- **Wellness Coach**: a diet + exercise plan from the Gemini API, informed by
  your latest Personal Doctor bloodwork when available (falls back to a
  short questionnaire otherwise). Recommends medical clearance before
  exercise whenever bloodwork has a "consult a doctor" flag.
- **AI search bar**: ask anything on the landing page (Gemini API).
- **Help & Support sidebar**: an AI chat for navigation/technical questions,
  plus a "report a technical issue" form that logs to the admin dashboard.
- **Admin dashboard** (for admin accounts): manage users (grant/revoke admin,
  delete), edit the clinical reference ranges used by Personal Doctor and
  Wellness Coach, post a site-wide announcement, and review reported issues.
  Admins can click "View as User" to preview the normal experience.

## Setup

```
pip install -r requirements.txt
cp .env.example .env        # then edit .env and add your own free Gemini API key
streamlit run app.py
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com)
(no credit card required — see "AI features" below for details).

Without an API key configured, the app still works — it shows rule-based
results and flags, just without AI-generated text (summaries, plans, search,
help chat).

### AI features (Gemini)

AI text (bloodwork summaries, Wellness Coach plans, the search bar, and the
help chat) runs on Google's [Gemini API](https://aistudio.google.com), using
Gemini's free tier — no credit card needed, ~1,500 requests/day. The client
(`gemini_client.py`) talks to Gemini's REST API directly via `requests`
rather than Google's official SDK, since that SDK depends on `google-auth` →
`cryptography`, which needs a Rust toolchain not available in this dev
environment. Gemini API keys are simple bearer keys (not OAuth), so a plain
HTTP call works fine without any of that.

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

## Deploying to a public URL

The recommended path is [Streamlit Community Cloud](https://streamlit.io/cloud) —
free, deploys straight from this GitHub repo, and gives you a URL like
`https://your-app-name.streamlit.app`.

1. Sign in at [share.streamlit.io](https://share.streamlit.io) with your
   GitHub account and authorize it to access this repo.
2. Click "New app", pick this repo/branch, and set the main file to `app.py`.
3. In the app's **Settings → Secrets**, paste in (this is where credentials
   belong — never commit them):
   ```
   GEMINI_API_KEY = "..."
   TURSO_DATABASE_URL = "libsql://your-db-name.turso.io"
   TURSO_AUTH_TOKEN = "..."

   [google_oauth]
   client_id = "..."
   client_secret = "..."
   redirect_uri = "https://your-app-name.streamlit.app"
   ```
4. Deploy. Every `git push` to this repo redeploys automatically.

   **Important:** saving secrets does not reliably auto-restart the app —
   after adding/changing secrets, manually click **"Reboot app"** (Manage
   app panel) or the new values won't be picked up.

### Persistent storage (Turso)

Local SQLite (the default) works great for development, but most hosting
platforms — including Streamlit Community Cloud — don't guarantee that disk
survives a restart or redeploy. For a public deployment, point the app at a
free [Turso](https://turso.tech) database (SQLite-compatible, so no schema
changes needed) instead:

1. Sign up at [turso.tech](https://turso.tech) (free tier).
2. Create a database: `turso db create health-portal` (via their CLI, or the
   web dashboard).
3. Get the URL: `turso db show health-portal --url`
4. Create an auth token: `turso db tokens create health-portal`
5. Set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` — locally in `.env`, and
   on Streamlit Cloud in Settings → Secrets (step 3 above).

If those two variables aren't set, the app automatically falls back to the
local SQLite file — nothing else to configure either way.

## Installing as an app (PWA)

Once deployed to a public HTTPS URL (PWAs require a secure context — plain
`localhost` works for testing, but not a bare HTTP address), visit the site
in Chrome/Edge and use the browser's **Install** option (an icon in the
address bar, or "Install app" in the menu) to add it as a standalone app
with its own icon and window — no app store needed. Because it's the same
deployed URL, it always reflects your latest `git push`; there's nothing
separate to keep in sync.

## Project structure

```
app.py                    Portal shell: auth gate, landing page, sidebar
                           help chat, admin dashboard, routing between services
auth.py                    password hashing/validation, Google OAuth flow,
                            "keep me logged in" tokens
db.py                      storage: users, entries, settings, issues —
                            local SQLite by default, or Turso if configured
pwa.py                      patches Streamlit's static files to make the
                            app installable (manifest, service worker)
pwa/                        PWA manifest, service worker, and icons
reference_ranges.py        reference ranges + flagging rules (admin-editable)
gemini_client.py            minimal Gemini REST client (no official SDK)
ai_advice.py                 Personal Doctor bloodwork summaries
ai_wellness.py                Wellness Coach diet/exercise plans
ai_assistant.py               site search bar + help chat
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
