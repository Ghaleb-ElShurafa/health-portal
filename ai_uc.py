"""Generates a plain-language pattern summary for the UC Tracker service via
the Gemini API. As with the other AI modules, the actual food/flare
correlation numbers are computed independently with rule-based logic
(services/uc_tracker.py) — the AI only narrates what the numbers already
show, it doesn't invent or override them.
"""

import gemini_client
from patient_context import build_patient_context

DISCLAIMER = (
    "This is a pattern observation from your own logged data, not a medical diagnosis. "
    "Correlation isn't causation — confirm any suspected trigger foods with your "
    "gastroenterologist, ideally with a supervised elimination trial."
)


def is_configured():
    return gemini_client.is_configured()


def _build_prompt(food_stats, overall_flare_rate, num_entries, profile=None):
    lines = [
        f"The user has logged {num_entries} days. Overall flare rate: {overall_flare_rate:.0%} of days.",
        "",
        "Food vs. flare-day correlation (foods with at least 2 occurrences):",
    ]
    for food, stats in food_stats:
        lines.append(
            f"- {food}: eaten {stats['times_eaten']} times, "
            f"on a flare day {stats['times_on_flare']} times ({stats['flare_rate']:.0%} of the time)"
        )

    lines.append("")
    lines.append(
        "Write a short, plain-language summary (a few sentences) highlighting any foods "
        "that stand out as potential triggers (notably higher flare-rate than the overall "
        "baseline, with a reasonable sample size), and note if the data is too limited to "
        "draw conclusions yet. Do not diagnose or claim certainty — frame findings as "
        "patterns worth discussing with a doctor, not confirmed causes."
    )

    context = build_patient_context(profile)
    if context:
        lines.append("")
        lines.append(context)

    return "\n".join(lines)


def get_pattern_summary(food_stats, overall_flare_rate, num_entries, profile=None):
    """food_stats: list of (food_name, {"times_eaten", "times_on_flare", "flare_rate"}) tuples."""
    if not is_configured():
        return (
            "AI pattern summary unavailable: no GEMINI_API_KEY configured. "
            "See the table above for the raw numbers."
        )
    if not food_stats:
        return "Not enough data yet to spot patterns — keep logging entries."

    prompt = _build_prompt(food_stats, overall_flare_rate, num_entries, profile)
    try:
        return gemini_client.generate(
            system_prompt=None,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
    except gemini_client.GeminiUnavailableError:
        return (
            "AI summary is temporarily unavailable (the AI service is busy) — "
            "the table above still reflects your actual data. Try again in a moment."
        )
