"""
Reference ranges for common bloodwork panels and a rule-based flagging engine.

Ranges are standard adult reference values (e.g. NCEP ATP III cholesterol
guidelines, ADA glucose/A1c thresholds, AHA blood pressure categories) used
for general education. They are not tuned to any individual's personal
medical history.
"""

from dataclasses import dataclass


@dataclass
class Flag:
    status: str          # "normal" | "watch" | "consult_doctor"
    label: str           # short human-readable status, e.g. "High"
    message: str         # one-line explanation of why


def _flag_range(value, low, high, low_label="Low", high_label="High", watch_only=False):
    if value < low:
        status = "watch" if watch_only else "consult_doctor"
        return Flag(status, low_label, f"{value} is below the normal range ({low}-{high}).")
    if value > high:
        status = "watch" if watch_only else "consult_doctor"
        return Flag(status, high_label, f"{value} is above the normal range ({low}-{high}).")
    return Flag("normal", "Normal", f"{value} is within the normal range ({low}-{high}).")


def flag_total_cholesterol(value):
    if value < 200:
        return Flag("normal", "Desirable", f"{value} mg/dL is in the desirable range (<200).")
    if value < 240:
        return Flag("watch", "Borderline high", f"{value} mg/dL is borderline high (200-239).")
    return Flag("consult_doctor", "High", f"{value} mg/dL is high (>=240).")


def flag_ldl(value):
    if value < 100:
        return Flag("normal", "Optimal", f"{value} mg/dL is optimal (<100).")
    if value < 130:
        return Flag("normal", "Near optimal", f"{value} mg/dL is near optimal (100-129).")
    if value < 160:
        return Flag("watch", "Borderline high", f"{value} mg/dL is borderline high (130-159).")
    if value < 190:
        return Flag("consult_doctor", "High", f"{value} mg/dL is high (160-189).")
    return Flag("consult_doctor", "Very high", f"{value} mg/dL is very high (>=190).")


def flag_hdl(value, sex):
    threshold = 40 if sex == "Male" else 50
    if value < threshold:
        return Flag("watch", "Low", f"{value} mg/dL is low (<{threshold}); low HDL is a risk factor.")
    if value >= 60:
        return Flag("normal", "Protective", f"{value} mg/dL is protective (>=60).")
    return Flag("normal", "Normal", f"{value} mg/dL is in the normal range.")


def flag_triglycerides(value):
    if value < 150:
        return Flag("normal", "Normal", f"{value} mg/dL is normal (<150).")
    if value < 200:
        return Flag("watch", "Borderline high", f"{value} mg/dL is borderline high (150-199).")
    if value < 500:
        return Flag("consult_doctor", "High", f"{value} mg/dL is high (200-499).")
    return Flag("consult_doctor", "Very high", f"{value} mg/dL is very high (>=500).")


def flag_glucose_fasting(value):
    if value < 70:
        return Flag("consult_doctor", "Low", f"{value} mg/dL is below normal (<70); may indicate hypoglycemia.")
    if value < 100:
        return Flag("normal", "Normal", f"{value} mg/dL is normal (70-99).")
    if value < 126:
        return Flag("watch", "Prediabetes range", f"{value} mg/dL is in the prediabetes range (100-125).")
    return Flag("consult_doctor", "Diabetes range", f"{value} mg/dL is in the diabetes range (>=126).")


def flag_hba1c(value):
    if value < 5.7:
        return Flag("normal", "Normal", f"{value}% is normal (<5.7%).")
    if value < 6.5:
        return Flag("watch", "Prediabetes range", f"{value}% is in the prediabetes range (5.7-6.4%).")
    return Flag("consult_doctor", "Diabetes range", f"{value}% is in the diabetes range (>=6.5%).")


def flag_blood_pressure(systolic, diastolic):
    if systolic >= 180 or diastolic >= 120:
        return Flag("consult_doctor", "Hypertensive crisis", "Seek care promptly — this reading needs urgent medical attention.")
    if systolic >= 140 or diastolic >= 90:
        return Flag("consult_doctor", "Stage 2 hypertension", f"{systolic}/{diastolic} mmHg is in the Stage 2 hypertension range.")
    if systolic >= 130 or diastolic >= 80:
        return Flag("watch", "Stage 1 hypertension", f"{systolic}/{diastolic} mmHg is in the Stage 1 hypertension range.")
    if systolic >= 120:
        return Flag("watch", "Elevated", f"{systolic}/{diastolic} mmHg is elevated.")
    return Flag("normal", "Normal", f"{systolic}/{diastolic} mmHg is normal (<120/<80).")


# Registry mapping metric key -> (display name, unit, flag function, needs_sex)
METRICS = {
    "total_cholesterol": ("Total Cholesterol", "mg/dL", flag_total_cholesterol, False),
    "ldl": ("LDL Cholesterol", "mg/dL", flag_ldl, False),
    "hdl": ("HDL Cholesterol", "mg/dL", flag_hdl, True),
    "triglycerides": ("Triglycerides", "mg/dL", flag_triglycerides, False),
    "glucose_fasting": ("Fasting Glucose", "mg/dL", flag_glucose_fasting, False),
    "hba1c": ("HbA1c", "%", flag_hba1c, False),
}
