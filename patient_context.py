"""Shared helper for describing a user's Patient Profile (conditions,
medications, supplements, goals) inside AI prompts. Reused by every
service's ai_*.py module so profile fields are described consistently
and a change to how profile data is presented only has to happen once.
"""

_UNDISCLOSED = ("None", "Prefer not to say")


def build_patient_context(profile):
    """profile: dict with conditions, other_condition, medications,
    supplements, goals (as returned by db.get_patient_profile /
    services.patient_profile.get_profile). Returns a prompt-ready string,
    or "" if there's nothing disclosed to include.
    """
    if not profile:
        return ""

    conditions = [c for c in (profile.get("conditions") or []) if c not in _UNDISCLOSED]
    if profile.get("other_condition"):
        conditions.append(profile["other_condition"])
    goals = [g for g in (profile.get("goals") or []) if g not in _UNDISCLOSED]
    medications = (profile.get("medications") or "").strip()
    supplements = (profile.get("supplements") or "").strip()

    lines = []
    if conditions:
        lines.append(f"Medical conditions: {', '.join(conditions)}.")
    if medications:
        lines.append(f"Current medications: {medications}.")
    if supplements:
        lines.append(f"Supplements: {supplements}.")
    if goals:
        lines.append(f"Goals: {', '.join(goals)}.")

    if not lines:
        return ""

    return (
        "Patient profile on file:\n" + "\n".join(lines) + "\n"
        "Take this into account and personalize accordingly, but do not diagnose any "
        "condition or give urgent medical directives — frame anything concerning as "
        "something to discuss with a doctor, dietitian, or pharmacist (for "
        "medication-related considerations)."
    )
