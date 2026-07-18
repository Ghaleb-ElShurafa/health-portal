import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import ai_assistant
import auth
import db
import reference_ranges as rr
from pwa import ensure_pwa_assets
from services import personal_doctor, wellness_coach

ensure_pwa_assets()
st.set_page_config(page_title="Health Services Portal", page_icon="🏥", layout="centered")
db.init_db()

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None
if "guest_entries" not in st.session_state:
    st.session_state.guest_entries = []
if "view_as_user" not in st.session_state:
    st.session_state.view_as_user = False
if "current_service" not in st.session_state:
    st.session_state.current_service = None
if "help_chat" not in st.session_state:
    st.session_state.help_chat = []


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
    st.session_state.view_as_user = False
    st.session_state.current_service = None
    st.rerun()


# Try a "keep me logged in" cookie before showing the login screen.
if st.session_state.auth_user is None:
    remember_token = st.context.cookies.get("remember_token")
    if remember_token:
        remembered_user = auth.get_user_by_remember_token(remember_token)
        if remembered_user:
            st.session_state.auth_user = remembered_user


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
            keep_logged_in = st.checkbox("Keep me logged in", key="signup_keep")
            if st.form_submit_button("Sign Up"):
                user, error = auth.sign_up(
                    email, password, first_name, last_name, int(age) if age is not None else None, country
                )
                if user:
                    if keep_logged_in:
                        token = auth.create_remember_token(user["id"])
                        _set_remember_cookie(token)
                    st.session_state.auth_user = user
                    st.rerun()
                else:
                    st.error(error)

    with tab_guest:
        st.caption("Try the app without creating an account. Guest data is only kept for this browser session and won't be saved after you close the tab.")
        if st.button("Continue as Guest"):
            st.session_state.auth_user = {"id": None, "email": "Guest", "auth_provider": "guest", "is_admin": False}
            st.rerun()


def render_sidebar_help(user):
    with st.sidebar:
        st.header("🆘 Help & Support")
        st.caption("Ask a question about using the site, or report a technical issue.")

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

        st.divider()
        with st.expander("🚩 Report a technical issue"):
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


def render_landing(user, as_admin_preview=False):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("🏥 Health Services Portal")
        st.caption(f"Signed in as **{user['email']}**" + (" (guest session)" if user["auth_provider"] == "guest" else ""))
    with top_right:
        if as_admin_preview:
            if st.button("Back to Admin"):
                st.session_state.view_as_user = False
                st.rerun()
        elif st.button("Log out"):
            _log_out(user)

    announcement = db.get_announcement()
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
            answer = ai_assistant.answer_search(query.strip())
        st.markdown(answer)

    st.divider()
    st.subheader("Services")
    cols = st.columns(3)
    with cols[0]:
        with st.container(border=True):
            st.markdown("### 🩺 Personal Doctor")
            st.caption("Track bloodwork results, get AI-powered insights, and see trends over time.")
            if st.button("Open", key="open_personal_doctor"):
                st.session_state.current_service = "personal_doctor"
                st.rerun()
    with cols[1]:
        with st.container(border=True):
            st.markdown("### 🥗 Wellness Coach")
            st.caption("Get a personalized diet and exercise plan, informed by your bloodwork.")
            if st.button("Open", key="open_wellness_coach"):
                st.session_state.current_service = "wellness_coach"
                st.rerun()
    with cols[2]:
        with st.container(border=True):
            st.markdown("### ➕ More services")
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

    tab_users, tab_ranges, tab_announcement, tab_issues = st.tabs(
        ["Users", "Reference Ranges", "Announcement", "Issues"]
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
        current = db.get_thresholds()
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
                st.success("Reference ranges updated.")
                st.rerun()

        if st.button("Reset all to defaults"):
            for key, value in rr.DEFAULT_THRESHOLDS.items():
                db.set_threshold(key, value)
            st.session_state.thresholds_version += 1
            st.rerun()

    with tab_announcement:
        st.subheader("Site announcement")
        st.caption("Shown as a banner to every user (including guests) on the main page. Leave blank to hide it.")
        current_announcement = db.get_announcement()
        new_announcement = st.text_area("Announcement text", value=current_announcement, height=100)
        if st.button("Save Announcement"):
            db.set_announcement(new_announcement)
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


if st.session_state.auth_user is None:
    render_auth_gate()
else:
    current_user = st.session_state.auth_user
    render_sidebar_help(current_user)

    if current_user.get("is_admin") and not st.session_state.view_as_user:
        render_admin(current_user)
    elif st.session_state.current_service == "personal_doctor":
        personal_doctor.render(current_user, db.get_thresholds())
    elif st.session_state.current_service == "wellness_coach":
        wellness_coach.render(current_user, db.get_thresholds())
    else:
        render_landing(current_user, as_admin_preview=current_user.get("is_admin", False))
