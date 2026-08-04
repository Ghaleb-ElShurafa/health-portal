"""Patient Profile service: a general health-screening intake — conditions,
medications, supplements, and goals — that personalizes every other service
in the portal (Personal Doctor, Wellness Coach, UC Tracker, Plate Score).
"""

import streamlit as st

import db

NOT_DISCLOSED = ["None", "Prefer not to say"]

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


def _render_summary(profile):
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

        if st.button("✏️ Edit Profile"):
            st.session_state.pp_editing = True
            st.rerun()


def _render_form(user, profile, has_data):
    if has_data:
        if st.button("← Cancel and view summary"):
            st.session_state.pp_editing = False
            st.rerun()

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
        submitted = st.form_submit_button("Save Profile")

    if submitted:
        new_profile = {
            "conditions": conditions,
            "other_condition": other_condition.strip(),
            "medications": medications.strip(),
            "supplements": supplements.strip(),
            "goals": goals,
        }
        if user["auth_provider"] == "guest":
            st.session_state.guest_patient_profile = new_profile
        else:
            db.set_patient_profile(
                user["id"], conditions, other_condition.strip(),
                medications.strip(), supplements.strip(), goals,
            )
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
        "the more personalized every other service (Personal Doctor, Wellness Coach, "
        "UC Tracker, and Plate Score) can be for you."
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
        _render_summary(profile)
    else:
        _render_form(user, profile, has_data)
