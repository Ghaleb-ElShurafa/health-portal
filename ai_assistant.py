"""Site-wide AI features: the top search bar (general Q&A) and the sidebar
help chat (navigation / technical support, and genuinely anything else the
user brings up). Separate from ai_advice.py and ai_wellness.py, which handle
service-specific AI content.
"""

import gemini_client

SITE_CONTEXT = """You are the site-wide assistant for "Health Services Portal", a
web app built with Streamlit. The portal has a landing page listing available
services as cards. There are currently three services:

- "Personal Doctor": users upload a bloodwork document (image or PDF) or
  enter results manually; the app extracts/stores lipid panel, glucose,
  HbA1c, and blood pressure values, flags them against clinical reference
  ranges, gives an AI-generated plain-language summary, and shows trend
  charts across every bloodwork on file over time.
- "Wellness Coach": generates a diet and exercise plan personalized from a
  user's latest Personal Doctor bloodwork and their diagnosis (if set),
  always recommending medical clearance before exercise if any bloodwork
  result needs a doctor.
- "UC Tracker": for users tracking ulcerative colitis, logs daily flares
  (yes/no, severity) and foods eaten, then analyzes patterns to help spot
  which foods correlate with flares.

More services will be added over time.

Accounts: users can sign up with email/password (with name, age, country of
residence, and an optional diagnosis), log in with Google, or use a guest
mode with no account (guest data isn't saved after the session ends). A
"keep me logged in" option persists sessions via a browser cookie. Admin
users see an Admin Dashboard instead of the normal view, with tabs for
managing users, editing the clinical reference ranges, posting a site
announcement, and reviewing reported issues. Admins can click "View as User"
to preview the normal user experience.
"""

FALLBACK_MESSAGE = (
    "The AI assistant is temporarily unavailable (the AI service is busy) — "
    "please try again in a moment."
)


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
    try:
        return gemini_client.generate(
            system_prompt=system,
            messages=[{"role": "user", "content": query}],
            max_tokens=400,
        )
    except gemini_client.GeminiUnavailableError:
        return FALLBACK_MESSAGE


def help_reply(history):
    """Multi-turn help chat. `history` is a list of {"role": "user"|"assistant", "content": str}."""
    if not is_configured():
        return (
            "AI help chat is unavailable: no GEMINI_API_KEY configured. "
            "You can still describe your issue below and report it for review."
        )

    system = (
        SITE_CONTEXT
        + "\n\nYou are the Help & Support assistant for this site. You can help with "
        "genuinely anything the user brings up — navigating the site, troubleshooting "
        "a technical problem, understanding a feature, or a general question — using "
        "the context above where relevant. Don't refuse or deflect topics unrelated to "
        "the site; just help. Be concise. If the user describes something that sounds "
        "like a genuine bug or technical problem you can't resolve by explaining, tell "
        "them to use the 'Report a technical issue' box below the chat so it gets "
        "reviewed. If it's a health question, remind them this isn't medical advice."
    )
    try:
        return gemini_client.generate(system_prompt=system, messages=history, max_tokens=400)
    except gemini_client.GeminiUnavailableError:
        return FALLBACK_MESSAGE
