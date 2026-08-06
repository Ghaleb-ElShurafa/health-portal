"""Injects custom CSS for the "Calm Drift" look — a warm cream base with
soft blurred blue/purple gradients, inspired by Calm/Headspace's visual
language. Paired with the fixed light theme in .streamlit/config.toml (so
colors here are tuned to that specific palette, not theme-adaptive)."""

import streamlit as st

CSS = """
<style>
.stApp {
    background:
        radial-gradient(circle at 18% 12%, rgba(147, 168, 224, 0.30) 0%, transparent 45%),
        radial-gradient(circle at 85% 18%, rgba(196, 167, 231, 0.26) 0%, transparent 45%),
        radial-gradient(circle at 50% 105%, rgba(251, 191, 165, 0.16) 0%, transparent 55%),
        #f9f4f2;
    background-attachment: fixed;
}

/* Bordered containers (service cards) get a soft frosted look + hover lift */
div[data-testid="stVerticalBlock"]:has(> div[class*="st-key-open_"]) {
    border-radius: 16px !important;
    background: rgba(255, 255, 255, 0.55);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    position: relative;
    cursor: pointer;
}
div[data-testid="stVerticalBlock"]:has(> div[class*="st-key-open_"]):hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 28px rgba(0, 97, 239, 0.14);
    border-color: rgba(0, 97, 239, 0.35) !important;
}
/* The "Open" button becomes an invisible full-card click target so the whole
   card is clickable, not just a small button at the bottom. */
div[data-testid="stVerticalBlock"] > div[class*="st-key-open_"] {
    position: absolute;
    inset: 0;
    z-index: 5;
}
div[data-testid="stVerticalBlock"] > div[class*="st-key-open_"] button {
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
}

/* Borderless "back" links: plain clickable text, no button box */
div[class*="st-key-back_link"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #0061ef !important;
    padding: 0.2rem 0 !important;
    font-weight: 600;
}
div[class*="st-key-back_link"] button:hover {
    text-decoration: underline;
    transform: none !important;
    box-shadow: none !important;
}

/* Search bar: minimal underline style instead of a boxed input + separate button */
div[class*="st-key-site_search_query"] input {
    border: none !important;
    border-bottom: 2px solid rgba(0, 97, 239, 0.30) !important;
    border-radius: 0 !important;
    background: transparent !important;
    padding-left: 0.2rem !important;
    transition: border-color 0.15s ease;
}
div[class*="st-key-site_search_query"] input:focus {
    border-bottom-color: #0061ef !important;
    box-shadow: none !important;
}
div[class*="st-key-search_submit"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #0061ef !important;
    font-size: 1.3rem !important;
}
div[class*="st-key-search_submit"] button:hover {
    transform: scale(1.15) !important;
    box-shadow: none !important;
}

/* Buttons: rounded, blue accent */
.stButton > button, .stFormSubmitButton > button, .stLinkButton > a {
    border-radius: 10px !important;
    transition: transform 0.1s ease, box-shadow 0.15s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 97, 239, 0.20);
}

/* Title styling */
h1 {
    background: linear-gradient(90deg, #2d2c2b 0%, #0061ef 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
    font-weight: 800 !important;
}

/* Landing page hero */
.hero-subtitle {
    color: #756e68;
    font-size: 1.05rem;
    margin-top: -0.5rem;
    margin-bottom: 1.25rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #fffdfb 0%, #f5efec 100%);
    border-right: 1px solid rgba(0, 97, 239, 0.12);
}

/* Service icon badges */
.service-icon-badge {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px;
    margin-bottom: 0.6rem;
}
.badge-teal {
    background: radial-gradient(circle, rgba(13, 148, 136, 0.24), rgba(13, 148, 136, 0.05));
    border: 1px solid rgba(13, 148, 136, 0.35);
}
.badge-green {
    background: radial-gradient(circle, rgba(101, 163, 13, 0.24), rgba(101, 163, 13, 0.05));
    border: 1px solid rgba(101, 163, 13, 0.35);
}
.badge-orange {
    background: radial-gradient(circle, rgba(234, 88, 12, 0.24), rgba(234, 88, 12, 0.05));
    border: 1px solid rgba(234, 88, 12, 0.35);
}
.badge-purple {
    background: radial-gradient(circle, rgba(124, 58, 237, 0.24), rgba(124, 58, 237, 0.05));
    border: 1px solid rgba(124, 58, 237, 0.35);
}
.badge-pink {
    background: radial-gradient(circle, rgba(219, 39, 119, 0.24), rgba(219, 39, 119, 0.05));
    border: 1px solid rgba(219, 39, 119, 0.35);
}
.badge-blue {
    background: radial-gradient(circle, rgba(0, 97, 239, 0.24), rgba(0, 97, 239, 0.05));
    border: 1px solid rgba(0, 97, 239, 0.35);
}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)
