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

BLOODWORK_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "total_cholesterol": {"type": "NUMBER", "nullable": True},
        "ldl": {"type": "NUMBER", "nullable": True},
        "hdl": {"type": "NUMBER", "nullable": True},
        "triglycerides": {"type": "NUMBER", "nullable": True},
        "glucose_fasting": {"type": "NUMBER", "nullable": True},
        "hba1c": {"type": "NUMBER", "nullable": True},
        "systolic": {"type": "NUMBER", "nullable": True},
        "diastolic": {"type": "NUMBER", "nullable": True},
        "test_date": {"type": "STRING", "nullable": True},
        "sex": {"type": "STRING", "nullable": True},
    },
}

EXTRACTION_PROMPT = (
    "This is a bloodwork/lab report document. Extract these values if present: "
    "total cholesterol, LDL, HDL, triglycerides (all mg/dL), fasting glucose (mg/dL), "
    "HbA1c (%), blood pressure systolic/diastolic (mmHg), the test date (as YYYY-MM-DD "
    "if determinable, otherwise as written), and patient sex if shown (\"Male\" or "
    "\"Female\"). Use null for anything not found or not legible. Do not guess or "
    "estimate a value that isn't actually in the document."
)


def is_configured():
    return gemini_client.is_configured()


def extract_from_document(file_bytes, mime_type):
    """Returns (values_dict_or_None, error_message_or_None)."""
    if not is_configured():
        return None, "AI extraction unavailable: no GEMINI_API_KEY configured. Enter values manually below."

    try:
        result = gemini_client.extract_from_document(
            EXTRACTION_PROMPT, file_bytes, mime_type, BLOODWORK_SCHEMA, max_tokens=800
        )
        return result, None
    except gemini_client.GeminiUnavailableError:
        return None, "AI extraction is temporarily unavailable (the service is busy) — try again, or enter values manually."
    except Exception:
        return None, "Couldn't read that document — try a clearer image/PDF, or enter values manually below."


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
    try:
        return gemini_client.generate(
            system_prompt=None,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
    except gemini_client.GeminiUnavailableError:
        return (
            "AI summary is temporarily unavailable (the AI service is busy) — "
            "your results and flags above are still accurate. Try again in a moment."
        )
