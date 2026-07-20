"""UC Tracker service: logs daily flares + foods eaten for users tracking
ulcerative colitis, and analyzes which foods correlate with flare days.
"""

from collections import defaultdict
from datetime import date

import pandas as pd
import streamlit as st

import ai_uc
import db

SEVERITIES = ["Mild", "Moderate", "Severe"]


def _get_entries(user):
    if user["auth_provider"] == "guest":
        return st.session_state.get("guest_uc_entries", [])
    return db.get_uc_entries_for_user(user["id"])


def get_recent_summary(user, max_foods=3):
    """Short text summary of recent flare rate + likely trigger foods, for
    other services (e.g. Wellness Coach) to factor in. Returns None if
    there's no UC Tracker data yet."""
    entries = _get_entries(user)
    if not entries:
        return None

    food_stats, overall_flare_rate = _food_flare_stats(entries)
    lines = [f"{len(entries)} day(s) logged, overall flare rate {overall_flare_rate:.0%}."]
    top = [f"{food} ({s['flare_rate']:.0%} flare rate, {s['times_eaten']}x)" for food, s in food_stats[:max_foods]]
    if top:
        lines.append("Possible trigger foods so far: " + ", ".join(top))
    return " ".join(lines)


def _parse_foods(raw_text):
    # Accepts comma-separated or one-per-line input.
    parts = [p.strip() for chunk in raw_text.split("\n") for p in chunk.split(",")]
    return [p for p in parts if p]


def _food_flare_stats(entries):
    per_food = defaultdict(lambda: {"times_eaten": 0, "times_on_flare": 0})
    total_flare_days = 0

    for entry in entries:
        foods = _parse_foods(entry["foods"])
        flared = bool(entry["flared"])
        if flared:
            total_flare_days += 1
        for food in foods:
            key = food.lower()
            per_food[key]["times_eaten"] += 1
            per_food[key]["label"] = food
            if flared:
                per_food[key]["times_on_flare"] += 1

    for stats in per_food.values():
        stats["flare_rate"] = stats["times_on_flare"] / stats["times_eaten"] if stats["times_eaten"] else 0

    overall_flare_rate = total_flare_days / len(entries) if entries else 0

    # Only foods with enough occurrences to mean anything, sorted by flare rate.
    candidates = [
        (stats["label"], stats) for stats in per_food.values() if stats["times_eaten"] >= 2
    ]
    candidates.sort(key=lambda item: item[1]["flare_rate"], reverse=True)
    return candidates, overall_flare_rate


def render(user):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("🔥 UC Tracker")
        st.caption(f"Signed in as **{user['email']}**" + (" (guest session)" if user["auth_provider"] == "guest" else ""))
    with top_right:
        if st.button("← Back to Services"):
            st.session_state.current_service = None
            st.rerun()

    st.warning(
        "**Not medical advice.** This tool helps you spot patterns in your own logged "
        "data. It cannot diagnose triggers or confirm causation — always discuss "
        "suspected trigger foods with your gastroenterologist."
    )

    st.markdown("Log each day's flare status and the foods you ate, to help spot patterns over time.")

    with st.form("uc_entry_form"):
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("Date", value=date.today())
        with col2:
            flared = st.checkbox("Flare today?")

        severity = st.selectbox("Severity (if flared)", SEVERITIES, index=0)
        foods = st.text_area("Foods eaten today (one per line, or comma-separated)", height=100)
        notes = st.text_input("Notes (optional)")

        submitted = st.form_submit_button("Log Entry")

    if submitted:
        if not foods.strip():
            st.error("Enter at least one food before logging.")
        else:
            if user["auth_provider"] == "guest":
                st.session_state.setdefault("guest_uc_entries", [])
                st.session_state.guest_uc_entries.append(
                    {
                        "entry_date": entry_date.isoformat(),
                        "flared": int(flared),
                        "severity": severity if flared else None,
                        "foods": foods,
                        "notes": notes,
                    }
                )
            else:
                db.add_uc_entry(
                    user["id"],
                    entry_date.isoformat(),
                    flared,
                    severity if flared else None,
                    foods,
                    notes,
                )
            st.success("Entry logged.")

    st.divider()
    st.subheader("History & Patterns")
    entries = _get_entries(user)

    if not entries:
        st.caption("No entries yet — log a few days to start seeing patterns.")
        return

    history_df = pd.DataFrame(entries)[["entry_date", "flared", "severity", "foods", "notes"]]
    history_df["flared"] = history_df["flared"].astype(bool)
    st.dataframe(history_df.sort_values("entry_date", ascending=False), use_container_width=True)

    food_stats, overall_flare_rate = _food_flare_stats(entries)
    st.caption(f"Overall flare rate across logged days: **{overall_flare_rate:.0%}**")

    if food_stats:
        stats_df = pd.DataFrame(
            [
                {
                    "Food": food,
                    "Times eaten": s["times_eaten"],
                    "Times on a flare day": s["times_on_flare"],
                    "Flare rate": f"{s['flare_rate']:.0%}",
                }
                for food, s in food_stats
            ]
        )
        st.dataframe(stats_df, use_container_width=True)

        if st.button("Analyze My Patterns"):
            with st.spinner("Analyzing..."):
                summary = ai_uc.get_pattern_summary(food_stats, overall_flare_rate, len(entries))
            st.markdown(summary)
            st.caption(ai_uc.DISCLAIMER)
    else:
        st.caption("Log a few more days with repeated foods to unlock pattern analysis.")
