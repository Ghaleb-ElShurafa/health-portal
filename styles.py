"""Injects custom CSS for a professional, eye-catching look. Paired with
the fixed dark theme in .streamlit/config.toml (so colors here are tuned to
that specific palette, not theme-adaptive)."""

import streamlit as st

CSS = """
<style>
.stApp {
    background:
        radial-gradient(circle at 15% 0%, rgba(45, 212, 191, 0.12) 0%, transparent 45%),
        radial-gradient(circle at 85% 100%, rgba(56, 130, 246, 0.10) 0%, transparent 45%),
        linear-gradient(160deg, #0b1220 0%, #0e1b33 55%, #0b1220 100%);
    background-attachment: fixed;
}

/* Bordered containers (service cards) get a soft lift + hover effect */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(45, 212, 191, 0.15);
    border-color: rgba(45, 212, 191, 0.4) !important;
}

/* Buttons: rounded, teal accent */
.stButton > button, .stFormSubmitButton > button, .stLinkButton > a {
    border-radius: 10px !important;
    transition: transform 0.1s ease, box-shadow 0.15s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(45, 212, 191, 0.25);
}

/* Title styling */
h1 {
    background: linear-gradient(90deg, #e6edf3 0%, #7dd8cf 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0e1b33 0%, #0b1220 100%);
    border-right: 1px solid rgba(45, 212, 191, 0.15);
}

/* Statement-of-the-day callout */
.sotd-banner {
    background: linear-gradient(135deg, rgba(45, 212, 191, 0.14), rgba(56, 130, 246, 0.10));
    border: 1px solid rgba(45, 212, 191, 0.3);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
    font-size: 1.05rem;
}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)
