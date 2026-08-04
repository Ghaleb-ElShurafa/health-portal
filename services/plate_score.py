"""Plate Score service: photograph or upload a photo of a meal, get an
AI-estimated calorie/macro breakdown and a personalized health score —
weighted by the user's Patient Profile (conditions, medications,
supplements, goals) when set.
"""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

import ai_food
import db
from ai_food import DISCLAIMER
from services import patient_profile


def _get_entries(user):
    if user["auth_provider"] == "guest":
        return st.session_state.get("guest_meal_entries", [])
    return db.get_meal_entries_for_user(user["id"])


def _score_badge(score):
    if score >= 7:
        return st.success
    if score >= 4:
        return st.warning
    return st.error


def render(user):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("🍽️ Plate Score")
        st.caption(f"Signed in as **{user['email']}**" + (" (guest session)" if user["auth_provider"] == "guest" else ""))
    with top_right:
        if st.button("← Back to Services"):
            st.session_state.current_service = None
            st.rerun()

    st.warning(
        "**Not medical or nutritional advice.** Calorie and nutrient estimates from a photo "
        "are approximate. Always consult a doctor or registered dietitian for a diet plan "
        "tailored to a specific health condition."
    )

    health_profile = patient_profile.get_profile(user)
    profile_summary = patient_profile.summary_line(health_profile)
    if profile_summary:
        st.caption(f"📋 Personalizing scores using your Patient Profile: {profile_summary}")
    else:
        st.caption("📋 No Patient Profile on file — fill one in for a more personalized score.")

    st.subheader("Log a meal")
    tab_camera, tab_upload = st.tabs(["📷 Take Photo", "📁 Upload Photo"])
    with tab_camera:
        camera_photo = st.camera_input("Take a photo of your meal", label_visibility="collapsed")
        st.caption("Camera not working, no camera on this device, or on a computer? Use the **📁 Upload Photo** tab instead.")
    with tab_upload:
        uploaded_photo = st.file_uploader("Upload a photo of your meal", type=["png", "jpg", "jpeg"], label_visibility="collapsed")

    photo = camera_photo or uploaded_photo
    if photo is not None and st.button("Analyze Meal", type="primary"):
        with st.spinner("Analyzing your meal..."):
            result, error = ai_food.analyze_meal_photo(photo.getvalue(), photo.type, health_profile)

        if error:
            st.error(error)
        else:
            entry_date = date.today().isoformat()
            if user["auth_provider"] == "guest":
                st.session_state.setdefault("guest_meal_entries", [])
                st.session_state.guest_meal_entries.append({"entry_date": entry_date, **result})
            else:
                db.add_meal_entry(
                    user["id"], entry_date, result["food_items"], result["estimated_calories"],
                    result["protein_g"], result["carbs_g"], result["fat_g"],
                    result["health_score"], result["assessment"],
                )

            st.subheader("Results")
            st.markdown(f"**Identified:** {result['food_items']}")
            score_fn = _score_badge(result["health_score"])
            score_fn(f"**Health Score: {result['health_score']:.0f}/10**")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Calories", f"{result['estimated_calories']:.0f}")
            c2.metric("Protein", f"{result['protein_g']:.0f}g")
            c3.metric("Carbs", f"{result['carbs_g']:.0f}g")
            c4.metric("Fat", f"{result['fat_g']:.0f}g")

            st.write(result["assessment"])
            st.caption(DISCLAIMER)

    st.divider()
    st.subheader("History")
    entries = _get_entries(user)

    if not entries:
        st.caption("No meals logged yet — take or upload a photo above to start tracking.")
        return

    history_df = pd.DataFrame(entries)
    today = date.today().isoformat()
    today_calories = history_df[history_df["entry_date"] == today]["estimated_calories"].sum()
    st.metric("Today's calories logged", f"{today_calories:.0f}")

    fig = px.line(history_df, x="entry_date", y="estimated_calories", markers=True, title="Calories over time")
    st.plotly_chart(fig, use_container_width=True)

    display_df = history_df[["entry_date", "food_items", "estimated_calories", "protein_g", "carbs_g", "fat_g", "health_score"]]
    st.dataframe(display_df.sort_values("entry_date", ascending=False), use_container_width=True)
