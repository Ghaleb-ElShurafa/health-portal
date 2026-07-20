"""Generates the personalized "Statement of the Day" shown on the landing
page, using whatever context is available about the user (diagnosis, latest
Personal Doctor bloodwork, recent UC Tracker pattern). Cached per user per
day in the database so it's not regenerated on every page load.
"""

from datetime import date

import db
import gemini_client
import reference_ranges as rr

FALLBACK = "Welcome back — check in on your health data today."


def _bloodwork_context(user_id):
    entries = db.get_entries_for_user(user_id)
    if not entries:
        return None
    latest = max(entries, key=lambda e: e["entry_date"])
    thresholds = db.get_thresholds()
    sex = latest.get("sex", "Female")
    lines = []
    any_consult = False
    for key, (name, unit, flag_fn, needs_sex) in rr.METRICS.items():
        value = latest.get(key)
        if value is None:
            continue
        flag = flag_fn(value, sex, thresholds) if needs_sex else flag_fn(value, thresholds)
        lines.append(f"{name}: {flag.label}")
        if flag.status == "consult_doctor":
            any_consult = True
    if not lines:
        return None
    return {"summary": ", ".join(lines), "needs_doctor": any_consult, "date": latest["entry_date"]}


def _uc_context(user_id):
    entries = db.get_uc_entries_for_user(user_id)
    if not entries:
        return None
    recent = entries[-7:]
    flare_days = sum(1 for e in recent if e["flared"])
    return {"recent_days": len(recent), "flare_days": flare_days}


def _build_prompt(user, bloodwork, uc):
    lines = [f"User's first name: {user.get('first_name') or 'there'}."]
    if user.get("diagnosis"):
        lines.append(f"Diagnosed with: {user['diagnosis']}.")
    if bloodwork:
        lines.append(f"Latest bloodwork ({bloodwork['date']}): {bloodwork['summary']}.")
        if bloodwork["needs_doctor"]:
            lines.append("At least one bloodwork result needs medical attention.")
    if uc:
        lines.append(f"UC Tracker: {uc['flare_days']} flare day(s) out of the last {uc['recent_days']} logged.")

    lines.append("")
    lines.append(
        "Write ONE short, warm, encouraging sentence (max ~25 words) as a 'statement of "
        "the day' for this user's health dashboard — a practical tip or encouragement "
        "relevant to what's known about them above. No greeting, no sign-off, just the "
        "one statement. Do not diagnose or give urgent medical directives; if something "
        "needs a doctor, gently mention following up rather than alarming them."
    )
    return "\n".join(lines)


def get_statement(user):
    today = date.today().isoformat()

    if user["auth_provider"] == "guest":
        # Guests have no persistent id to cache against; generate fresh each session.
        user_id = None
    else:
        user_id = user["id"]
        cached = db.get_daily_statement(user_id, today)
        if cached:
            return cached

    if not gemini_client.is_configured():
        return FALLBACK

    bloodwork = _bloodwork_context(user_id) if user_id else None
    uc = _uc_context(user_id) if user_id else None
    prompt = _build_prompt(user, bloodwork, uc)

    try:
        statement = gemini_client.generate(
            system_prompt=None,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        ).strip()
    except gemini_client.GeminiUnavailableError:
        return FALLBACK

    if user_id:
        db.set_daily_statement(user_id, today, statement)
    return statement
