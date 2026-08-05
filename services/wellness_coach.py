"""Wellness Coach service: diet + exercise guidance, personalized with the
user's latest Bloodwork Analysis results when available, otherwise based on
a short questionnaire.
"""

import streamlit as st

import ai_wellness
import db
import reference_ranges as rr
from services import patient_profile, uc_tracker


def _latest_entry(user):
    if user["auth_provider"] == "guest":
        entries = st.session_state.get("guest_entries", [])
    else:
        entries = db.get_entries_for_user(user["id"])
    if not entries:
        return None
    return max(entries, key=lambda e: e["entry_date"])


def _summarize_entry(entry, thresholds):
    summary_lines = []
    needs_clearance = False
    sex = entry.get("sex", "Female")

    for key, (name, unit, flag_fn, needs_sex) in rr.METRICS.items():
        value = entry.get(key)
        if value is None:
            continue
        flag = flag_fn(value, sex, thresholds) if needs_sex else flag_fn(value, thresholds)
        summary_lines.append(f"- {name}: {value} {unit} -> {flag.label} ({flag.status})")
        if flag.status == "consult_doctor":
            needs_clearance = True

    systolic, diastolic = entry.get("systolic"), entry.get("diastolic")
    if systolic is not None and diastolic is not None:
        bp_flag = rr.flag_blood_pressure(systolic, diastolic, thresholds)
        summary_lines.append(f"- Blood Pressure: {systolic:.0f}/{diastolic:.0f} mmHg -> {bp_flag.label} ({bp_flag.status})")
        if bp_flag.status == "consult_doctor":
            needs_clearance = True

    return summary_lines, needs_clearance


def render(user, thresholds):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("🥗 Wellness Coach")
        st.caption(f"Signed in as **{user['email']}**" + (" (guest session)" if user["auth_provider"] == "guest" else ""))
    with top_right:
        if st.button("← Back to Services"):
            st.session_state.current_service = None
            st.rerun()

    st.markdown(
        "Get a personalized diet and exercise plan. **To use this service:** answer the "
        "short questionnaire below and click **Generate Plan** — it's automatically "
        "personalized further using your latest Bloodwork Analysis results, your Patient "
        "Profile, and your UC Tracker history, whenever any of those are on file."
    )
    st.warning(
        "**Not medical or nutritional advice.** This tool offers general wellness "
        "suggestions only. Always consult a healthcare provider before starting a new "
        "diet or exercise program."
    )

    entry = _latest_entry(user)
    bloodwork_summary, needs_clearance = ([], False)
    if entry:
        bloodwork_summary, needs_clearance = _summarize_entry(entry, thresholds)
        st.info(f"Using your most recent Bloodwork Analysis entry from **{entry['entry_date']}** to personalize this plan.")
        with st.expander("View bloodwork used"):
            for line in bloodwork_summary:
                st.markdown(line)
        if needs_clearance:
            st.error(
                "⚠️ One or more of your bloodwork results need medical attention. "
                "Get clearance from a doctor before starting a new exercise program — "
                "any exercise suggestions below will be kept conservative until then."
            )
    else:
        st.caption(
            "No Bloodwork Analysis entry on file yet — this plan will be based on your "
            "answers below only. Log bloodwork in Bloodwork Analysis for a more personalized plan."
        )

    uc_summary = uc_tracker.get_recent_summary(user)
    if uc_summary:
        st.info(f"Also factoring in your UC Tracker data: {uc_summary}")

    health_profile = patient_profile.get_profile(user)
    profile_summary = patient_profile.summary_line(health_profile)
    if profile_summary:
        st.caption(f"📋 Personalizing using your Patient Profile: {profile_summary}")
    else:
        st.caption("📋 No Patient Profile on file — fill one in for a more personalized plan.")

    st.subheader("Tell us about your goals")
    with st.form("wellness_questionnaire"):
        goal = st.selectbox(
            "Primary goal",
            ["Weight loss", "Weight maintenance", "Muscle gain", "General health improvement"],
        )
        activity_level = st.selectbox(
            "Current activity level",
            ["Sedentary", "Light", "Moderate", "Active", "Very active"],
        )
        dietary_restrictions = st.multiselect(
            "Dietary restrictions",
            ["None", "Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "Halal", "Kosher", "Other"],
            default=["None"],
        )
        notes = st.text_area("Anything else we should know? (optional)")
        submitted = st.form_submit_button("Generate Plan")

    if submitted:
        questionnaire = {
            "Primary goal": goal,
            "Current activity level": activity_level,
            "Dietary restrictions": ", ".join(dietary_restrictions),
            "Additional notes": notes,
        }
        profile = {"age": user.get("age"), "country": user.get("country")}

        st.subheader("Your plan")
        if needs_clearance:
            st.error("⚠️ Remember: get medical clearance before starting any new exercise program.")

        if not ai_wellness.is_configured():
            st.info(
                "Set `GEMINI_API_KEY` in a `.env` file to enable AI-generated plans "
                "(see README)."
            )
        else:
            with st.spinner("Generating your plan..."):
                plan = ai_wellness.get_plan(profile, bloodwork_summary, needs_clearance, questionnaire, uc_summary, health_profile)
            st.markdown(plan)
        st.caption(ai_wellness.DISCLAIMER)
