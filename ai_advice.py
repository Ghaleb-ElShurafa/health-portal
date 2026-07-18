"""Generates plain-language explanations and lifestyle suggestions via the
Gemini API, given rule-based flags computed locally (reference_ranges.py).

The rule-based "consult a doctor" flag is always computed independently and
displayed in the UI regardless of what the model says — the AI is only
responsible for the explanatory text, never for deciding whether a finding
is urgent.
"""

import gemini_client

DISCLAIMER = (
    "This is general educational information, not medical advice or a diagnosis. "
    "Always consult a healthcare provider about your results."
)


def is_configured():
    return gemini_client.is_configured()


def _build_prompt(results, sex):
    lines = [f"Patient sex: {sex}", "", "Lab results:"]
    any_consult = False
    for name, unit, value, flag in results:
        lines.append(f"- {name}: {value} {unit} -> {flag.label} ({flag.status})")
        if flag.status == "consult_doctor":
            any_consult = True

    lines.append("")
    lines.append(
        "Write a short, plain-language summary (a few sentences) of these results for "
        "the patient, then 2-4 concrete, general lifestyle/diet suggestions relevant to "
        "any out-of-range values. Do not diagnose any condition. "
        + (
            "At least one value needs a doctor's attention — say so clearly and encourage "
            "the patient to follow up, without being alarmist."
            if any_consult
            else "All values are in the normal or watch range — you may still gently note "
            "any general health habits that could help maintain them."
        )
    )
    return "\n".join(lines)


def get_advice(results, sex):
    """results: list of (display_name, unit, value, Flag) tuples."""
    if not is_configured():
        return (
            "AI explanation unavailable: no GEMINI_API_KEY configured. "
            "Showing rule-based results only. See README for setup instructions."
        )

    prompt = _build_prompt(results, sex)
    return gemini_client.generate(
        system_prompt=None,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
