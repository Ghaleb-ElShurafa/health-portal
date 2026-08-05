"""Patient Profile service: a general health-screening intake — conditions,
medications, supplements, goals, and optional body metrics (height, weight,
sex) — that personalizes every other service in the portal (Bloodwork
Analysis, Fitness Coach, Conditions Tracker, Plate Score).
"""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

import body_metrics
import db

NOT_DISCLOSED = ["None", "Prefer not to say"]

SEX_OPTIONS = ["Prefer not to say", "Male", "Female"]

CONDITIONS = NOT_DISCLOSED + [
    "Type 1 Diabetes", "Type 2 Diabetes", "Prediabetes",
    "Hypertension (High Blood Pressure)", "High Cholesterol", "Heart Disease",
    "Arrhythmia", "Obesity", "Metabolic Syndrome", "PCOS (Polycystic Ovary Syndrome)",
    "Hypothyroidism", "Hyperthyroidism",
    "Ulcerative Colitis", "Crohn's Disease", "Irritable Bowel Syndrome (IBS)",
    "Celiac Disease", "Peptic Ulcer", "Stomach Ulcer", "GERD / Acid Reflux",
    "Lactose Intolerance", "Diverticulitis", "Gallstones",
    "Asthma", "COPD", "Sleep Apnea", "Seasonal Allergies", "Food Allergies",
    "Rheumatoid Arthritis", "Osteoarthritis", "Osteoporosis", "Gout",
    "Fibromyalgia", "Chronic Back Pain",
    "Depression", "Anxiety Disorder", "Bipolar Disorder", "ADHD", "Insomnia",
    "Chronic Kidney Disease", "Kidney Stones",
    "Eczema", "Psoriasis", "Acne", "Rosacea",
    "Migraine", "Epilepsy", "Multiple Sclerosis",
    "Anemia", "Iron Deficiency",
    "Autoimmune Disease (other)", "Cancer (active or in remission)", "Pregnancy",
]

GOALS = NOT_DISCLOSED + [
    "Weight loss", "Weight gain / muscle growth", "Maintain current weight",
    "General health improvement", "Diet change / healthier eating",
    "Manage a chronic condition", "Improve energy levels", "Better sleep",
    "Reduce stress", "Increase physical activity", "Improve heart health",
    "Lower cholesterol", "Manage blood sugar", "Pregnancy nutrition",
]


def get_profile(user):
    """Public helper other services use to read the current profile."""
    if user["auth_provider"] == "guest":
        st.session_state.setdefault("guest_patient_profile", dict(db.EMPTY_PATIENT_PROFILE))
        return st.session_state.guest_patient_profile
    return db.get_patient_profile(user["id"])


def summary_line(profile):
    """Short one-line summary for display elsewhere (e.g. the landing page)."""
    bits = []
    conditions = list(profile.get("conditions") or [])
    if profile.get("other_condition"):
        conditions.append(profile["other_condition"])
    if conditions:
        bits.append("Conditions: " + ", ".join(conditions))
    if profile.get("goals"):
        bits.append("Goals: " + ", ".join(profile["goals"]))
    return " · ".join(bits)


def _has_data(profile):
    return bool(
        profile.get("conditions") or profile.get("other_condition")
        or profile.get("medications") or profile.get("supplements") or profile.get("goals")
        or profile.get("height_cm") or profile.get("weight_kg")
    )


def _save_notice():
    if not st.session_state.get("pp_just_saved"):
        return
    with st.container(border=True):
        col1, col2 = st.columns([9, 1])
        with col1:
            st.success("✅ Profile saved — this will now personalize your other services.")
        with col2:
            if st.button("✕", key="dismiss_pp_saved", help="Close"):
                st.session_state.pp_just_saved = False
                st.rerun()


def _render_summary(user, profile):
    st.subheader("Your profile")
    with st.container(border=True):
        conditions = list(profile.get("conditions") or [])
        if profile.get("other_condition"):
            conditions.append(profile["other_condition"])

        if conditions:
            st.markdown("**🩺 Medical conditions**")
            st.write(", ".join(conditions))
        if profile.get("medications"):
            st.markdown("**💊 Current medications**")
            st.write(profile["medications"])
        if profile.get("supplements"):
            st.markdown("**🌿 Supplements**")
            st.write(profile["supplements"])
        if profile.get("goals"):
            st.markdown("**🎯 Goals**")
            st.write(", ".join(profile["goals"]))

        if profile.get("height_cm") or profile.get("weight_kg"):
            st.markdown("**📏 Body metrics**")
            bits = []
            if profile.get("height_cm"):
                feet, inches = body_metrics.cm_to_ft_in(profile["height_cm"])
                bits.append(f"Height: {profile['height_cm']:.0f} cm ({feet} ft {inches:.0f} in)")
            if profile.get("weight_kg"):
                bits.append(f"Weight: {profile['weight_kg']:.1f} kg ({body_metrics.kg_to_lb(profile['weight_kg']):.0f} lb)")
            if profile.get("sex"):
                bits.append(f"Sex: {profile['sex']}")
            st.write(" · ".join(bits))
            bmi = body_metrics.compute_bmi(profile.get("weight_kg"), profile.get("height_cm"))
            if bmi:
                st.write(f"BMI: **{bmi:.1f}** ({body_metrics.bmi_category(bmi)})")

        if st.button("✏️ Edit Profile"):
            st.session_state.pp_editing = True
            st.rerun()

    if user["auth_provider"] != "guest":
        history = db.get_body_metrics_history(user["id"])
        if len(history) >= 2:
            st.subheader("Weight over time")
            hist_df = pd.DataFrame(history)
            fig = px.line(hist_df, x="recorded_at", y="weight_kg", markers=True, title="Weight (kg) over time")
            st.plotly_chart(fig, use_container_width=True)


def _render_form(user, profile, has_data):
    if has_data:
        if st.button("← Cancel and view summary"):
            st.session_state.pp_editing = False
            st.rerun()

    st.markdown(
        "**📏 Body metrics** (optional — used for BMI tracking and to scale your Fitness "
        "Coach muscle diagram; leave at 0 to skip)"
    )
    st.session_state.setdefault("pp_unit_system", "Metric (cm / kg)")
    unit_system = st.radio(
        "Units", ["Metric (cm / kg)", "Imperial (ft-in / lb)"], horizontal=True, key="pp_unit_system",
    )
    default_height_cm = profile.get("height_cm") or 0.0
    default_weight_kg = profile.get("weight_kg") or 0.0
    default_feet, default_inches = (
        body_metrics.cm_to_ft_in(default_height_cm) if default_height_cm else (0, 0.0)
    )
    default_lb = body_metrics.kg_to_lb(default_weight_kg) if default_weight_kg else 0.0

    with st.form("patient_profile_form"):
        conditions = st.multiselect(
            "Medical conditions",
            options=CONDITIONS,
            default=[c for c in profile["conditions"] if c in CONDITIONS],
            placeholder="Start typing to search — e.g. 'ulc' for Ulcers, Ulcerative Colitis...",
        )
        other_condition = st.text_input(
            "Other condition (if not listed above)",
            value=profile.get("other_condition", ""),
            placeholder="Leave blank if none",
        )
        medications = st.text_area(
            "Current medications",
            value=profile.get("medications", ""),
            placeholder="e.g. Metformin, Lisinopril — one per line or comma-separated. Leave blank if none.",
        )
        supplements = st.text_area(
            "Supplements",
            value=profile.get("supplements", ""),
            placeholder="e.g. Vitamin D, Fish oil — one per line or comma-separated. Leave blank if none.",
        )
        goals = st.multiselect(
            "Goals",
            options=GOALS,
            default=[g for g in profile["goals"] if g in GOALS],
            placeholder="What are you trying to achieve?",
        )

        if unit_system.startswith("Metric"):
            height_cm_input = st.number_input(
                "Height (cm)", min_value=0.0, max_value=300.0, value=float(default_height_cm), step=0.5,
            )
            weight_kg_input = st.number_input(
                "Weight (kg)", min_value=0.0, max_value=400.0, value=float(default_weight_kg), step=0.1,
            )
        else:
            col_ft, col_in = st.columns(2)
            with col_ft:
                feet_input = st.number_input(
                    "Height — feet", min_value=0, max_value=8, value=int(default_feet), step=1,
                )
            with col_in:
                inches_input = st.number_input(
                    "Height — inches", min_value=0.0, max_value=11.9, value=float(round(default_inches, 1)), step=0.5,
                )
            weight_lb_input = st.number_input(
                "Weight (lb)", min_value=0.0, max_value=880.0, value=float(round(default_lb, 1)), step=0.5,
            )

        sex = st.selectbox(
            "Sex",
            options=SEX_OPTIONS,
            index=SEX_OPTIONS.index(profile.get("sex")) if profile.get("sex") in SEX_OPTIONS else 0,
            help="Only used to pick which muscle-figure diagram style shows in Fitness Coach.",
        )

        submitted = st.form_submit_button("Save Profile")

    if submitted:
        if unit_system.startswith("Metric"):
            height_cm = height_cm_input or None
            weight_kg = weight_kg_input or None
        else:
            height_cm = body_metrics.ft_in_to_cm(feet_input, inches_input) or None
            weight_kg = body_metrics.lb_to_kg(weight_lb_input) or None
        sex_value = "" if sex == "Prefer not to say" else sex

        new_profile = {
            "conditions": conditions,
            "other_condition": other_condition.strip(),
            "medications": medications.strip(),
            "supplements": supplements.strip(),
            "goals": goals,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "sex": sex_value,
        }
        if user["auth_provider"] == "guest":
            st.session_state.guest_patient_profile = new_profile
        else:
            db.set_patient_profile(
                user["id"], conditions, other_condition.strip(),
                medications.strip(), supplements.strip(), goals,
                height_cm=height_cm, weight_kg=weight_kg, sex=sex_value,
            )
            if height_cm and weight_kg:
                bmi = body_metrics.compute_bmi(weight_kg, height_cm)
                db.add_body_metrics_entry(user["id"], date.today().isoformat(), height_cm, weight_kg, bmi)
        st.session_state.pp_editing = False
        st.session_state.pp_just_saved = True
        st.rerun()


def render(user):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("📋 Patient Profile")
        st.caption(f"Signed in as **{user['email']}**" + (" (guest session)" if user["auth_provider"] == "guest" else ""))
    with top_right:
        if st.button("← Back to Services"):
            st.session_state.current_service = None
            st.rerun()

    st.markdown(
        "A general health screening. Nothing here is required — but the more you share, "
        "the more personalized every other service (Bloodwork Analysis, Fitness Coach, "
        "Conditions Tracker, and Plate Score) can be for you."
    )
    st.caption(
        "This is not medical advice and isn't a substitute for a medical history taken by a "
        "clinician. Select **None** or **Prefer not to say** for anything you'd rather skip."
    )

    profile = get_profile(user)
    has_data = _has_data(profile)
    st.session_state.setdefault("pp_editing", not has_data)
    st.session_state.setdefault("pp_just_saved", False)

    _save_notice()

    if has_data and not st.session_state.pp_editing:
        _render_summary(user, profile)
    else:
        _render_form(user, profile, has_data)
