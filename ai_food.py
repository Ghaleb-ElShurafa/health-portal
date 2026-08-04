"""AI food-photo analysis for Plate Score: identifies food, estimates calories
and macros, and produces a personalized health score + written assessment in a
single Gemini multimodal call. The user's diagnosis and dietary goal (if set)
are folded into the same prompt so scoring and advice are personalized without
a second round-trip.
"""

import gemini_client

DISCLAIMER = (
    "This is an estimate from a photo, not a lab measurement or medical advice. "
    "Actual calories and nutrients can vary significantly from what's shown here — "
    "always consult a doctor or registered dietitian for a condition-specific diet plan."
)

MEAL_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "food_items": {"type": "STRING"},
        "estimated_calories": {"type": "NUMBER"},
        "protein_g": {"type": "NUMBER"},
        "carbs_g": {"type": "NUMBER"},
        "fat_g": {"type": "NUMBER"},
        "health_score": {"type": "NUMBER"},
        "assessment": {"type": "STRING"},
    },
    "required": [
        "food_items", "estimated_calories", "protein_g", "carbs_g",
        "fat_g", "health_score", "assessment",
    ],
}

# Loose plausibility bounds for a single meal — catches the rare case where
# the model returns a syntactically valid but nonsensical number (e.g. a
# degenerate value like 1000000) instead of failing outright.
_PLAUSIBLE_RANGES = {
    "estimated_calories": (0, 4000),
    "protein_g": (0, 300),
    "carbs_g": (0, 500),
    "fat_g": (0, 300),
    "health_score": (1, 10),
}


def _is_plausible(result):
    return all(
        lo <= result.get(field, lo) <= hi
        for field, (lo, hi) in _PLAUSIBLE_RANGES.items()
    )


def is_configured():
    return gemini_client.is_configured()


def _build_prompt(user):
    lines = [
        "This is a photo of a meal for a diet-tracking app. Identify the food items "
        "(a short comma-separated list), estimate total calories and macros (protein, "
        "carbs, fat in grams) for the whole plate, and give a health_score from 1 "
        "(very unhealthy) to 10 (excellent, well-balanced) for a generally healthy diet."
    ]

    if user.get("diagnosis"):
        lines.append(
            f"This user's health profile notes: {user['diagnosis']}. Weight the score "
            "and assessment toward what matters for that condition (e.g. flag high sugar "
            "or refined carbs clearly for diabetes, high sodium for blood pressure concerns)."
        )
    if user.get("goal"):
        lines.append(
            f"This user's dietary/fitness goal is: {user['goal']}. Weight the score and "
            "assessment toward that goal (e.g. protein adequacy for muscle gain, calorie "
            "appropriateness for weight loss)."
        )
    if not user.get("diagnosis") and not user.get("goal"):
        lines.append(
            "No specific health condition or dietary goal is on file — score and assess "
            "for general balanced nutrition."
        )

    lines.append(
        "Then write a short (3-4 sentence) assessment: note what's good about the meal, "
        "flag any specific concern relevant to the profile above if applicable, and give "
        "one practical, actionable suggestion. Do not diagnose any condition or give urgent "
        "medical directives — frame concerns as something to discuss with a doctor or dietitian."
    )
    return "\n".join(lines)


def analyze_meal_photo(file_bytes, mime_type, user):
    """Returns (result_dict_or_None, error_message_or_None). result_dict has
    keys: food_items, estimated_calories, protein_g, carbs_g, fat_g,
    health_score, assessment.
    """
    if not is_configured():
        return None, "AI analysis unavailable: no GEMINI_API_KEY configured. See README."

    prompt = _build_prompt(user)
    for _ in range(2):
        try:
            result = gemini_client.extract_from_document(prompt, file_bytes, mime_type, MEAL_SCHEMA, max_tokens=1200)
        except gemini_client.GeminiUnavailableError:
            return None, "AI analysis is temporarily unavailable (the service is busy) — try again in a moment."
        except Exception:
            return None, "Couldn't read that photo clearly — try a clearer photo with better lighting, or from directly above the plate."
        if _is_plausible(result):
            return result, None
    return None, "AI analysis returned an implausible result — try again, or try a clearer photo."
