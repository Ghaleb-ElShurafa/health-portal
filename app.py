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
from services import bloodwork_analysis, community_hub, conditions_tracker, fitness_coach, patient_profile, plate_score

ensure_pwa_assets()
st.set_page_config(page_title="Health Services Portal", page_icon="🏥", layout="centered")
db.init_db()

WELCOME_MESSAGE = (
    "Welcome to the Health Services Portal! We're glad you're here. Start with "
    "Patient Profile so every other service can personalize itself to you, and "
    "check out the Community Hub to connect with others on a similar journey. "
    "Run into a problem? Use Technical Issues in the menu — our team reads every report."
)

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None
if "guest_entries" not in st.session_state:
    st.session_state.guest_entries = []
if "guest_tracked_conditions" not in st.session_state:
    st.session_state.guest_tracked_conditions = dict(db.EMPTY_TRACKED_CONDITIONS)
if "guest_condition_entries" not in st.session_state:
    st.session_state.guest_condition_entries = {}
if "guest_meal_entries" not in st.session_state:
    st.session_state.guest_meal_entries = []
if "guest_patient_profile" not in st.session_state:
    st.session_state.guest_patient_profile = dict(db.EMPTY_PATIENT_PROFILE)
if "guest_fitness_settings" not in st.session_state:
    st.session_state.guest_fitness_settings = dict(db.EMPTY_FITNESS_SETTINGS)
if "guest_workout_log" not in st.session_state:
    st.session_state.guest_workout_log = []
if "view_as_user" not in st.session_state:
    st.session_state.view_as_user = True
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
    st.session_state.guest_tracked_conditions = dict(db.EMPTY_TRACKED_CONDITIONS)
    st.session_state.guest_condition_entries = {}
    st.session_state.guest_meal_entries = []
    st.session_state.guest_patient_profile = dict(db.EMPTY_PATIENT_PROFILE)
    st.session_state.guest_fitness_settings = dict(db.EMPTY_FITNESS_SETTINGS)
    st.session_state.guest_workout_log = []
    st.session_state.pop("guest_workout_log_next_id", None)
    st.session_state.pop("pp_editing", None)
    st.session_state.pp_just_saved = False
    st.session_state.view_as_user = True
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
            db.create_welcome_message(user["id"], WELCOME_MESSAGE)
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
                    db.create_welcome_message(user["id"], WELCOME_MESSAGE)
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
            username = st.text_input(
                "Username", key="signup_username",
                placeholder="e.g. alexj — how friends will find you in the Community Hub",
            )
            c3, c4 = st.columns(2)
            age = c3.number_input("Age", min_value=0, max_value=120, step=1, value=None, key="signup_age")
            country = c4.text_input("Country of residence", key="signup_country")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            st.caption("Password needs at least 8 characters, including one number and one uppercase letter.")
            st.caption("Username needs 3-20 characters: letters, numbers, and underscores only.")
            st.caption("Medical conditions, medications, and goals are collected after signup in Patient Profile.")
            keep_logged_in = st.checkbox("Keep me logged in", key="signup_keep")
            if st.form_submit_button("Sign Up"):
                user, error = auth.sign_up(
                    email, password, first_name, last_name, int(age) if age is not None else None, country, username,
                )
                if user:
                    if keep_logged_in:
                        token = auth.create_remember_token(user["id"])
                        _set_remember_cookie(token)
                    st.session_state.auth_user = user
                    db.log_activity(user["email"], user.get("first_name"), "signup")
                    db.create_welcome_message(user["id"], WELCOME_MESSAGE)
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
                st.session_state.guest_welcome_message = {"content": WELCOME_MESSAGE, "seen": False}
                db.log_activity(display_name, display_name, "guest")
                st.rerun()

    st.divider()
    with st.expander("📲 Install this app on your iPhone"):
        st.caption("Adds a Health Portal icon to your home screen, so it opens like a regular app.")
        step_cols = st.columns(3)
        steps = [
            ("badge-blue", "📤", "1. Tap Share", "In Safari's toolbar, tap the Share icon (a square with an arrow pointing up)."),
            ("badge-teal", "➕", "2. Add to Home Screen", "Scroll down the menu that pops up — tap More first if you don't see it — and choose \"Add to Home Screen.\""),
            ("badge-green", "✅", "3. Tap Add", "Confirm by tapping Add in the top-right corner. The app icon now appears on your home screen."),
        ]
        for col, (badge_cls, icon, title, body) in zip(step_cols, steps):
            with col:
                st.markdown(
                    f'<div class="service-icon-badge {badge_cls}">{icon}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{title}**")
                st.caption(body)
        st.caption("Note: this only works in Safari — Chrome and other iPhone browsers don't support adding to the home screen.")


def render_site_menu(user):
    """Rendered directly inside the sidebar (not behind a nested popover) so
    opening the sidebar — one tap on mobile — immediately shows everything;
    no second "Menu" click required."""
    st.markdown("**☰ Menu**")

    tab_qa, tab_tutorials, tab_settings, tab_about, tab_review, tab_issues = st.tabs(
        ["❓ Q&A", "🎓 Tutorials", "⚙️ Settings", "ℹ️ About", "⭐ Leave a Review", "🚩 Technical Issues"]
    )

    with tab_about:
        st.markdown("**Health Services Portal**")
        st.write(
            "A multi-service health app: a Patient Profile screening personalizes "
            "AI-powered bloodwork analysis, a wellness/diet coach, a calendar-based "
            "conditions tracker, and a meal-photo calorie and health scorer."
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
            "3. **Fitness Coach** — build your own workout routine from a curated "
            "exercise library, or answer a short questionnaire to get an AI-suggested "
            "diet + exercise plan, automatically enriched by your bloodwork and "
            "Conditions Tracker data if you have any.\n"
            "4. **Conditions Tracker** — pick a condition to monitor, then click any "
            "day on the calendar to log symptoms; after a few entries, analyze "
            "patterns to spot trends and possible triggers.\n"
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
                "service works without one — Fitness Coach falls back to its "
                "questionnaire, and Conditions Tracker/Plate Score/Patient Profile "
                "don't need bloodwork at all."
            )
        with st.expander("Do I need to create an account?"):
            st.write(
                "No — use \"Continue as Guest\" to try the app with just a display "
                "name. Guest data only lasts for that browser session."
            )

    with tab_review:
        st.caption("Tell us what you think — the team reads every review and can reply to you directly.")
        st.session_state.setdefault("review_form_version", 0)
        rv = st.session_state.review_form_version
        feedback = st.text_area("Your feedback", key=f"review_feedback_v{rv}", placeholder="What do you like? What could be better?")
        if st.button("Submit Review", key="submit_review"):
            if feedback.strip():
                display_name = user.get("first_name") or user["email"]
                db.create_review(user.get("id"), user["email"], display_name, feedback.strip())
                st.session_state.review_form_version += 1
                st.success("Thanks for the feedback! Check Messages (top of the home screen) if the team replies.")
                st.rerun()
            else:
                st.warning("Please write something before submitting.")

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

    with tab_settings:
        is_guest = user["auth_provider"] == "guest"

        st.markdown("**Appearance**")
        current_dark = bool(user.get("dark_mode"))
        theme_choice = st.radio(
            "Theme", ["Light", "Dark"], index=1 if current_dark else 0,
            key="settings_theme", horizontal=True,
        )
        new_dark = theme_choice == "Dark"
        if new_dark != current_dark:
            user["dark_mode"] = new_dark
            if not is_guest:
                db.update_user_preferences(user["id"], new_dark, user.get("language", "English"))
            st.rerun()

        st.markdown("**Language**")
        languages = ["English", "Arabic", "French"]
        current_lang = user.get("language") or "English"
        lang_choice = st.selectbox(
            "Language", languages, index=languages.index(current_lang), key="settings_language",
        )
        if lang_choice != current_lang:
            user["language"] = lang_choice
            if not is_guest:
                db.update_user_preferences(user["id"], bool(user.get("dark_mode")), lang_choice)
            st.rerun()
        if lang_choice != "English":
            st.caption(
                "Arabic and French are on the way — the app will keep showing English "
                "under the hood until full translation ships."
            )

        if not is_guest:
            st.markdown("**Community**")
            st.session_state.setdefault("settings_username_version", 0)
            uv = st.session_state.settings_username_version
            with st.form(f"settings_username_form_v{uv}"):
                new_username = st.text_input(
                    "Username", value=user.get("username") or "", key=f"settings_username_v{uv}",
                    help="Lets friends find you in the Community Hub. 3-20 characters: letters, numbers, underscores.",
                )
                if st.form_submit_button("Update username"):
                    ok, msg = auth.change_username(user["id"], new_username)
                    if ok:
                        user["username"] = new_username.strip()
                        st.session_state.settings_username_version += 1
                        st.success("Username updated.")
                        st.rerun()
                    else:
                        st.error(msg)

            current_public = bool(user.get("community_public", True))
            public_choice = st.checkbox(
                "Share my posts on the Community Hub's public feed",
                value=current_public, key="settings_community_public",
            )
            if public_choice != current_public:
                user["community_public"] = public_choice
                db.update_community_privacy(user["id"], public_choice)
                st.rerun()
            st.caption("Turning this off hides your posts from everyone else, but you can still read the public feed and message friends.")

        if is_guest:
            st.divider()
            st.caption("Sign up for an account to manage account info and keep these preferences.")
        elif user["auth_provider"] != "password":
            st.divider()
            st.caption("Account info is managed by Google for sign-ins via Google — nothing to change here.")
        else:
            st.divider()
            st.markdown("**Account info**")
            st.caption(f"Signed in as {user['email']}")

            st.session_state.setdefault("settings_name_version", 0)
            nv = st.session_state.settings_name_version
            with st.form(f"settings_name_form_v{nv}"):
                first = st.text_input("First name", value=user.get("first_name") or "", key=f"settings_first_v{nv}")
                last = st.text_input("Last name", value=user.get("last_name") or "", key=f"settings_last_v{nv}")
                if st.form_submit_button("Update name"):
                    ok, msg = auth.change_display_name(user["id"], first, last)
                    if ok:
                        user["first_name"], user["last_name"] = first.strip(), last.strip()
                        st.session_state.settings_name_version += 1
                        st.success("Name updated.")
                        st.rerun()
                    else:
                        st.error(msg)

            st.session_state.setdefault("settings_email_version", 0)
            ev = st.session_state.settings_email_version
            with st.form(f"settings_email_form_v{ev}"):
                new_email = st.text_input("New email", key=f"settings_email_v{ev}")
                email_pw = st.text_input("Current password", type="password", key=f"settings_email_pw_v{ev}")
                if st.form_submit_button("Update email"):
                    ok, msg = auth.change_email(user["id"], email_pw, new_email)
                    if ok:
                        user["email"] = new_email.strip()
                        st.session_state.settings_email_version += 1
                        st.success("Email updated.")
                        st.rerun()
                    else:
                        st.error(msg)

            st.session_state.setdefault("settings_password_version", 0)
            pv = st.session_state.settings_password_version
            with st.form(f"settings_password_form_v{pv}"):
                current_pw = st.text_input("Current password", type="password", key=f"settings_cur_pw_v{pv}")
                new_pw = st.text_input("New password", type="password", key=f"settings_new_pw_v{pv}")
                st.caption("Needs at least 8 characters, including one number and one uppercase letter.")
                if st.form_submit_button("Update password"):
                    ok, msg = auth.change_password(user["id"], current_pw, new_pw)
                    if ok:
                        st.session_state.settings_password_version += 1
                        st.success("Password updated.")
                        st.rerun()
                    else:
                        st.error(msg)


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


def render_messages_button(user):
    if user["auth_provider"] == "guest":
        welcome = st.session_state.get("guest_welcome_message")
        unseen = 1 if welcome and not welcome["seen"] else 0
        label = f"💬 {unseen}" if unseen else "💬"
        with st.popover(label, help="Messages"):
            st.markdown("**Messages**")
            if welcome:
                with st.container(border=True):
                    st.caption("From the Health Portal team")
                    st.write(welcome["content"])
                if unseen and st.button("Mark as read", key="mark_welcome_read_guest", use_container_width=True):
                    st.session_state.guest_welcome_message["seen"] = True
                    st.rerun()
            st.caption(
                "Sign up for an account to keep your messages, reply-free updates from "
                "our team, and message friends you make in the Community Hub."
            )
        return

    welcome = db.get_welcome_message(user["id"])
    welcome_unseen = bool(welcome and not welcome["seen"])
    review_unseen = db.count_unseen_replies(user["id"])
    total_unseen = review_unseen + (1 if welcome_unseen else 0)
    label = f"💬 {total_unseen}" if total_unseen else "💬"
    with st.popover(label, help="Messages"):
        st.markdown("**Messages**")
        if welcome:
            with st.container(border=True):
                st.caption(f"From the Health Portal team ({welcome['created_at']})")
                st.write(welcome["content"])

        reviews = db.get_reviews_for_user(user["id"])
        replied = [r for r in reviews if r["admin_reply"]]
        if not replied and not welcome:
            st.caption("No messages yet. Leave a review from the Menu and the team may respond here.")
        else:
            for r in replied:
                with st.container(border=True):
                    st.caption(f"Your review ({r['created_at']}): {r['feedback']}")
                    st.markdown(f"**Team reply:** {r['admin_reply']}")
                    st.caption(r["replied_at"])
        if total_unseen:
            if st.button("Mark all as read", key="mark_all_read", use_container_width=True):
                if welcome_unseen:
                    db.mark_welcome_seen(user["id"])
                for r in replied:
                    if not r["user_seen_reply"]:
                        db.mark_review_seen(r["id"])
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
        msg_col, action_col = st.columns([1, 1])
        with msg_col:
            render_messages_button(user)
        with action_col:
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

    st.subheader("Ask anything")
    search_col, button_col = st.columns([9, 1], vertical_alignment="bottom")
    with search_col:
        query = st.text_input(
            "Search or ask a question",
            key="site_search_query",
            placeholder="e.g. How do I read my cholesterol results?",
            label_visibility="collapsed",
        )
    with button_col:
        submitted_search = st.button("🔍", key="search_submit", help="Search", use_container_width=True)
    if submitted_search and query.strip():
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
            if st.button(" ", key="open_patient_profile"):
                st.session_state.current_service = "patient_profile"
                st.rerun()
    with row1[1]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-teal">🩺</div>', unsafe_allow_html=True)
            st.markdown("#### Bloodwork Analysis")
            st.caption("Upload a lab report document, get AI-powered insights, and see trends over time.")
            if st.button(" ", key="open_bloodwork_analysis"):
                st.session_state.current_service = "bloodwork_analysis"
                st.rerun()
    with row1[2]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-green">🏋️</div>', unsafe_allow_html=True)
            st.markdown("#### Fitness Coach")
            st.caption("Build your own routine or get an AI-suggested plan, with a muscle diagram and calorie tracking.")
            if st.button(" ", key="open_fitness_coach"):
                st.session_state.current_service = "fitness_coach"
                st.rerun()

    row2 = st.columns(3)
    with row2[0]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-orange">📅</div>', unsafe_allow_html=True)
            st.markdown("#### Conditions Tracker")
            st.caption("Log symptoms on a calendar for any condition you're monitoring, and get an AI trend summary.")
            if st.button(" ", key="open_conditions_tracker"):
                st.session_state.current_service = "conditions_tracker"
                st.rerun()
    with row2[1]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-pink">🍽️</div>', unsafe_allow_html=True)
            st.markdown("#### Plate Score")
            st.caption("Photograph your meal for an AI-scored calorie and nutrition breakdown, personalized to your profile.")
            if st.button(" ", key="open_plate_score"):
                st.session_state.current_service = "plate_score"
                st.rerun()
    with row2[2]:
        with st.container(border=True):
            st.markdown('<div class="service-icon-badge badge-purple">👥</div>', unsafe_allow_html=True)
            st.markdown("#### Community Hub")
            st.caption("Share your journey publicly, connect with friends, and message them privately.")
            if st.button(" ", key="open_community_hub"):
                st.session_state.current_service = "community_hub"
                st.rerun()


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

    tab_users, tab_ranges, tab_announcement, tab_reviews, tab_issues, tab_activity = st.tabs(
        ["Users", "Reference Ranges", "Announcement", "Reviews", "Issues", "Activity"]
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

    with tab_reviews:
        st.subheader("User reviews")
        st.caption("Submitted via the \"Leave a Review\" tab in the sidebar menu. Replies show up in the user's Messages panel.")
        reviews = db.list_reviews()
        if not reviews:
            st.caption("No reviews submitted yet.")
        else:
            st.session_state.setdefault("review_reply_version", {})
            for review in reviews:
                status_icon = "🟢" if review["admin_reply"] else "🔴"
                who = review["display_name"] or review["email"]
                with st.expander(f"{status_icon} #{review['id']} — {who} — {review['created_at']}"):
                    st.markdown(f"**Feedback:** {review['feedback']}")
                    st.caption(f"Contact: {review['email']}")
                    rv = st.session_state.review_reply_version.get(review["id"], 0)
                    reply_text = st.text_area(
                        "Reply", value=review["admin_reply"] or "", key=f"reply_{review['id']}_v{rv}",
                    )
                    if st.button("Send Reply", key=f"send_reply_{review['id']}"):
                        if reply_text.strip():
                            db.reply_to_review(review["id"], reply_text.strip())
                            st.session_state.review_reply_version[review["id"]] = rv + 1
                            st.success("Reply sent.")
                            st.rerun()
                        else:
                            st.warning("Write a reply before sending.")

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


styles.inject(bool(st.session_state.auth_user and st.session_state.auth_user.get("dark_mode")))

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
    elif st.session_state.current_service == "fitness_coach":
        fitness_coach.render(current_user, _cached_thresholds())
    elif st.session_state.current_service == "conditions_tracker":
        conditions_tracker.render(current_user)
    elif st.session_state.current_service == "plate_score":
        plate_score.render(current_user)
    elif st.session_state.current_service == "community_hub":
        community_hub.render(current_user)
    else:
        render_landing(current_user, as_admin_preview=current_user.get("is_admin", False))
