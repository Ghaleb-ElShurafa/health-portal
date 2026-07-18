"""
Reference ranges for common bloodwork panels and a rule-based flagging engine.

Default thresholds are standard adult reference values (e.g. NCEP ATP III
cholesterol guidelines, ADA glucose/A1c thresholds, AHA blood pressure
categories) used for general education. They are not tuned to any
individual's personal medical history. Admins can override any threshold
through the admin dashboard; overrides are stored in the database
(db.get_thresholds() / db.set_threshold()) and merged over these defaults.
"""

from dataclasses import dataclass

DEFAULT_THRESHOLDS = {
    "total_cholesterol.borderline": 200,
    "total_cholesterol.high": 240,
    "ldl.near_optimal": 100,
    "ldl.borderline": 130,
    "ldl.high": 160,
    "ldl.very_high": 190,
    "hdl.low_male": 40,
    "hdl.low_female": 50,
    "hdl.protective": 60,
    "triglycerides.borderline": 150,
    "triglycerides.high": 200,
    "triglycerides.very_high": 500,
    "glucose_fasting.low": 70,
    "glucose_fasting.normal_max": 100,
    "glucose_fasting.diabetes": 126,
    "hba1c.prediabetes": 5.7,
    "hba1c.diabetes": 6.5,
    "bp.elevated_systolic": 120,
    "bp.stage1_systolic": 130,
    "bp.stage1_diastolic": 80,
    "bp.stage2_systolic": 140,
    "bp.stage2_diastolic": 90,
    "bp.crisis_systolic": 180,
    "bp.crisis_diastolic": 120,
}

# Grouped for the admin editing UI: (section title, [(threshold key, label), ...])
THRESHOLD_GROUPS = [
    ("Total Cholesterol (mg/dL)", [
        ("total_cholesterol.borderline", "Borderline high starts at"),
        ("total_cholesterol.high", "High starts at"),
    ]),
    ("LDL Cholesterol (mg/dL)", [
        ("ldl.near_optimal", "Near optimal starts at"),
        ("ldl.borderline", "Borderline high starts at"),
        ("ldl.high", "High starts at"),
        ("ldl.very_high", "Very high starts at"),
    ]),
    ("HDL Cholesterol (mg/dL)", [
        ("hdl.low_male", "Low threshold (male)"),
        ("hdl.low_female", "Low threshold (female)"),
        ("hdl.protective", "Protective starts at"),
    ]),
    ("Triglycerides (mg/dL)", [
        ("triglycerides.borderline", "Borderline high starts at"),
        ("triglycerides.high", "High starts at"),
        ("triglycerides.very_high", "Very high starts at"),
    ]),
    ("Fasting Glucose (mg/dL)", [
        ("glucose_fasting.low", "Low threshold"),
        ("glucose_fasting.normal_max", "Prediabetes starts at"),
        ("glucose_fasting.diabetes", "Diabetes starts at"),
    ]),
    ("HbA1c (%)", [
        ("hba1c.prediabetes", "Prediabetes starts at"),
        ("hba1c.diabetes", "Diabetes starts at"),
    ]),
    ("Blood Pressure (mmHg)", [
        ("bp.elevated_systolic", "Elevated systolic starts at"),
        ("bp.stage1_systolic", "Stage 1 systolic starts at"),
        ("bp.stage1_diastolic", "Stage 1 diastolic starts at"),
        ("bp.stage2_systolic", "Stage 2 systolic starts at"),
        ("bp.stage2_diastolic", "Stage 2 diastolic starts at"),
        ("bp.crisis_systolic", "Hypertensive crisis systolic starts at"),
        ("bp.crisis_diastolic", "Hypertensive crisis diastolic starts at"),
    ]),
]


@dataclass
class Flag:
    status: str          # "normal" | "watch" | "consult_doctor"
    label: str           # short human-readable status, e.g. "High"
    message: str         # one-line explanation of why


def flag_total_cholesterol(value, t=None):
    t = t or DEFAULT_THRESHOLDS
    if value < t["total_cholesterol.borderline"]:
        return Flag("normal", "Desirable", f"{value} mg/dL is in the desirable range (<{t['total_cholesterol.borderline']}).")
    if value < t["total_cholesterol.high"]:
        return Flag("watch", "Borderline high", f"{value} mg/dL is borderline high ({t['total_cholesterol.borderline']}-{t['total_cholesterol.high'] - 1}).")
    return Flag("consult_doctor", "High", f"{value} mg/dL is high (>={t['total_cholesterol.high']}).")


def flag_ldl(value, t=None):
    t = t or DEFAULT_THRESHOLDS
    if value < t["ldl.near_optimal"]:
        return Flag("normal", "Optimal", f"{value} mg/dL is optimal (<{t['ldl.near_optimal']}).")
    if value < t["ldl.borderline"]:
        return Flag("normal", "Near optimal", f"{value} mg/dL is near optimal ({t['ldl.near_optimal']}-{t['ldl.borderline'] - 1}).")
    if value < t["ldl.high"]:
        return Flag("watch", "Borderline high", f"{value} mg/dL is borderline high ({t['ldl.borderline']}-{t['ldl.high'] - 1}).")
    if value < t["ldl.very_high"]:
        return Flag("consult_doctor", "High", f"{value} mg/dL is high ({t['ldl.high']}-{t['ldl.very_high'] - 1}).")
    return Flag("consult_doctor", "Very high", f"{value} mg/dL is very high (>={t['ldl.very_high']}).")


def flag_hdl(value, sex, t=None):
    t = t or DEFAULT_THRESHOLDS
    threshold = t["hdl.low_male"] if sex == "Male" else t["hdl.low_female"]
    if value < threshold:
        return Flag("watch", "Low", f"{value} mg/dL is low (<{threshold}); low HDL is a risk factor.")
    if value >= t["hdl.protective"]:
        return Flag("normal", "Protective", f"{value} mg/dL is protective (>={t['hdl.protective']}).")
    return Flag("normal", "Normal", f"{value} mg/dL is in the normal range.")


def flag_triglycerides(value, t=None):
    t = t or DEFAULT_THRESHOLDS
    if value < t["triglycerides.borderline"]:
        return Flag("normal", "Normal", f"{value} mg/dL is normal (<{t['triglycerides.borderline']}).")
    if value < t["triglycerides.high"]:
        return Flag("watch", "Borderline high", f"{value} mg/dL is borderline high ({t['triglycerides.borderline']}-{t['triglycerides.high'] - 1}).")
    if value < t["triglycerides.very_high"]:
        return Flag("consult_doctor", "High", f"{value} mg/dL is high ({t['triglycerides.high']}-{t['triglycerides.very_high'] - 1}).")
    return Flag("consult_doctor", "Very high", f"{value} mg/dL is very high (>={t['triglycerides.very_high']}).")


def flag_glucose_fasting(value, t=None):
    t = t or DEFAULT_THRESHOLDS
    if value < t["glucose_fasting.low"]:
        return Flag("consult_doctor", "Low", f"{value} mg/dL is below normal (<{t['glucose_fasting.low']}); may indicate hypoglycemia.")
    if value < t["glucose_fasting.normal_max"]:
        return Flag("normal", "Normal", f"{value} mg/dL is normal ({t['glucose_fasting.low']}-{t['glucose_fasting.normal_max'] - 1}).")
    if value < t["glucose_fasting.diabetes"]:
        return Flag("watch", "Prediabetes range", f"{value} mg/dL is in the prediabetes range ({t['glucose_fasting.normal_max']}-{t['glucose_fasting.diabetes'] - 1}).")
    return Flag("consult_doctor", "Diabetes range", f"{value} mg/dL is in the diabetes range (>={t['glucose_fasting.diabetes']}).")


def flag_hba1c(value, t=None):
    t = t or DEFAULT_THRESHOLDS
    if value < t["hba1c.prediabetes"]:
        return Flag("normal", "Normal", f"{value}% is normal (<{t['hba1c.prediabetes']}%).")
    if value < t["hba1c.diabetes"]:
        return Flag("watch", "Prediabetes range", f"{value}% is in the prediabetes range ({t['hba1c.prediabetes']}-{t['hba1c.diabetes']}%).")
    return Flag("consult_doctor", "Diabetes range", f"{value}% is in the diabetes range (>={t['hba1c.diabetes']}%).")


def flag_blood_pressure(systolic, diastolic, t=None):
    t = t or DEFAULT_THRESHOLDS
    if systolic >= t["bp.crisis_systolic"] or diastolic >= t["bp.crisis_diastolic"]:
        return Flag("consult_doctor", "Hypertensive crisis", "Seek care promptly — this reading needs urgent medical attention.")
    if systolic >= t["bp.stage2_systolic"] or diastolic >= t["bp.stage2_diastolic"]:
        return Flag("consult_doctor", "Stage 2 hypertension", f"{systolic}/{diastolic} mmHg is in the Stage 2 hypertension range.")
    if systolic >= t["bp.stage1_systolic"] or diastolic >= t["bp.stage1_diastolic"]:
        return Flag("watch", "Stage 1 hypertension", f"{systolic}/{diastolic} mmHg is in the Stage 1 hypertension range.")
    if systolic >= t["bp.elevated_systolic"]:
        return Flag("watch", "Elevated", f"{systolic}/{diastolic} mmHg is elevated.")
    return Flag("normal", "Normal", f"{systolic}/{diastolic} mmHg is normal (<{t['bp.elevated_systolic']}/<{t['bp.stage1_diastolic']}).")


# Registry mapping metric key -> (display name, unit, flag function, needs_sex)
METRICS = {
    "total_cholesterol": ("Total Cholesterol", "mg/dL", flag_total_cholesterol, False),
    "ldl": ("LDL Cholesterol", "mg/dL", flag_ldl, False),
    "hdl": ("HDL Cholesterol", "mg/dL", flag_hdl, True),
    "triglycerides": ("Triglycerides", "mg/dL", flag_triglycerides, False),
    "glucose_fasting": ("Fasting Glucose", "mg/dL", flag_glucose_fasting, False),
    "hba1c": ("HbA1c", "%", flag_hba1c, False),
}
