"""Site-wide AI features: the top search bar (general Q&A) and the sidebar
help chat (navigation / technical support). Separate from ai_advice.py and
ai_wellness.py, which handle service-specific AI content.
"""

import gemini_client

SITE_CONTEXT = """You are the site-wide assistant for "Health Services Portal", a
web app built with Streamlit. The portal has a landing page listing available
services as cards. There are currently two services: "Personal Doctor", where
users log bloodwork results (lipid panel, glucose, HbA1c, blood pressure) and
get rule-based flags against clinical reference ranges, an AI-generated
plain-language summary, and trend charts; and "Wellness Coach", which
generates a diet and exercise plan personalized from a user's latest Personal
Doctor bloodwork (or a short questionnaire if none is on file), always
recommending medical clearance before exercise if any bloodwork result needs
a doctor. More services will be added over time.

Accounts: users can sign up with email/password (with name, age, country of
residence), log in with Google, or use a guest mode with no account (guest
data isn't saved after the session ends). A "keep me logged in" option
persists sessions via a browser cookie. Admin users see an Admin Dashboard
instead of the normal view, with tabs for managing users, editing the
clinical reference ranges, posting a site announcement, and reviewing
reported issues. Admins can click "View as User" to preview the normal user
experience.
"""


def is_configured():
    return gemini_client.is_configured()


def answer_search(query):
    """Single-turn general Q&A for the top search bar."""
    if not is_configured():
        return "AI search is unavailable: no GEMINI_API_KEY configured (see README)."

    system = (
        SITE_CONTEXT
        + "\n\nAnswer the user's question concisely and helpfully. If it's about "
        "using this site, answer from the context above. If it's a general "
        "question unrelated to the site, just answer it normally. If it's a "
        "health question, remind the user this isn't medical advice."
    )
    return gemini_client.generate(
        system_prompt=system,
        messages=[{"role": "user", "content": query}],
        max_tokens=400,
    )


def help_reply(history):
    """Multi-turn help chat. `history` is a list of {"role": "user"|"assistant", "content": str}."""
    if not is_configured():
        return (
            "AI help chat is unavailable: no GEMINI_API_KEY configured. "
            "You can still describe your issue below and report it for review."
        )

    system = (
        SITE_CONTEXT
        + "\n\nYou are the Help & Support assistant. Help the user navigate the "
        "site or troubleshoot technical issues, using the context above. Be "
        "concise. If the user describes something that sounds like a genuine "
        "bug or technical problem you can't resolve by explaining, tell them "
        "to use the 'Report a technical issue' box below the chat so it gets "
        "reviewed."
    )
    return gemini_client.generate(system_prompt=system, messages=history, max_tokens=400)
