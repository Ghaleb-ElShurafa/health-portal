# Health Services Portal

A multi-service health app built with Streamlit. Users sign up, land on a
personalized dashboard, and open individual tools — currently **Personal
Doctor** (upload bloodwork documents, AI-extracted and tracked over time),
**Wellness Coach** (diet/exercise plans tailored to diagnosis + bloodwork +
UC Tracker data), **UC Tracker** (log flares and food to spot ulcerative
colitis trigger patterns), and **Plate Score** (photograph a meal for an
AI-scored calorie/nutrition breakdown, personalized to your diagnosis and
goal). More services can be added as new cards on the landing page.

**⚠️ Not medical advice.** This is an educational/portfolio project. It does
not diagnose or treat any condition. "Consult a doctor" flags are always
computed with local rule-based logic (`reference_ranges.py`), independent of
the AI — the model only writes explanatory text, never decides what's urgent.

## Features

- **Accounts**: email/password (with name, age, country of residence, an
  optional diagnosis, and an optional dietary/fitness goal), Google sign-in,
  or a guest mode that asks for a display name (no account needed
  otherwise). "Keep me logged in" persists a session via a browser cookie
  for 30 days. Diagnosis and goal can be set at signup or updated anytime
  from the landing page.
- **Personal Doctor**: upload a photo or PDF of a lab report — Gemini reads
  the document directly (no OCR step) and pre-fills a lipid panel,
  glucose/HbA1c, and blood pressure form for you to review and edit before
  saving. Every save is flagged against standard adult reference ranges
  (NCEP ATP III cholesterol guidelines, ADA glucose/A1c thresholds, AHA blood
  pressure categories), gets an AI-generated plain-language summary, and adds
  to trend charts across every bloodwork entry on file over time.
- **Wellness Coach**: a diet + exercise plan personalized from your latest
  Personal Doctor bloodwork, your diagnosis (if set), and your UC Tracker
  history (if any) — falls back to a short questionnaire if none of that
  exists yet. Recommends medical clearance before exercise whenever
  bloodwork has a "consult a doctor" flag.
- **UC Tracker**: log each day's flare status (yes/no + severity) and the
  foods you ate. The app computes a food-vs-flare-day correlation table
  (rule-based, not AI) and an AI narrative highlighting likely trigger foods
  — correlation, not diagnosis, always framed as something to discuss with
  a gastroenterologist.
- **Plate Score**: take a photo (camera or upload, works on phone and
  desktop) of a meal — Gemini identifies the food, estimates calories and
  macros, and returns a 1-10 health score with a short written assessment,
  all in one pass. Diagnosis and goal (if set) are folded into that same
  prompt, so a diabetic profile gets sugar/carb-aware scoring while a
  muscle-gain goal gets protein-adequacy feedback. Each analysis auto-logs
  to a history with a calories-over-time trend chart and today's running
  total. Photos themselves are never stored, only the extracted values.
- **AI search bar**: ask anything on the landing page.
- **Help & Support sidebar**: an AI chat that can help with genuinely
  anything — site navigation, technical issues, or general questions — plus
  a "report a technical issue" form that logs to the admin dashboard.
- **Admin dashboard** (for admin accounts): manage users (grant/revoke admin,
  delete), edit the clinical reference ranges used across services, post a
  site-wide announcement, review reported issues, and see a sign-in activity
  log (every password/Google/guest login, plus auto-logins via "keep me
  logged in", with who and when). Admins can click "View as User" to preview
  the normal experience. The Streamlit toolbar (Deploy button, hamburger
  menu) is hidden from everyone — admin controls live in this in-app
  dashboard instead, not Streamlit's own chrome.

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
help chat, document extraction, statement of the day).

### AI features (Gemini)

All AI text and document extraction runs on Google's
[Gemini API](https://aistudio.google.com), using the free tier — no credit
card needed. The client (`gemini_client.py`) talks to Gemini's REST API
directly via `requests` rather than Google's official SDK, since that SDK
depends on `google-auth` → `cryptography`, which needs a Rust toolchain not
available in this dev environment. Gemini API keys are simple bearer keys
(not OAuth), so a plain HTTP call works fine without any of that. It also
retries transient failures (rate limits, 5xx errors) with backoff, and every
AI-calling module falls back to a friendly "busy, try again" message instead
of crashing if Gemini is unavailable.

Bloodwork document extraction uses Gemini's multimodal input (the image/PDF
is sent directly, no separate OCR step) with structured JSON output
(`responseSchema`) so the extracted values map directly onto the app's
existing fields.

Primary model is `gemini-flash-lite-latest`, with automatic fallback to two
other models (`gemini_client.py`'s `MODEL_FALLBACKS` list) if the primary one
is having its own outage — this has happened in practice (a multi-hour
`-latest` alias outage on Google's end) and is otherwise invisible to users.
Each model gets retried with exponential backoff on rate limits/5xx errors
before moving to the next one; a genuinely bad request (e.g. an invalid API
key) fails immediately instead of retrying pointlessly.

### Accounts

- **Email/password**: sign up directly in the app with first/last name, age,
  country, an optional diagnosis, email, and a password (8+ characters, one
  number, one uppercase letter).
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

### Render (recommended)

[Render](https://render.com) deploys straight from this GitHub repo on its
free tier, gives you a URL like `https://health-portal.onrender.com`, and —
unlike Streamlit Community Cloud — automatically restarts the app whenever
an environment variable changes, so there's no separate manual reboot step
after updating a secret.

1. Sign up at [render.com](https://render.com) and connect your GitHub
   account.
2. Click **New → Blueprint**, pick this repo. Render auto-detects
   `render.yaml` in the repo root and proposes the `health-portal` web
   service defined there.
3. When prompted for the environment variables it left blank
   (`GEMINI_API_KEY`, `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`), paste in
   your own values — this is where credentials belong, never commit them.
4. Deploy. Every `git push` to this repo redeploys automatically from then
   on, and so does every future secret change.

Free-tier apps on Render still spin down after 15 minutes of inactivity and
take a bit to cold-start on the next visit — same as any $0 host. A free
uptime pinger (e.g. [UptimeRobot](https://uptimerobot.com) or
[cron-job.org](https://cron-job.org)) hitting the URL every few minutes
keeps it warm if that matters to you.

### Streamlit Community Cloud (alternative)

Also free and deploys from this same repo, at a `https://your-app.streamlit.app`
URL — see git history for the previous setup steps. In practice this app hit
a build that stopped picking up new pushes, which Render's independent build
pipeline sidesteps; Streamlit Cloud also has a known quirk where secret
changes don't reliably auto-restart the app (a manual "Reboot app" click in
the Manage app panel is needed), unlike Render's automatic restart-on-change.

### Persistent storage (Turso)

Local SQLite (the default) works great for development, but most hosting
platforms don't guarantee that disk survives a restart or redeploy. For a
public deployment, point the app at a free [Turso](https://turso.tech)
database (SQLite-compatible, so no schema changes needed) instead:

1. Sign up at [turso.tech](https://turso.tech) (free tier).
2. Create a database: `turso db create health-portal` (via their CLI, or the
   web dashboard).
3. Get the URL: `turso db show health-portal --url`
4. Create an auth token: `turso db tokens create health-portal`
5. Set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` — locally in `.env`, and
   in whichever host's environment variable / secrets panel you deploy to.

If those two variables aren't set, the app automatically falls back to the
local SQLite file — nothing else to configure either way.

`db.py` connects over HTTP (not the `libsql://` WebSocket scheme) since each
call here is a short one-off request and the WebSocket handshake was
unreliable in testing.

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
app.py                        Portal shell: auth gate, landing page, sidebar
                               help chat, admin dashboard, routing between services
auth.py                        password hashing/validation, Google OAuth flow,
                                "keep me logged in" tokens, diagnosis, goal
db.py                          storage: users, entries, UC entries, meal
                                entries, settings, issues, activity log —
                                local SQLite by default, or Turso if configured
styles.py                      custom CSS (gradient background, card/button
                                styling) injected on every page
pwa.py                          patches Streamlit's static files to make the
                                app installable (manifest, service worker)
pwa/                            PWA manifest, service worker, and icons
reference_ranges.py            reference ranges + flagging rules (admin-editable)
gemini_client.py                Gemini REST client: text generation, multimodal
                                 document extraction, retry/backoff/fallback
ai_advice.py                     Personal Doctor bloodwork summaries + document extraction
ai_wellness.py                    Wellness Coach diet/exercise plans
ai_uc.py                          UC Tracker pattern narrative
ai_food.py                        Plate Score meal photo analysis + scoring
ai_assistant.py                   site search bar + help chat
services/personal_doctor.py      Personal Doctor service UI
services/wellness_coach.py       Wellness Coach service UI
services/uc_tracker.py           UC Tracker service UI
services/plate_score.py          Plate Score service UI
.streamlit/config.toml           hides the Streamlit toolbar and raw error
                                  tracebacks from all users
```

## Scope note

This is a working prototype demonstrating a full multi-service pipeline
(auth → service routing → rule-based analysis → AI explanation → trend
visualization) using data you enter or upload yourself. Uploaded bloodwork
documents are read by Gemini for extraction and are not stored — only the
extracted values are kept. Turning this into something a healthcare company
could deploy with real patient data would require HIPAA/PIPEDA-compliant
infrastructure (encryption at rest, access controls, audit logging, BAAs
with any third-party APIs used) that's out of scope here.
