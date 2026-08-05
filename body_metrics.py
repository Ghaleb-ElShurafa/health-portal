"""Shared BMI math and unit conversion, used by Patient Profile (data entry)
and Fitness Coach (scaling the muscle-figure diagram to the user's build).
Kept separate from both so neither service has to import the other.
"""

BMI_CATEGORIES = [
    (18.5, "Underweight"),
    (25.0, "Normal"),
    (30.0, "Overweight"),
    (float("inf"), "Obese"),
]


def compute_bmi(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    height_m = height_cm / 100
    return weight_kg / (height_m ** 2)


def bmi_category(bmi):
    if bmi is None:
        return "Normal"  # undisclosed/not-provided build defaults to a neutral figure
    for ceiling, label in BMI_CATEGORIES:
        if bmi < ceiling:
            return label
    return "Obese"


def kg_to_lb(kg):
    return kg * 2.2046226218


def lb_to_kg(lb):
    return lb / 2.2046226218


def cm_to_ft_in(cm):
    total_inches = cm / 2.54
    feet = int(total_inches // 12)
    inches = total_inches - feet * 12
    return feet, inches


def ft_in_to_cm(feet, inches):
    return ((feet or 0) * 12 + (inches or 0)) * 2.54
