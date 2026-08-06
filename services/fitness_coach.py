"""Fitness Coach service: an optional AI-suggested diet + exercise plan, or a
manual routine you build yourself from a curated exercise library (filtered
by home/gym facility), with a daily checklist, computed calories burned and
muscle groups worked, an interactive muscle-figure diagram, and a calories
in vs out comparison against Plate Score.
"""

from collections import defaultdict
from datetime import date, timedelta

import streamlit as st

import ai_fitness
import body_metrics
import db
import exercise_library
import muscle_diagram
import reference_ranges as rr
from services import conditions_tracker, patient_profile, plate_score

RECENT_COLOR = "#2dd4bf"
STALE_COLOR = "#eab308"


def _get_settings(user):
    if user["auth_provider"] == "guest":
        st.session_state.setdefault("guest_fitness_settings", dict(db.EMPTY_FITNESS_SETTINGS))
        return st.session_state.guest_fitness_settings
    return db.get_fitness_settings(user["id"])


def _save_settings(user, facility, days_per_week):
    if user["auth_provider"] == "guest":
        st.session_state.guest_fitness_settings = {"facility": facility, "days_per_week": days_per_week}
    else:
        db.set_fitness_settings(user["id"], facility, days_per_week)


def _get_log(user):
    if user["auth_provider"] == "guest":
        st.session_state.setdefault("guest_workout_log", [])
        return st.session_state.guest_workout_log
    return db.get_workout_log(user["id"])


def _add_log_entry(user, log_date, exercise_name, muscle_group, duration_min, intensity, calories, completed):
    if user["auth_provider"] == "guest":
        st.session_state.setdefault("guest_workout_log", [])
        st.session_state.setdefault("guest_workout_log_next_id", 1)
        entry_id = st.session_state.guest_workout_log_next_id
        st.session_state.guest_workout_log_next_id += 1
        st.session_state.guest_workout_log.append({
            "id": entry_id, "log_date": log_date, "exercise_name": exercise_name,
            "muscle_group": muscle_group, "duration_min": duration_min, "intensity": intensity,
            "calories_burned": calories, "completed": int(completed),
        })
    else:
        db.add_workout_log_entry(
            user["id"], log_date, exercise_name, muscle_group, duration_min, intensity, calories, completed,
        )


def _update_log_entry(user, entry_id, duration_min, intensity, calories, completed):
    if user["auth_provider"] == "guest":
        for e in st.session_state.guest_workout_log:
            if e["id"] == entry_id:
                e.update({
                    "duration_min": duration_min, "intensity": intensity,
                    "calories_burned": calories, "completed": int(completed),
                })
    else:
        db.update_workout_log_entry(entry_id, duration_min, intensity, calories, completed)


def _delete_log_entry(user, entry_id):
    if user["auth_provider"] == "guest":
        st.session_state.guest_workout_log = [e for e in st.session_state.guest_workout_log if e["id"] != entry_id]
    else:
        db.delete_workout_log_entry(entry_id)


def _muscle_highlight_colors(log):
    today = date.today()
    last_worked = {}
    for entry in log:
        if not entry.get("completed"):
            continue
        try:
            d = date.fromisoformat(entry["log_date"])
        except (ValueError, TypeError):
            continue
        group = entry["muscle_group"]
        if group not in last_worked or d > last_worked[group]:
            last_worked[group] = d

    highlighted = {}
    posterior_status = []
    for group, last_date in last_worked.items():
        days_ago = (today - last_date).days
        if days_ago <= 3:
            color, label = RECENT_COLOR, "Worked in the last 3 days"
        elif days_ago <= 7:
            color, label = STALE_COLOR, "Worked in the last 7 days"
        else:
            continue
        if group in muscle_diagram.FRONT_VISIBLE_GROUPS:
            highlighted[group] = color
        else:
            posterior_status.append((group, label))
    return highlighted, posterior_status


def _week_stats(log):
    today = date.today()
    week_ago = today - timedelta(days=7)
    days_worked = set()
    muscle_counts = defaultdict(int)
    total_burned = 0.0
    for entry in log:
        if not entry.get("completed"):
            continue
        try:
            d = date.fromisoformat(entry["log_date"])
        except (ValueError, TypeError):
            continue
        if d < week_ago or d > today:
            continue
        days_worked.add(entry["log_date"])
        muscle_counts[entry["muscle_group"]] += 1
        total_burned += entry.get("calories_burned") or 0
    sorted_counts = sorted(muscle_counts.items(), key=lambda item: -item[1])
    return len(days_worked), sorted_counts, total_burned


def _calories_in_for_date(user, date_str):
    entries = plate_score.get_entries(user)
    return sum(e.get("calories") or 0 for e in entries if e.get("entry_date") == date_str)


def _calories_in_for_week(user):
    today = date.today()
    week_ago = today - timedelta(days=7)
    total = 0.0
    for e in plate_score.get_entries(user):
        try:
            d = date.fromisoformat(e["entry_date"])
        except (ValueError, TypeError, KeyError):
            continue
        if week_ago <= d <= today:
            total += e.get("calories") or 0
    return total


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


def _render_muscle_diagram(user, profile, log):
    st.subheader("Muscle activity")
    bmi = body_metrics.compute_bmi(profile.get("weight_kg"), profile.get("height_cm"))
    bmi_category = body_metrics.bmi_category(bmi)
    sex = profile.get("sex") if profile.get("sex") in ("Male", "Female") else "Male"
    highlighted, posterior_status = _muscle_highlight_colors(log)
    svg = muscle_diagram.build_svg(sex=sex, bmi_category=bmi_category, highlighted=highlighted)

    col_svg, col_legend = st.columns([1, 1])
    with col_svg:
        st.markdown(svg, unsafe_allow_html=True)
    with col_legend:
        st.caption("🟢 Worked in the last 3 days · 🟡 Worked in the last 7 days · Gray = not recently worked")
        if posterior_status:
            st.markdown("**Also worked (not shown on this front-view figure):**")
            for group, label in posterior_status:
                st.markdown(f"- {group}: {label}")
        if not (profile.get("height_cm") and profile.get("weight_kg")):
            st.caption(
                "Add your height, weight, and sex in Patient Profile to personalize this "
                "figure's build — showing a neutral default for now."
            )


def _render_add_exercise(user, profile, settings):
    st.subheader("Add an exercise")
    col1, col2 = st.columns(2)
    with col1:
        muscle_group = st.selectbox("Muscle group", exercise_library.MUSCLE_GROUPS, key="fc_muscle_group")
    with col2:
        facility = settings.get("facility", "Both")
        options = exercise_library.exercises_for(muscle_group, facility)
        exercise_name = st.selectbox(
            "Exercise",
            [e["name"] for e in options] if options else ["No exercises available for this facility"],
            key="fc_exercise_name",
        )

    if not options:
        return

    ex = exercise_library.find_exercise(exercise_name)
    st.caption(ex["instructions"])
    st.markdown(f"[▶ Watch a demo]({exercise_library.video_search_url(exercise_name)})")

    with st.form("fc_add_exercise_form"):
        log_date = st.date_input("Date", value=date.today())
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=10)
        intensity = st.selectbox("Intensity", list(exercise_library.INTENSITY_MULTIPLIERS.keys()), index=1)
        completed = st.checkbox("Mark as completed", value=True)
        submitted = st.form_submit_button("Add to log")

    if submitted:
        weight_kg = profile.get("weight_kg") or 70.0
        calories = exercise_library.estimate_calories(exercise_name, duration, intensity, weight_kg)
        _add_log_entry(user, log_date.isoformat(), exercise_name, muscle_group, duration, intensity, calories, completed)
        if not profile.get("weight_kg"):
            st.caption("Used a default 70 kg estimate since no weight is on file — add yours in Patient Profile for accuracy.")
        st.rerun()


def _render_checklist(user, log):
    st.subheader("Your checklist")
    if not log:
        st.caption("No exercises logged yet — add one above.")
        return

    today = date.today().isoformat()
    by_date = defaultdict(list)
    for entry in log:
        by_date[entry["log_date"]].append(entry)

    for log_date_str in sorted(by_date.keys(), reverse=True)[:14]:
        entries = by_date[log_date_str]
        done_count = sum(1 for e in entries if e["completed"])
        with st.expander(f"{log_date_str} ({done_count}/{len(entries)} done)", expanded=(log_date_str == today)):
            for entry in entries:
                cols = st.columns([4, 2, 2, 1])
                with cols[0]:
                    done = st.checkbox(
                        f"{entry['exercise_name']} ({entry['muscle_group']})",
                        value=bool(entry["completed"]), key=f"fc_done_{entry['id']}",
                    )
                with cols[1]:
                    st.caption(f"{entry['duration_min']:.0f} min · {entry['intensity']}")
                with cols[2]:
                    st.caption(f"{entry['calories_burned']:.0f} kcal")
                with cols[3]:
                    if st.button("🗑️", key=f"fc_del_{entry['id']}", help="Remove"):
                        _delete_log_entry(user, entry["id"])
                        st.rerun()
                if done != bool(entry["completed"]):
                    _update_log_entry(user, entry["id"], entry["duration_min"], entry["intensity"], entry["calories_burned"], done)
                    st.rerun()


def _render_weekly_summary(user, profile, settings, log):
    st.subheader("This week")
    days_worked, muscle_counts, total_burned = _week_stats(log)
    today = date.today().isoformat()
    calories_in_today = _calories_in_for_date(user, today)
    calories_out_today = sum(
        e.get("calories_burned") or 0 for e in log if e["log_date"] == today and e["completed"]
    )

    col_a, col_b, col_c = st.columns(3)
    days_goal = settings.get("days_per_week")
    col_a.metric("Days worked out", f"{days_worked}" + (f" / {days_goal}" if days_goal else ""))
    col_b.metric("Calories burned (7d)", f"{total_burned:.0f}")
    if calories_in_today or calories_out_today:
        col_c.metric("Today: in vs out", f"{calories_in_today:.0f} / {calories_out_today:.0f}")
    else:
        col_c.metric("Today: in vs out", "No data yet")

    if muscle_counts:
        st.caption("Muscle groups worked this week: " + ", ".join(f"{g} ({c}x)" for g, c in muscle_counts))

    if st.button("📊 Generate weekly recap (AI)"):
        with st.spinner("Analyzing your week..."):
            calories_in_week = _calories_in_for_week(user)
            summary = ai_fitness.get_adherence_summary(
                days_worked, days_goal, muscle_counts, total_burned, calories_in_week, profile,
            )
        st.markdown(summary)


def _render_routine_tab(user, profile, settings):
    log = _get_log(user)
    _render_muscle_diagram(user, profile, log)
    st.divider()
    _render_add_exercise(user, profile, settings)
    st.divider()
    _render_checklist(user, log)
    st.divider()
    _render_weekly_summary(user, profile, settings, log)


def _render_ai_tab(user, thresholds):
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

    uc_summary = conditions_tracker.get_recent_summary(user)
    if uc_summary:
        st.info(f"Also factoring in your Conditions Tracker data: {uc_summary}")

    health_profile = patient_profile.get_profile(user)
    profile_summary = patient_profile.summary_line(health_profile)
    if profile_summary:
        st.caption(f"📋 Personalizing using your Patient Profile: {profile_summary}")
    else:
        st.caption("📋 No Patient Profile on file — fill one in for a more personalized plan.")

    st.subheader("Tell us about your goals")
    with st.form("fitness_questionnaire"):
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

        if not ai_fitness.is_configured():
            st.info(
                "Set `GEMINI_API_KEY` in a `.env` file to enable AI-generated plans "
                "(see README)."
            )
        else:
            with st.spinner("Generating your plan..."):
                plan = ai_fitness.get_plan(profile, bloodwork_summary, needs_clearance, questionnaire, uc_summary, health_profile)
            st.markdown(plan)
        st.caption(ai_fitness.DISCLAIMER)


def render(user, thresholds):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("🏋️ Fitness Coach")
        st.caption(f"Signed in as **{user['email']}**" + (" (guest session)" if user["auth_provider"] == "guest" else ""))
    with top_right:
        if st.button("← Back to Services", key="back_link"):
            st.session_state.current_service = None
            st.rerun()

    st.markdown(
        "Build your own workout routine or get an AI-suggested plan. **To use this "
        "service:** set your facility and weekly goal below, then either add exercises "
        "to **My Routine** and check them off as you go, or answer the questionnaire "
        "under **AI Suggested Plan** for a generated diet + exercise plan."
    )
    st.warning(
        "**Not medical or nutritional advice.** This tool offers general fitness "
        "suggestions and estimates only. Always consult a healthcare provider before "
        "starting a new diet or exercise program."
    )

    profile = patient_profile.get_profile(user)
    settings = _get_settings(user)

    with st.expander("⚙️ Facility & weekly goal", expanded=not settings.get("days_per_week")):
        with st.form("fitness_settings_form"):
            facility = st.selectbox(
                "Where do you work out?", ["Both", "Home", "Gym"],
                index=["Both", "Home", "Gym"].index(settings.get("facility", "Both")),
            )
            days_per_week = st.number_input(
                "Exercise days per week (goal)", min_value=0, max_value=7,
                value=settings.get("days_per_week") or 3,
            )
            saved = st.form_submit_button("Save")
        if saved:
            _save_settings(user, facility, days_per_week)
            st.rerun()

    tab_routine, tab_ai = st.tabs(["📝 My Routine", "🤖 AI Suggested Plan"])
    with tab_routine:
        _render_routine_tab(user, profile, settings)
    with tab_ai:
        _render_ai_tab(user, thresholds)
