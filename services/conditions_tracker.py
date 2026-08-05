"""Conditions Tracker service: pick which condition(s) to actively monitor
(same fuzzy-search pattern as Patient Profile), log symptoms on a visual
calendar — click any day to log or edit that day's entry, and logged days
show directly on the calendar so past history is visible at a glance — and
get an AI trend summary (improving/worsening/stable) plus likely triggers.
"""

from collections import defaultdict
from datetime import date

import pandas as pd
import streamlit as st
from streamlit_calendar import calendar

import ai_conditions
import db
from services import patient_profile

SEVERITIES = ["Mild", "Moderate", "Severe"]

SEVERITY_COLORS = {
    None: "#2dd4bf",
    "Mild": "#eab308",
    "Moderate": "#f97316",
    "Severe": "#ef4444",
}


def _get_tracked(user):
    if user["auth_provider"] == "guest":
        st.session_state.setdefault("guest_tracked_conditions", dict(db.EMPTY_TRACKED_CONDITIONS))
        return st.session_state.guest_tracked_conditions
    return db.get_tracked_conditions(user["id"])


def _save_tracked(user, conditions, other_condition):
    if user["auth_provider"] == "guest":
        st.session_state.guest_tracked_conditions = {"conditions": conditions, "other_condition": other_condition}
    else:
        db.set_tracked_conditions(user["id"], conditions, other_condition)


def _get_entries(user, condition):
    if user["auth_provider"] == "guest":
        st.session_state.setdefault("guest_condition_entries", {})
        return st.session_state.guest_condition_entries.get(condition, [])
    return db.get_condition_entries(user["id"], condition)


def _add_entry(user, condition, entry_date_str, symptom_occurred, severity, triggers, notes):
    if user["auth_provider"] == "guest":
        st.session_state.setdefault("guest_condition_entries", {})
        st.session_state.guest_condition_entries.setdefault(condition, [])
        st.session_state.guest_condition_entries[condition].append(
            {
                "id": None, "entry_date": entry_date_str, "symptom_occurred": int(symptom_occurred),
                "severity": severity, "triggers": triggers, "notes": notes,
            }
        )
    else:
        db.add_condition_entry(user["id"], condition, entry_date_str, symptom_occurred, severity, triggers, notes)


def _update_entry(user, condition, entry_id, entry_date_str, symptom_occurred, severity, triggers, notes):
    if user["auth_provider"] == "guest":
        for e in st.session_state.guest_condition_entries.get(condition, []):
            if e["entry_date"] == entry_date_str:
                e.update({"symptom_occurred": int(symptom_occurred), "severity": severity, "triggers": triggers, "notes": notes})
    else:
        db.update_condition_entry(entry_id, symptom_occurred, severity, triggers, notes)


def _parse_triggers(raw_text):
    parts = [p.strip() for chunk in (raw_text or "").split("\n") for p in chunk.split(",")]
    return [p for p in parts if p]


def _trigger_stats(entries):
    per_trigger = defaultdict(lambda: {"times_occurred": 0, "times_with_symptom": 0})
    total_symptom_days = 0
    for entry in entries:
        triggers = _parse_triggers(entry.get("triggers"))
        occurred = bool(entry["symptom_occurred"])
        if occurred:
            total_symptom_days += 1
        for trigger in triggers:
            key = trigger.lower()
            per_trigger[key]["times_occurred"] += 1
            per_trigger[key]["label"] = trigger
            if occurred:
                per_trigger[key]["times_with_symptom"] += 1

    for stats in per_trigger.values():
        stats["symptom_rate"] = stats["times_with_symptom"] / stats["times_occurred"] if stats["times_occurred"] else 0

    overall_rate = total_symptom_days / len(entries) if entries else 0
    candidates = [(s["label"], s) for s in per_trigger.values() if s["times_occurred"] >= 2]
    candidates.sort(key=lambda item: item[1]["symptom_rate"], reverse=True)
    return candidates, overall_rate


def _extract_clicked_date(result):
    """Defensive extraction: streamlit-calendar's dateClick/eventClick payload
    shape isn't fully documented, so this tries every plausible key."""
    if not result:
        return None
    for callback_key in ("dateClick", "eventClick"):
        if result.get("callback") == callback_key:
            info = result.get(callback_key, {})
            if callback_key == "eventClick":
                info = info.get("event", info)
            date_str = info.get("dateStr") or info.get("date") or info.get("start")
            if date_str:
                return str(date_str)[:10]
    return None


def get_recent_summary(user, max_triggers=3):
    """Short text summary of recent symptom rate + likely triggers across all
    tracked conditions, for other services (e.g. Wellness Coach) to factor
    in. Returns None if there's no data yet.
    """
    tracked = _get_tracked(user)
    all_conditions = list(tracked["conditions"])
    if tracked.get("other_condition"):
        all_conditions.append(tracked["other_condition"])
    if not all_conditions:
        return None

    lines = []
    for condition in all_conditions:
        entries = _get_entries(user, condition)
        if not entries:
            continue
        stats, overall_rate = _trigger_stats(entries)
        top = [f"{t} ({s['symptom_rate']:.0%})" for t, s in stats[:max_triggers]]
        line = f"{condition}: {len(entries)} day(s) logged, {overall_rate:.0%} symptom rate"
        if top:
            line += f", possible triggers: {', '.join(top)}"
        lines.append(line)
    return "; ".join(lines) if lines else None


def render(user):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("📅 Conditions Tracker")
        st.caption(f"Signed in as **{user['email']}**" + (" (guest session)" if user["auth_provider"] == "guest" else ""))
    with top_right:
        if st.button("← Back to Services"):
            st.session_state.current_service = None
            st.rerun()

    st.markdown(
        "Track any condition on a calendar. **To use this service:** pick which "
        "condition(s) you want to monitor below, then click any day on the calendar "
        "to log symptoms for that day — logged days show up right on the calendar so "
        "you can look back and see your history at a glance."
    )
    st.warning(
        "**Not medical advice.** This tool helps you spot patterns in your own logged "
        "data. It cannot diagnose triggers or confirm causation — always discuss "
        "suspected triggers with your doctor."
    )

    tracked = _get_tracked(user)
    has_tracked = bool(tracked["conditions"] or tracked.get("other_condition"))
    st.session_state.setdefault("ct_editing_tracked", not has_tracked)

    if has_tracked and not st.session_state.ct_editing_tracked:
        all_conditions = list(tracked["conditions"])
        if tracked.get("other_condition"):
            all_conditions.append(tracked["other_condition"])
        st.caption("📋 Tracking: " + ", ".join(all_conditions))
        if st.button("✏️ Edit tracked conditions"):
            st.session_state.ct_editing_tracked = True
            st.rerun()
    else:
        st.subheader("Which condition(s) do you want to track?")
        profile = patient_profile.get_profile(user)
        default_conditions = [c for c in profile["conditions"] if c in patient_profile.CONDITIONS]
        with st.form("tracked_conditions_form"):
            conditions = st.multiselect(
                "Conditions", options=patient_profile.CONDITIONS, default=default_conditions,
                placeholder="Start typing to search — e.g. 'ulc' for Ulcers, Ulcerative Colitis...",
            )
            other_condition = st.text_input(
                "Other condition (if not listed above)", value=tracked.get("other_condition", "")
            )
            submitted = st.form_submit_button("Save")
        if submitted:
            _save_tracked(user, conditions, other_condition.strip())
            st.session_state.ct_editing_tracked = False
            st.rerun()
        return

    all_conditions = list(tracked["conditions"])
    if tracked.get("other_condition"):
        all_conditions.append(tracked["other_condition"])
    condition = st.selectbox("Viewing", all_conditions) if len(all_conditions) > 1 else all_conditions[0]

    entries = _get_entries(user, condition)
    entries_by_date = {e["entry_date"]: e for e in entries}

    events = []
    for entry_date_str, entry in entries_by_date.items():
        occurred = bool(entry["symptom_occurred"])
        severity = entry.get("severity") if occurred else None
        events.append(
            {
                "start": entry_date_str,
                "title": severity if occurred else "✓ No symptoms",
                "color": SEVERITY_COLORS.get(severity, SEVERITY_COLORS[None]),
            }
        )

    calendar_options = {
        "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""},
        "initialView": "dayGridMonth",
        "height": 500,
    }
    # Key includes the entry count so the component remounts (and visibly
    # refreshes) whenever a new day is logged - streamlit-calendar's exact
    # behavior on prop changes with a stable key isn't documented, so this
    # forces a guaranteed refresh rather than risk a stale calendar.
    result = calendar(
        events=events, options=calendar_options,
        callbacks=["dateClick", "eventClick"], key=f"calendar_{condition}_{len(entries)}",
    )

    clicked = _extract_clicked_date(result)
    if clicked:
        st.session_state.ct_selected_date = clicked
    selected_date = st.session_state.get("ct_selected_date", date.today().isoformat())

    existing = entries_by_date.get(selected_date)

    st.subheader(f"Log entry for {selected_date}")
    with st.form(f"entry_form_{condition}_{selected_date}"):
        symptom_occurred = st.checkbox(
            "Symptom occurred today?",
            value=bool(existing["symptom_occurred"]) if existing else False,
            key=f"occurred_{condition}_{selected_date}",
        )
        severity_index = SEVERITIES.index(existing["severity"]) if existing and existing.get("severity") in SEVERITIES else 0
        severity = st.selectbox(
            "Severity (if occurred)", SEVERITIES, index=severity_index, key=f"severity_{condition}_{selected_date}",
        )
        triggers = st.text_area(
            "Possible triggers (foods, stress, weather, etc.)",
            value=existing.get("triggers", "") if existing else "",
            height=80, key=f"triggers_{condition}_{selected_date}",
        )
        notes = st.text_input(
            "Notes (optional)", value=existing.get("notes", "") if existing else "", key=f"notes_{condition}_{selected_date}",
        )
        submitted = st.form_submit_button("Save Entry")

    if submitted:
        final_severity = severity if symptom_occurred else None
        if existing:
            _update_entry(user, condition, existing.get("id"), selected_date, symptom_occurred, final_severity, triggers, notes)
        else:
            _add_entry(user, condition, selected_date, symptom_occurred, final_severity, triggers, notes)
        st.success("Entry saved.")
        st.rerun()

    st.divider()
    st.subheader("History & Patterns")
    if not entries:
        st.caption("No entries yet — click a day on the calendar above to log your first entry.")
        return

    stats, overall_rate = _trigger_stats(entries)
    st.caption(f"Overall symptom rate across logged days: **{overall_rate:.0%}**")

    if stats:
        stats_df = pd.DataFrame(
            [
                {
                    "Trigger": t,
                    "Times occurred": s["times_occurred"],
                    "Times with symptom": s["times_with_symptom"],
                    "Symptom rate": f"{s['symptom_rate']:.0%}",
                }
                for t, s in stats
            ]
        )
        st.dataframe(stats_df, use_container_width=True)
    else:
        st.caption("Log a few more days with repeated triggers to see a trigger table here.")

    if st.button("Analyze My Patterns"):
        with st.spinner("Analyzing..."):
            summary = ai_conditions.get_pattern_summary(condition, stats, overall_rate, entries, patient_profile.get_profile(user))
        st.markdown(summary)
        st.caption(ai_conditions.DISCLAIMER)
