"""Generates diet and exercise plans for the Wellness Coach service via the
Gemini API. As with ai_advice.py, the "needs doctor clearance before
exercise" flag is always computed independently with rule-based logic
(services/wellness_coach.py) and shown in the UI regardless of what the
model says — the AI only writes the plan text, never decides medical safety.
"""

import gemini_client

DISCLAIMER = (
    "This is a general wellness suggestion, not medical or nutritional advice tailored "
    "to your full health history. Always consult a healthcare provider before starting "
    "a new diet or exercise program, especially if any results above need attention."
)


def is_configured():
    return gemini_client.is_configured()


def _build_prompt(profile, bloodwork_summary, needs_clearance, questionnaire, uc_summary=None):
    lines = []
    if profile.get("age") or profile.get("country"):
        lines.append(f"User: age {profile.get('age', 'unknown')}, country {profile.get('country', 'unknown')}.")
    if profile.get("diagnosis"):
        lines.append(
            f"Diagnosed with: {profile['diagnosis']}. Tailor both the diet and exercise "
            "guidance specifically for someone managing this condition (e.g. common "
            "trigger foods to be cautious with, flare-safe exercise intensity), in "
            "addition to the questionnaire and bloodwork below."
        )

    lines.append("")
    lines.append("Questionnaire:")
    for label, value in questionnaire.items():
        if value:
            lines.append(f"- {label}: {value}")

    if bloodwork_summary:
        lines.append("")
        lines.append("Most recent bloodwork on file:")
        lines.extend(bloodwork_summary)
    else:
        lines.append("")
        lines.append("No bloodwork on file — base the plan on the questionnaire only.")

    if uc_summary:
        lines.append("")
        lines.append("UC Tracker data (their own logged flare/food history):")
        lines.append(uc_summary)

    lines.append("")
    lines.append(
        "Write a short diet plan (general food/nutrition guidance, not a strict meal-by-meal "
        "plan) and a short exercise plan (type, frequency, intensity), tailored to the "
        "questionnaire, diagnosis (if any), and any bloodwork/UC Tracker findings above. "
        "Do not diagnose any condition. "
        + (
            "At least one bloodwork result needs medical attention — recommend the user get "
            "medical clearance before starting a new exercise program, and keep exercise "
            "suggestions conservative/light until they do."
            if needs_clearance
            else "Bloodwork (if any) looks acceptable — normal general exercise guidance is fine."
        )
    )
    return "\n".join(lines)


def get_plan(profile, bloodwork_summary, needs_clearance, questionnaire, uc_summary=None):
    if not is_configured():
        return (
            "AI plan unavailable: no GEMINI_API_KEY configured. "
            "See README for setup instructions."
        )

    prompt = _build_prompt(profile, bloodwork_summary, needs_clearance, questionnaire, uc_summary)
    try:
        return gemini_client.generate(
            system_prompt=None,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
        )
    except gemini_client.GeminiUnavailableError:
        return "Your plan is temporarily unavailable (the AI service is busy) — try again in a moment."
