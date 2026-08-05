import html
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import ai_assistant
import auth
import db
import reference_ranges as rr
import styles
from pwa import ensure_pwa_assets
from services import bloodwork_analysis, patient_profile, plate_score, uc_tracker, wellness_coach

ensure_pwa_assets()
st.set_page_config(page_title="Health Services Portal", page_icon="🏥", layout="centered")
styles.inject()
db.init_db()

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None
if "guest_entries" not in st.session_state:
    st.session_state.guest_entries = []
if "guest_uc_entries" not in st.session_state:
    st.session_state.guest_uc_entries = []
if "guest_meal_entries" not in st.session_state:
    st.session_state.guest_meal_entries = []
if "guest_patient_profile" not in st.session_state:
    st.session_state.guest_patient_profile = dict(db.EMPTY_PATIENT_PROFILE)
if "view_as_user" not in st.session_state:
    st.session_state.view_as_user = False
if "current_service" not in st.session_state:
    st.session_state.current_service = None
if "help_chat" not in st.session_state:
    st.session_state.help_chat = []
if "search_answer" not in st.session_state:
    st.session_state.search_answer = None


@st.cache_data(ttl=60)
def _cached_thresholds():
    return db.get_thresholds()


@st.cache_data(ttl=60)
def _cached_announcement():
    return db.get_announcement()


def _set_remember_cookie(token):
    components.html(
        f"<script>document.cookie = 'remember_token={token}; max-age={auth.REMEMBER_TOKEN_DAYS * 86400}; path=/; SameSite=Lax';</script>",
        height=0,
    )
    # Give the cookie script's iframe a moment to load and execute before
    # st.rerun() below tears down the DOM.
    time.sleep(0.3)


def _clear_remember_cookie():
    components.html(
        "<script>document.cookie = 'remember_token=; max-age=0; path=/; SameSite=Lax';</script>",
        height=0,
    )
    time.sleep(0.3)


def _log_out(user):
    if user and user.get("auth_provider") != "guest" and user.get("id") is not None:
        auth.clear_remember_token(user["id"])
    _clear_remember_cookie()
    st.session_state.auth_user = None
    st.session_state.guest_entries = []
    st.session_state.guest_uc_entries = []
    st.session_state.guest_meal_entries = []
    st.session_state.guest_patient_profile = dict(db.EMPTY_PATIENT_PROFILE)
    st.session_state.pop("pp_editing", None)
    st.session_state.pp_just_saved = False
    st.session_state.view_as_user = False
    st.session_state.current_service = None
    st.session_state.search_answer = None
    st.rerun()


# Try a "keep me logged in" cookie before showing the login screen.
if st.session_state.auth_user is None:
    remember_token = st.context.cookies.get("remember_token")
    if remember_token:
        remembered_user = auth.get_user_by_remember_token(remember_token)
        if remembered_user:
            st.session_state.auth_user = remembered_user
            db.log_activity(remembered_user["email"], remembered_user.get("first_name"), "remember_token")


def render_auth_gate():
    st.title("🏥 Health Services Portal")
    st.caption("Log in, sign up, or continue as a guest to try it out.")

    query = st.query_params
    if "code" in query and "state" in query:
        user, error = auth.complete_google_login(query["code"], query["state"])
        st.query_params.clear()
        if user:
            token = auth.create_remember_token(user["id"])
            _set_remember_cookie(token)
            st.session_state.auth_user = user
            db.log_activity(user["email"], user.get("first_name"), "google")
            st.rerun()
        else:
            st.error(error)

    tab_login, tab_signup, tab_guest = st.tabs(["Log In", "Sign Up", "Continue as Guest"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            keep_logged_in = st.checkbox("Keep me logged in", key="login_keep")
            if st.form_submit_button("Log In"):
                user, error = auth.log_in(email, password)
                if user:
                    if keep_logged_in:
                        token = auth.create_remember_token(user["id"])
                        _set_remember_cookie(token)
                    st.session_state.auth_user = user
                    db.log_activity(user["email"], user.get("first_name"), "password")
                    st.rerun()
                else:
                    st.error(error)

        if auth.google_configured():
            st.divider()
            st.link_button("Sign in with Google", auth.build_google_auth_url())
        else:
            st.caption("Google sign-in isn't configured yet (see README).")

    with tab_signup:
        with st.form("signup_form"):
            c1, c2 = st.columns(2)
            first_name = c1.text_input("First name", key="signup_first_name")
            last_name = c2.text_input("Last name", key="signup_last_name")
            c3, c4 = st.columns(2)
            age = c3.number_input("Age", min_value=0, max_value=120, step=1, value=None, key="signup_age")
            country = c4.text_input("Country of residence", key="signup_country")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            st.caption("Password needs at least 8 characters, including one number and one uppercase letter.")
            st.caption("Medical conditions, medications, and goals are collected after signup in Patient Profile.")
            keep_logged_in = st.checkbox("Keep me logged in", key="signup_keep")
            if st.form_submit_button("Sign Up"):
                user, error = auth.sign_up(
                    email, password, first_name, last_name, int(age) if age is not None else None, country,
                )
                if user:
                    if keep_logged_in:
                        token = auth.create_remember_token(user["id"])
                        _set_remember_cookie(token)
                    st.session_state.auth_user = user
                    db.log_activity(user["email"], user.get("first_name"), "signup")
                    st.rerun()
                else:
                    st.error(error)

    with tab_guest:
        st.caption("Try the app without creating an account. Guest data is only kept for this browser session and won't be saved after you close the tab.")
        guest_name = st.text_input("Choose a display name", key="guest_display_name", placeholder="e.g. Alex")
        if st.button("Continue as Guest"):
            if not guest_name.strip():
                st.error("Please enter a display name.")
            else:
                display_name = guest_name.strip()
                st.session_state.auth_user = {
                    "id": None,
                    "email": display_name,
                    "auth_provider": "guest",
                    "is_admin": False,
                    "first_name": display_name,
                }
                db.log_activity(display_name, display_name, "guest")
                st.rerun()


def render_site_menu(user):
    with st.popover("☰ Menu", use_container_width=True):
        tab_about, tab_tutorials, tab_qa, tab_issues = st.tabs(
            ["ℹ️ About", "🎓 Tutorials", "❓ Q&A", "🚩 Technical Issues"]
        )

        with tab_about:
            st.markdown("**Health Services Portal**")
            st.write(
                "A multi-service health app: a Patient Profile screening personalizes "
                "AI-powered bloodwork analysis, a wellness/diet coach, an ulcerative "
                "colitis tracker, and a meal-photo calorie and health scorer."
            )
            st.caption(
                "⚠️ This is an educational/portfolio project, not medical advice, and "
                "not a substitute for care from a licensed professional."
            )

        with tab_tutorials:
            st.markdown("**Getting started**")
            st.markdown(
                "1. **Patient Profile** — start here. Add any conditions, medications, "
                "supplements, and goals so every other service can personalize itself "
                "to you.\n"
                "2. **Bloodwork Analysis** — upload a photo or PDF of a lab report; AI "
                "reads the values, you review/correct them, then save to see flagged "
                "results and a summary.\n"
                "3. **Wellness Coach** — answer a short questionnaire to get a diet + "
                "exercise plan, automatically enriched by your bloodwork and UC Tracker "
                "data if you have any.\n"
                "4. **UC Tracker** — log daily flare status and foods eaten; after a few "
                "entries, analyze patterns to spot possible triggers.\n"
                "5. **Plate Score** — photograph or upload a meal photo for an instant "
                "calorie/nutrition score, personalized to your profile."
            )

        with tab_qa:
            with st.expander("Is this real medical advice?"):
                st.write(
                    "No. Every AI-generated summary is educational only. \"Consult a "
                    "doctor\" flags are always computed with local rule-based logic, "
                    "independent of the AI — always follow up with a real clinician."
                )
            with st.expander("Is my data private?"):
                st.write(
                    "Your data is stored to power your own account's features (trends, "
                    "history, personalization) and isn't shared. Uploaded bloodwork/meal "
                    "photos are read by the AI and not stored — only the extracted values "
                    "are kept. Guest sessions aren't saved at all once you close the tab."
                )
            with st.expander("How does the AI work?"):
                st.write(
                    "Google's Gemini API reads documents/photos and writes explanatory "
                    "text. Anything clinically significant (like a \"consult a doctor\" "
                    "flag) is always decided by fixed rule-based logic, never by the AI."
                )
            with st.expander("What if I don't have a lab report to upload?"):
                st.write(
                    "Bloodwork Analysis requires an uploaded document, but every other "
                    "service works without one — Wellness Coach falls back to its "
                    "questionnaire, and UC Tracker/Plate Score/Patient Profile don't need "
                    "bloodwork at all."
                )
            with st.expander("Do I need to create an account?"):
                st.write(
                    "No — use \"Continue as Guest\" to try the app with just a display "
                    "name. Guest data only lasts for that browser session."
                )

        with tab_issues:
            st.caption("Found a bug or something not working right? Let us know.")
            st.session_state.setdefault("issue_form_version", 0)
            iv = st.session_state.issue_form_version
            description = st.text_area("What went wrong?", key=f"issue_description_v{iv}")
            if st.button("Submit Report", key="submit_issue"):
                if description.strip():
                    chat_context = "\n".join(f"{m['role']}: {m['content']}" for m in st.session_state.help_chat)
                    db.create_issue(user["email"], description.strip(), chat_context)
                    st.session_state.issue_form_version += 1
                    st.success("Thanks — this has been logged for review.")
                    st.rerun()
                else:
                    st.warning("Please describe the issue before submitting.")


def render_sidebar_help(user):
    with st.sidebar:
        render_site_menu(user)
        st.divider()

        st.header("🆘 Help & Support")
        st.caption("Ask a question about using the site.")

        for msg in st.session_state.help_chat:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        prompt = st.chat_input("Ask for help...")
        if prompt:
            st.session_state.help_chat.append({"role": "user", "content": prompt})
            with st.spinner("Thinking..."):
                reply = ai_assistant.help_reply(st.session_state.help_chat)
            st.session_state.help_chat.append({"role": "assistant", "content": reply})
            st.rerun()


def render_landing(user, as_admin_preview=False):
    display_name = user.get("first_name") or ("Guest" if user["auth_provider"] == "guest" else user["email"])

    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title(f"🏥 Welcome back, {display_name}!")
        subtitle = f"Signed in as <strong>{html.escape(user['email'])}</strong>"
        if user["auth_provider"] == "guest":
            subtitle += " (guest session)"
        st.markdown(f'<p class="hero-subtitle">{subtitle}</p>', unsafe_allow_html=True)
    with top_right:
        if as_admin_preview:
            if st.button("Back to Admin"):
                st.session_state.view_as_user = False
                st.rerun()
        elif st.button("Log out"):
            _log_out(user)

    profile_summary = patient_profile.summary_line(patient_profile.get_profile(user))
    if profile_summary:
        st.caption("📋 " + profile_summary)
    else:
        st.caption("📋 No Patient Profile on file yet — fill one in below for more personalized results.")

    announcement = _cached_announcement()
    if announcement:
        st.info(announcement)

    st.subheader("🔍 Ask anything")
    query = st.text_input(
        "Search or ask a question",
        key="site_search_query",
        placeholder="e.g. How do I read my cholesterol results?",
        label_visibility="collapsed",
    )
    if st.button("Search") and query.strip():
        with st.spinner("Thinking..."):
            st.session_state.search_answer = ai_assistant.answer_search(query.strip())
        st.rerun()

    if st.session_state.search_answer:
        with st.container(border=True):
            ans_col, close_col = st.columns([9, 1])
            with close_col:
                if st.button("✕", key="close_search_answer", help="Close"):
                    st.session_state.search_answer = None
                    st.rerun()
            with ans_col:
                st.markdown(st.session_state.search_answer)

    st.divider()
    st.subheader("Services")
    row1 = st.columns(3)
    with row1[0]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-blue">📋</div>', unsafe_allow_html=True)
            st.markdown("#### Patient Profile")
            st.caption("A general health screening — conditions, medications, supplements, goals — that personalizes every other service.")
            if st.button("Open", key="open_patient_profile"):
                st.session_state.current_service = "patient_profile"
                st.rerun()
    with row1[1]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-teal">🩺</div>', unsafe_allow_html=True)
            st.markdown("#### Bloodwork Analysis")
            st.caption("Upload a lab report document, get AI-powered insights, and see trends over time.")
            if st.button("Open", key="open_bloodwork_analysis"):
                st.session_state.current_service = "bloodwork_analysis"
                st.rerun()
    with row1[2]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-green">🥗</div>', unsafe_allow_html=True)
            st.markdown("#### Wellness Coach")
            st.caption("Get a personalized diet and exercise plan, tailored to your profile and bloodwork.")
            if st.button("Open", key="open_wellness_coach"):
                st.session_state.current_service = "wellness_coach"
                st.rerun()

    row2 = st.columns(3)
    with row2[0]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-orange">🔥</div>', unsafe_allow_html=True)
            st.markdown("#### UC Tracker")
            st.caption("Log flares and food to spot patterns for ulcerative colitis.")
            if st.button("Open", key="open_uc_tracker"):
                st.session_state.current_service = "uc_tracker"
                st.rerun()
    with row2[1]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-pink">🍽️</div>', unsafe_allow_html=True)
            st.markdown("#### Plate Score")
            st.caption("Photograph your meal for an AI-scored calorie and nutrition breakdown, personalized to your profile.")
            if st.button("Open", key="open_plate_score"):
                st.session_state.current_service = "plate_score"
                st.rerun()
    with row2[2]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-purple">➕</div>', unsafe_allow_html=True)
            st.markdown("#### More services")
            st.caption("New services will appear here as they're added.")


def render_admin(user):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("🛠️ Admin Dashboard")
        st.caption(f"Signed in as **{user['email']}** (admin)")
    with top_right:
        if st.button("View as User"):
            st.session_state.view_as_user = True
            st.rerun()
        if st.button("Log out"):
            _log_out(user)

    tab_users, tab_ranges, tab_announcement, tab_issues, tab_activity = st.tabs(
        ["Users", "Reference Ranges", "Announcement", "Issues", "Activity"]
    )

    with tab_users:
        st.subheader("Registered users")
        users = db.list_users()
        if not users:
            st.caption("No registered users yet.")
        else:
            users_df = pd.DataFrame(users)
            users_df["is_admin"] = users_df["is_admin"].astype(bool)
            st.dataframe(users_df, use_container_width=True)

            st.divider()
            st.subheader("Manage a user")
            options = {f"{u['email']} (id {u['id']})": u for u in users}
            chosen_label = st.selectbox("Select a user", list(options.keys()))
            chosen = options[chosen_label]

            c1, c2 = st.columns(2)
            with c1:
                make_admin = not chosen["is_admin"]
                label = "Grant admin" if make_admin else "Revoke admin"
                if st.button(label):
                    db.set_admin(chosen["id"], make_admin)
                    st.rerun()
            with c2:
                if chosen["id"] != user["id"] and st.button("Delete user", type="secondary"):
                    db.delete_user(chosen["id"])
                    st.rerun()
            if chosen["id"] == user["id"]:
                st.caption("You can't delete your own account from here.")

    with tab_ranges:
        st.subheader("Clinical reference ranges")
        st.caption("These thresholds control how results are flagged for every user. Changes apply immediately.")
        st.session_state.setdefault("thresholds_version", 0)
        version = st.session_state.thresholds_version
        current = _cached_thresholds()
        with st.form("thresholds_form"):
            new_values = {}
            for section_title, fields in rr.THRESHOLD_GROUPS:
                st.markdown(f"**{section_title}**")
                cols = st.columns(len(fields))
                for col, (key, label) in zip(cols, fields):
                    new_values[key] = col.number_input(label, value=float(current[key]), key=f"th_{key}_v{version}")
            if st.form_submit_button("Save Changes"):
                for key, value in new_values.items():
                    if value != current[key]:
                        db.set_threshold(key, value)
                st.session_state.thresholds_version += 1
                _cached_thresholds.clear()
                st.success("Reference ranges updated.")
                st.rerun()

        if st.button("Reset all to defaults"):
            for key, value in rr.DEFAULT_THRESHOLDS.items():
                db.set_threshold(key, value)
            st.session_state.thresholds_version += 1
            _cached_thresholds.clear()
            st.rerun()

    with tab_announcement:
        st.subheader("Site announcement")
        st.caption("Shown as a banner to every user (including guests) on the main page. Leave blank to hide it.")
        current_announcement = _cached_announcement()
        new_announcement = st.text_area("Announcement text", value=current_announcement, height=100)
        if st.button("Save Announcement"):
            db.set_announcement(new_announcement)
            _cached_announcement.clear()
            st.success("Announcement saved.")
            st.rerun()

    with tab_issues:
        st.subheader("Reported technical issues")
        st.caption("Submitted by users via the Help & Support sidebar.")
        issues = db.list_issues()
        if not issues:
            st.caption("No issues reported yet.")
        else:
            for issue in issues:
                status_icon = "🟢" if issue["status"] == "resolved" else "🔴"
                with st.expander(f"{status_icon} #{issue['id']} — {issue['user_email']} — {issue['created_at']}"):
                    st.markdown(f"**Description:** {issue['description']}")
                    if issue["chat_context"]:
                        st.markdown("**Chat context:**")
                        st.text(issue["chat_context"])
                    if issue["status"] == "open":
                        if st.button("Mark resolved", key=f"resolve_{issue['id']}"):
                            db.set_issue_status(issue["id"], "resolved")
                            st.rerun()
                    else:
                        if st.button("Reopen", key=f"reopen_{issue['id']}"):
                            db.set_issue_status(issue["id"], "open")
                            st.rerun()

    with tab_activity:
        st.subheader("Sign-in activity")
        st.caption("Every sign-in — password, Google, guest, or auto-login via 'keep me logged in' — most recent first.")
        activity = db.list_activity()
        if not activity:
            st.caption("No activity logged yet.")
        else:
            st.dataframe(pd.DataFrame(activity), use_container_width=True)


if st.session_state.auth_user is None:
    render_auth_gate()
else:
    current_user = st.session_state.auth_user
    render_sidebar_help(current_user)

    if current_user.get("is_admin") and not st.session_state.view_as_user:
        render_admin(current_user)
    elif st.session_state.current_service == "patient_profile":
        patient_profile.render(current_user)
    elif st.session_state.current_service == "bloodwork_analysis":
        bloodwork_analysis.render(current_user, _cached_thresholds())
    elif st.session_state.current_service == "wellness_coach":
        wellness_coach.render(current_user, _cached_thresholds())
    elif st.session_state.current_service == "uc_tracker":
        uc_tracker.render(current_user)
    elif st.session_state.current_service == "plate_score":
        plate_score.render(current_user)
    else:
        render_landing(current_user, as_admin_preview=current_user.get("is_admin", False))
