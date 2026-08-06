"""Community Hub: a simple public feed for sharing your health journey, plus
friends and private messaging between them. Guests don't have a persistent
identity across sessions, so this service is registered-users only.
"""

import streamlit as st

import db


def _display_name(user_row):
    name = f"{user_row.get('first_name') or ''} {user_row.get('last_name') or ''}".strip()
    return name or user_row["email"]


def _render_feed_tab(user):
    is_public = bool(user.get("community_public", True))
    if is_public:
        st.session_state.setdefault("community_post_version", 0)
        pv = st.session_state.community_post_version
        content = st.text_area(
            "Share something with the community",
            key=f"community_post_v{pv}",
            placeholder="How's your journey going? Share a win, a tip, or ask for advice...",
        )
        if st.button("Post", key="submit_community_post"):
            if content.strip():
                display_name = user.get("first_name") or user["email"]
                db.create_post(user["id"], display_name, content.strip())
                st.session_state.community_post_version += 1
                st.rerun()
            else:
                st.warning("Write something before posting.")
    else:
        st.info(
            "You've opted out of the public feed in Settings, so posting is turned off. "
            "You can still read what others share below."
        )

    st.divider()
    posts = db.list_public_posts()
    if not posts:
        st.caption("No posts yet — be the first to share something.")
        return
    for post in posts:
        with st.container(border=True):
            header_col, delete_col = st.columns([5, 1])
            with header_col:
                st.markdown(f"**{post['display_name']}** · {post['created_at']}")
            with delete_col:
                if post["user_id"] == user["id"]:
                    if st.button("Delete", key=f"delete_post_{post['id']}"):
                        db.delete_post(post["id"], user["id"])
                        st.rerun()
            st.write(post["content"])


def _render_friends_tab(user):
    st.markdown("**Find people**")
    query = st.text_input("Search by name or email", key="community_friend_search", placeholder="e.g. Alex or alex@example.com")
    if query.strip():
        results = db.search_users(query.strip(), user["id"])
        friend_ids = {f["user_id"] for f in db.list_friends(user["id"])}
        pending_ids = db.list_sent_request_ids(user["id"])
        if not results:
            st.caption("No matching users found.")
        for person in results:
            with st.container(border=True):
                cols = st.columns([3, 1])
                with cols[0]:
                    st.write(_display_name(person))
                    st.caption(person["email"])
                with cols[1]:
                    if person["id"] in friend_ids:
                        st.caption("Friends")
                    elif person["id"] in pending_ids:
                        st.caption("Requested")
                    else:
                        if st.button("Add", key=f"add_friend_{person['id']}"):
                            db.send_friend_request(user["id"], person["id"])
                            st.rerun()

    requests = db.list_pending_requests(user["id"])
    if requests:
        st.divider()
        st.markdown("**Friend requests**")
        for req in requests:
            with st.container(border=True):
                cols = st.columns([3, 1, 1])
                with cols[0]:
                    st.write(_display_name(req))
                    st.caption(req["email"])
                with cols[1]:
                    if st.button("Accept", key=f"accept_{req['request_id']}"):
                        db.respond_friend_request(req["request_id"], True)
                        st.rerun()
                with cols[2]:
                    if st.button("Decline", key=f"decline_{req['request_id']}"):
                        db.respond_friend_request(req["request_id"], False)
                        st.rerun()

    st.divider()
    st.markdown("**Your friends**")
    friends = db.list_friends(user["id"])
    if not friends:
        st.caption("No friends yet — search for someone above to get started.")
    for friend in friends:
        with st.container(border=True):
            cols = st.columns([3, 1])
            with cols[0]:
                st.write(_display_name(friend))
                st.caption(friend["email"])
            with cols[1]:
                if st.button("Remove", key=f"remove_friend_{friend['user_id']}"):
                    db.remove_friend(user["id"], friend["user_id"])
                    st.rerun()


def _render_messages_tab(user):
    friends = db.list_friends(user["id"])
    if not friends:
        st.caption("Add friends in the Friends tab first — you can only message friends.")
        return

    options = {_display_name(f): f["user_id"] for f in friends}
    unread_by_friend = {f["user_id"]: db.count_unread_from(user["id"], f["user_id"]) for f in friends}
    labels = [f"{name} ({unread_by_friend[uid]})" if unread_by_friend[uid] else name for name, uid in options.items()]
    label_to_uid = dict(zip(labels, options.values()))
    chosen_label = st.selectbox("Conversation", labels, key="community_conversation_choice")
    other_id = label_to_uid[chosen_label]

    db.mark_messages_read(user["id"], other_id)

    messages = db.list_conversation(user["id"], other_id)
    with st.container(border=True):
        if not messages:
            st.caption("No messages yet — say hello below.")
        for msg in messages:
            sender = "You" if msg["from_user_id"] == user["id"] else chosen_label.split(" (")[0]
            st.markdown(f"**{sender}** · {msg['created_at']}")
            st.write(msg["content"])

    st.session_state.setdefault("community_message_version", 0)
    mv = st.session_state.community_message_version
    reply = st.text_input("Message", key=f"community_message_v{mv}", label_visibility="collapsed", placeholder="Type a message...")
    if st.button("Send", key="send_community_message"):
        if reply.strip():
            db.send_message(user["id"], other_id, reply.strip())
            st.session_state.community_message_version += 1
            st.rerun()


def render(user):
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("👥 Community Hub")
        st.caption(f"Signed in as **{user['email']}**")
    with top_right:
        if st.button("← Back to Services", key="back_link"):
            st.session_state.current_service = None
            st.rerun()

    if user["auth_provider"] == "guest":
        st.info("Sign up for an account to join the Community Hub — guest sessions can't have friends or a persistent public profile.")
        return

    st.markdown(
        "Share your health journey publicly, connect with friends, and message them "
        "privately. You can turn off public sharing anytime in **Settings**."
    )

    tab_feed, tab_friends, tab_messages = st.tabs(["🌍 Public Feed", "👥 Friends", "💬 Messages"])
    with tab_feed:
        _render_feed_tab(user)
    with tab_friends:
        _render_friends_tab(user)
    with tab_messages:
        _render_messages_tab(user)
