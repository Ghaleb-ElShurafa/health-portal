"""Generates diet/exercise plans and weekly adherence summaries for the
Fitness Coach service via the Gemini API. As with ai_advice.py, the "needs
doctor clearance before exercise" flag and all adherence/calorie numbers are
always computed independently with rule-based logic
(services/fitness_coach.py) and shown in the UI regardless of what the model
says — the AI only writes narrative text, never decides medical safety or
invents numbers.
"""

import gemini_client
from patient_context import build_patient_context

DISCLAIMER = (
    "This is a general wellness suggestion, not medical or nutritional advice tailored "
    "to your full health history. Always consult a healthcare provider before starting "
    "a new diet or exercise program, especially if any results above need attention."
)


def is_configured():
    return gemini_client.is_configured()


def _build_prompt(profile, bloodwork_summary, needs_clearance, questionnaire, uc_summary=None, health_profile=None):
    lines = []
    if profile.get("age") or profile.get("country"):
        lines.append(f"User: age {profile.get('age', 'unknown')}, country {profile.get('country', 'unknown')}.")

    context = build_patient_context(health_profile)
    if context:
        lines.append(context)

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
        lines.append("Conditions Tracker data (their own logged symptom/trigger history):")
        lines.append(uc_summary)

    lines.append("")
    lines.append(
        "Write a short diet plan (general food/nutrition guidance, not a strict meal-by-meal "
        "plan) and a short exercise plan (type, frequency, intensity), tailored to the "
        "questionnaire, patient profile (if any), and any bloodwork/Conditions Tracker "
        "findings above. "
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


def get_plan(profile, bloodwork_summary, needs_clearance, questionnaire, uc_summary=None, health_profile=None):
    if not is_configured():
        return (
            "AI plan unavailable: no GEMINI_API_KEY configured. "
            "See README for setup instructions."
        )

    prompt = _build_prompt(profile, bloodwork_summary, needs_clearance, questionnaire, uc_summary, health_profile)
    try:
        return gemini_client.generate(
            system_prompt=None,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
        )
    except gemini_client.GeminiUnavailableError:
        return "Your plan is temporarily unavailable (the AI service is busy) — try again in a moment."


def _build_adherence_prompt(days_worked_out, days_goal, muscle_group_counts, calories_burned, calories_in, profile=None):
    lines = [
        f"This week the user completed workouts on {days_worked_out} day(s)"
        + (f", against a goal of {days_goal} day(s) per week." if days_goal else ".")
    ]
    if muscle_group_counts:
        lines.append("Muscle groups worked and how many times this week:")
        for group, count in muscle_group_counts:
            lines.append(f"- {group}: {count}x")
    lines.append(f"Total estimated calories burned from logged workouts this week: {calories_burned:.0f} kcal.")
    if calories_in:
        lines.append(f"Total estimated calories consumed this week (from Plate Score meal logs): {calories_in:.0f} kcal.")
        lines.append(f"Net (intake minus burned from exercise, not total metabolism): {calories_in - calories_burned:.0f} kcal.")
    else:
        lines.append("No Plate Score meal logs on file this week to compare against.")

    context = build_patient_context(profile)
    if context:
        lines.append("")
        lines.append(context)

    lines.append("")
    lines.append(
        "Write a short, encouraging 2-4 sentence weekly recap: note adherence to the "
        "workout-day goal (if any), call out any noticeably under-worked or well-balanced "
        "muscle groups, and mention the calories burned vs eaten comparison if data exists. "
        "Do not invent numbers beyond what's given above, and don't give medical or "
        "nutritional advice beyond general encouragement."
    )
    return "\n".join(lines)


def get_adherence_summary(days_worked_out, days_goal, muscle_group_counts, calories_burned, calories_in=None, profile=None):
    """muscle_group_counts: list of (muscle_group, count) tuples for the week."""
    if not is_configured():
        return (
            "AI weekly recap unavailable: no GEMINI_API_KEY configured. "
            "See the numbers above for your raw weekly stats."
        )
    prompt = _build_adherence_prompt(days_worked_out, days_goal, muscle_group_counts, calories_burned, calories_in, profile)
    try:
        return gemini_client.generate(
            system_prompt=None,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
    except gemini_client.GeminiUnavailableError:
        return "Your weekly recap is temporarily unavailable (the AI service is busy) — try again in a moment."
