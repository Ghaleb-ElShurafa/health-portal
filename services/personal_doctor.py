"""Personal Doctor service: bloodwork entry, rule-based flagging, AI summary,
and trend charts."""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

import db
import reference_ranges as rr
from ai_advice import DISCLAIMER, get_advice, is_configured


def render(user, thresholds):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("🩺 Personal Doctor")
        st.caption(f"Signed in as **{user['email']}**" + (" (guest session)" if user["auth_provider"] == "guest" else ""))
    with top_right:
        if st.button("← Back to Services"):
            st.session_state.current_service = None
            st.rerun()

    st.warning(
        "**Not medical advice.** This tool provides general educational information only "
        "and cannot diagnose or treat any condition. Always consult a healthcare provider "
        "about your results, especially anything flagged below."
    )

    st.markdown(
        "Enter your bloodwork results below to get a plain-language summary, general "
        "diet/lifestyle pointers, and a flag for anything that should be discussed with "
        "a doctor. Leave any field blank if you don't have that result."
    )

    with st.form("entry_form"):
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("Test date", value=date.today())
        with col2:
            sex = st.selectbox("Sex", ["Female", "Male"])

        st.subheader("Lipid panel")
        c1, c2, c3 = st.columns(3)
        total_cholesterol = c1.number_input("Total Cholesterol (mg/dL)", min_value=0.0, value=None, step=1.0)
        ldl = c2.number_input("LDL (mg/dL)", min_value=0.0, value=None, step=1.0)
        hdl = c3.number_input("HDL (mg/dL)", min_value=0.0, value=None, step=1.0)
        triglycerides = st.number_input("Triglycerides (mg/dL)", min_value=0.0, value=None, step=1.0)

        st.subheader("Glucose")
        c4, c5 = st.columns(2)
        glucose_fasting = c4.number_input("Fasting Glucose (mg/dL)", min_value=0.0, value=None, step=1.0)
        hba1c = c5.number_input("HbA1c (%)", min_value=0.0, value=None, step=0.1, format="%.1f")

        st.subheader("Blood pressure")
        c6, c7 = st.columns(2)
        systolic = c6.number_input("Systolic (mmHg)", min_value=0.0, value=None, step=1.0)
        diastolic = c7.number_input("Diastolic (mmHg)", min_value=0.0, value=None, step=1.0)

        submitted = st.form_submit_button("Analyze")

    if submitted:
        raw_values = {
            "total_cholesterol": total_cholesterol,
            "ldl": ldl,
            "hdl": hdl,
            "triglycerides": triglycerides,
            "glucose_fasting": glucose_fasting,
            "hba1c": hba1c,
            "systolic": systolic,
            "diastolic": diastolic,
        }
        provided = {k: v for k, v in raw_values.items() if v is not None}

        if not provided:
            st.error("Enter at least one value before analyzing.")
        else:
            if user["auth_provider"] == "guest":
                st.session_state.guest_entries.append(
                    {"entry_date": entry_date.isoformat(), "sex": sex, **provided}
                )
            else:
                db.add_entry(user["id"], entry_date.isoformat(), sex, provided)

            results = []
            for key, (name, unit, flag_fn, needs_sex) in rr.METRICS.items():
                if key in provided:
                    flag = flag_fn(provided[key], sex, thresholds) if needs_sex else flag_fn(provided[key], thresholds)
                    results.append((name, unit, provided[key], flag))

            if systolic is not None and diastolic is not None:
                bp_flag = rr.flag_blood_pressure(systolic, diastolic, thresholds)
                results.append(("Blood Pressure", "mmHg", f"{systolic:.0f}/{diastolic:.0f}", bp_flag))

            st.subheader("Results")
            any_consult = any(f.status == "consult_doctor" for _, _, _, f in results)
            if any_consult:
                st.error("⚠️ One or more results should be discussed with a doctor — see details below.")

            for name, unit, value, flag in results:
                display = f"**{name}:** {value} {unit} — {flag.label}"
                if flag.status == "normal":
                    st.success(display)
                elif flag.status == "watch":
                    st.warning(display)
                else:
                    st.error(display)

            st.subheader("AI summary & suggestions")
            if not is_configured():
                st.info(
                    "Set `GEMINI_API_KEY` in a `.env` file to enable AI-generated "
                    "explanations (see README). Showing rule-based results only for now."
                )
            else:
                with st.spinner("Generating summary..."):
                    advice = get_advice(results, sex)
                st.write(advice)
            st.caption(DISCLAIMER)

    st.divider()
    st.subheader("History")
    if user["auth_provider"] == "guest":
        entries = st.session_state.guest_entries
    else:
        entries = db.get_entries_for_user(user["id"])

    if len(entries) < 1:
        st.caption("No entries yet — submit the form above to start tracking trends.")
    else:
        history_df = pd.DataFrame(entries)
        metric_options = [c for c in db.COLUMNS if c in history_df.columns and history_df[c].notna().sum() >= 1]
        if metric_options:
            chosen = st.selectbox("Chart metric", metric_options)
            chart_df = history_df.dropna(subset=[chosen])
            fig = px.line(chart_df, x="entry_date", y=chosen, markers=True, title=f"{chosen} over time")
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(history_df, use_container_width=True)
