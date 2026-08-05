"""Bloodwork Analysis service: upload a bloodwork document for AI-assisted
extraction, rule-based flagging, AI summary, and trend charts across every
bloodwork entry on file over time. Values only ever come from an uploaded
document — there's no standalone manual-entry path — though the extracted
values can still be reviewed and corrected before saving.
"""

from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import ai_advice
import db
import reference_ranges as rr
from ai_advice import DISCLAIMER, get_advice, is_configured
from services import patient_profile


def _parse_extracted_date(value):
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def render(user, thresholds):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("🩺 Bloodwork Analysis")
        st.caption(f"Signed in as **{user['email']}**" + (" (guest session)" if user["auth_provider"] == "guest" else ""))
    with top_right:
        if st.button("← Back to Services"):
            st.session_state.current_service = None
            st.rerun()

    st.markdown(
        "Upload a photo or PDF of a lab report and AI reads the values for you — lipid "
        "panel, glucose/HbA1c, and blood pressure. **To use this service:** upload a lab "
        "report below, click **Extract Values**, review the numbers it found (correcting "
        "anything it misread), then save to get your flagged results and an AI summary."
    )
    st.warning(
        "**Not medical advice.** This tool provides general educational information only "
        "and cannot diagnose or treat any condition. Always consult a healthcare provider "
        "about your results, especially anything flagged below."
    )

    st.session_state.setdefault("bloodwork_form_version", 0)
    st.session_state.setdefault("extracted_bloodwork", {})

    st.subheader("Upload a bloodwork document")
    uploaded_file = st.file_uploader("Lab report (image or PDF)", type=["png", "jpg", "jpeg", "pdf"])
    if uploaded_file is not None and st.button("Extract Values"):
        mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "pdf": "application/pdf"}
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        with st.spinner("Reading document..."):
            extracted, error = ai_advice.extract_from_document(uploaded_file.getvalue(), mime_map.get(ext, "image/png"))
        if error:
            st.warning(error)
        if extracted:
            st.session_state.extracted_bloodwork = extracted
            st.session_state.bloodwork_form_version += 1
            st.success("Values extracted — review and edit below before saving.")
            st.rerun()

    extracted = st.session_state.extracted_bloodwork
    version = st.session_state.bloodwork_form_version

    if not extracted:
        st.divider()
        st.caption("Upload a lab report above and click **Extract Values** to review and save your results.")
    else:
        st.divider()
        st.subheader("Review & Save")
        st.caption("Fields are pre-filled from your uploaded document. Correct anything it misread before saving.")

        with st.form("entry_form"):
            col1, col2 = st.columns(2)
            with col1:
                entry_date = st.date_input(
                    "Test date", value=_parse_extracted_date(extracted.get("test_date")), key=f"date_v{version}"
                )
            with col2:
                sex_options = ["Female", "Male"]
                default_sex = sex_options.index(extracted["sex"]) if extracted.get("sex") in sex_options else 0
                sex = st.selectbox("Sex", sex_options, index=default_sex, key=f"sex_v{version}")

            st.subheader("Lipid panel")
            c1, c2, c3 = st.columns(3)
            total_cholesterol = c1.number_input(
                "Total Cholesterol (mg/dL)", min_value=0.0, value=extracted.get("total_cholesterol"), step=1.0, key=f"tc_v{version}"
            )
            ldl = c2.number_input("LDL (mg/dL)", min_value=0.0, value=extracted.get("ldl"), step=1.0, key=f"ldl_v{version}")
            hdl = c3.number_input("HDL (mg/dL)", min_value=0.0, value=extracted.get("hdl"), step=1.0, key=f"hdl_v{version}")
            triglycerides = st.number_input(
                "Triglycerides (mg/dL)", min_value=0.0, value=extracted.get("triglycerides"), step=1.0, key=f"tg_v{version}"
            )

            st.subheader("Glucose")
            c4, c5 = st.columns(2)
            glucose_fasting = c4.number_input(
                "Fasting Glucose (mg/dL)", min_value=0.0, value=extracted.get("glucose_fasting"), step=1.0, key=f"gf_v{version}"
            )
            hba1c = c5.number_input(
                "HbA1c (%)", min_value=0.0, value=extracted.get("hba1c"), step=0.1, format="%.1f", key=f"hba1c_v{version}"
            )

            st.subheader("Blood pressure")
            c6, c7 = st.columns(2)
            systolic = c6.number_input(
                "Systolic (mmHg)", min_value=0.0, value=extracted.get("systolic"), step=1.0, key=f"sys_v{version}"
            )
            diastolic = c7.number_input(
                "Diastolic (mmHg)", min_value=0.0, value=extracted.get("diastolic"), step=1.0, key=f"dia_v{version}"
            )

            submitted = st.form_submit_button("Save & Analyze")

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
                st.error("No values to save — the document may not have contained any readable results.")
            else:
                if user["auth_provider"] == "guest":
                    st.session_state.guest_entries.append(
                        {"entry_date": entry_date.isoformat(), "sex": sex, **provided}
                    )
                else:
                    db.add_entry(user["id"], entry_date.isoformat(), sex, provided)

                st.session_state.extracted_bloodwork = {}
                st.session_state.bloodwork_form_version += 1

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
                        advice = get_advice(results, sex, patient_profile.get_profile(user))
                    st.write(advice)
                st.caption(DISCLAIMER)

    st.divider()
    st.subheader("History")
    if user["auth_provider"] == "guest":
        entries = st.session_state.guest_entries
    else:
        entries = db.get_entries_for_user(user["id"])

    if len(entries) < 1:
        st.caption("No entries yet — upload a document above to start tracking trends.")
    else:
        history_df = pd.DataFrame(entries)
        metric_options = [c for c in db.COLUMNS if c in history_df.columns and history_df[c].notna().sum() >= 1]
        if metric_options:
            chosen = st.selectbox("Chart metric", metric_options)
            chart_df = history_df.dropna(subset=[chosen])
            fig = px.line(chart_df, x="entry_date", y=chosen, markers=True, title=f"{chosen} over time")
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(history_df, use_container_width=True)
