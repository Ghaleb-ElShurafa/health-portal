"""Generates a plain-language pattern + trend summary for the Conditions
Tracker service via the Gemini API. As with the other AI modules, the actual
trigger correlation and trend numbers are computed independently with
rule-based logic — the AI only narrates what the numbers already show, it
doesn't invent or override them.
"""

import gemini_client
from patient_context import build_patient_context

DISCLAIMER = (
    "This is a pattern observation from your own logged data, not a medical diagnosis. "
    "Correlation isn't causation — confirm any suspected triggers with your doctor, "
    "ideally with a supervised elimination trial where relevant."
)


def is_configured():
    return gemini_client.is_configured()


def _compute_trend(entries):
    """Rule-based trend signal: compares the symptom rate in the most recent
    half of logged days against the earlier half. Returns None if there
    isn't enough data yet for a meaningful comparison.
    """
    if len(entries) < 6:
        return None

    sorted_entries = sorted(entries, key=lambda e: e["entry_date"])
    mid = len(sorted_entries) // 2
    earlier, recent = sorted_entries[:mid], sorted_entries[mid:]

    def rate(chunk):
        return sum(1 for e in chunk if e["symptom_occurred"]) / len(chunk)

    earlier_rate, recent_rate = rate(earlier), rate(recent)
    diff = recent_rate - earlier_rate
    if diff <= -0.15:
        label = "improving"
    elif diff >= 0.15:
        label = "worsening"
    else:
        label = "stable"
    return {"label": label, "earlier_rate": earlier_rate, "recent_rate": recent_rate}


def _build_prompt(condition, trigger_stats, overall_rate, entries, profile=None):
    lines = [
        f"Tracking: {condition}. The user has logged {len(entries)} days. "
        f"Overall symptom rate: {overall_rate:.0%} of days.",
    ]

    trend = _compute_trend(entries)
    if trend:
        lines.append(
            f"Trend (recent half of logged days vs. earlier half): recent symptom rate "
            f"{trend['recent_rate']:.0%} vs. earlier {trend['earlier_rate']:.0%} — "
            f"this is categorized as **{trend['label']}**."
        )
    else:
        lines.append("Not enough logged days yet for a reliable trend comparison (need at least 6).")

    lines.append("")
    lines.append("Trigger vs. symptom-day correlation (triggers with at least 2 occurrences):")
    for trigger, stats in trigger_stats:
        lines.append(
            f"- {trigger}: occurred {stats['times_occurred']} times, "
            f"on a symptom day {stats['times_with_symptom']} times ({stats['symptom_rate']:.0%} of the time)"
        )
    if not trigger_stats:
        lines.append("(none with enough occurrences yet)")

    lines.append("")
    lines.append(
        "Write a short, plain-language summary (a few sentences): state whether things "
        "look like they're improving, worsening, or staying stable/normal based on the "
        "trend above, then highlight any triggers that stand out (notably higher "
        "symptom-rate than the overall baseline, with a reasonable sample size). Note if "
        "the data is too limited to draw conclusions yet. Do not diagnose or claim "
        "certainty — frame findings as patterns worth discussing with a doctor, not "
        "confirmed causes."
    )

    context = build_patient_context(profile)
    if context:
        lines.append("")
        lines.append(context)

    return "\n".join(lines)


def get_pattern_summary(condition, trigger_stats, overall_rate, entries, profile=None):
    """trigger_stats: list of (trigger_name, {"times_occurred", "times_with_symptom",
    "symptom_rate"}) tuples. entries: the raw list of logged day dicts, used
    to compute the trend.
    """
    if not is_configured():
        return (
            "AI pattern summary unavailable: no GEMINI_API_KEY configured. "
            "See the table above for the raw numbers."
        )
    if not entries:
        return "Not enough data yet to spot patterns — keep logging entries."

    prompt = _build_prompt(condition, trigger_stats, overall_rate, entries, profile)
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
