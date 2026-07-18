"""Site-wide AI features: the top search bar (general Q&A) and the sidebar
help chat (navigation / technical support). Separate from ai_advice.py,
which only handles bloodwork interpretation for the Personal Doctor service.
"""

import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-5"

SITE_CONTEXT = """You are the site-wide assistant for "Health Services Portal", a
web app built with Streamlit. The portal has a landing page listing available
services as cards. Currently the only service is "Personal Doctor": users log
bloodwork results (lipid panel, glucose, HbA1c, blood pressure), get rule-based
flags against clinical reference ranges, an AI-generated plain-language summary,
and trend charts. More services will be added over time.

Accounts: users can sign up with email/password, log in with Google, or use a
guest mode with no account (guest data isn't saved after the session ends).
Admin users see an Admin Dashboard instead of the normal view, with tabs for
managing users, editing the clinical reference ranges, posting a site
announcement, and reviewing reported issues. Admins can click "View as User" to
preview the normal user experience.
"""


def is_configured():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def answer_search(query):
    """Single-turn general Q&A for the top search bar."""
    if not is_configured():
        return "AI search is unavailable: no ANTHROPIC_API_KEY configured (see README)."

    client = Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=SITE_CONTEXT
        + "\n\nAnswer the user's question concisely and helpfully. If it's about "
        "using this site, answer from the context above. If it's a general "
        "question unrelated to the site, just answer it normally. If it's a "
        "health question, remind the user this isn't medical advice.",
        messages=[{"role": "user", "content": query}],
    )
    return response.content[0].text


def help_reply(history):
    """Multi-turn help chat. `history` is a list of {"role": "user"|"assistant", "content": str}."""
    if not is_configured():
        return (
            "AI help chat is unavailable: no ANTHROPIC_API_KEY configured. "
            "You can still describe your issue below and report it for review."
        )

    client = Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=SITE_CONTEXT
        + "\n\nYou are the Help & Support assistant. Help the user navigate the "
        "site or troubleshoot technical issues, using the context above. Be "
        "concise. If the user describes something that sounds like a genuine "
        "bug or technical problem you can't resolve by explaining, tell them "
        "to use the 'Report a technical issue' box below the chat so it gets "
        "reviewed.",
        messages=history,
    )
    return response.content[0].text
