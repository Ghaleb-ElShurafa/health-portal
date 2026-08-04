"""Injects custom CSS for a professional, eye-catching look. Paired with
the fixed dark theme in .streamlit/config.toml (so colors here are tuned to
that specific palette, not theme-adaptive)."""

import streamlit as st

CSS = """
<style>
.stApp {
    background:
        radial-gradient(circle at 15% 0%, rgba(45, 212, 191, 0.14) 0%, transparent 45%),
        radial-gradient(circle at 85% 0%, rgba(56, 130, 246, 0.12) 0%, transparent 45%),
        radial-gradient(circle at 50% 100%, rgba(249, 115, 22, 0.06) 0%, transparent 50%),
        linear-gradient(160deg, #0b1220 0%, #0e1b33 55%, #0b1220 100%);
    background-attachment: fixed;
}

/* Bordered containers (service cards) get a frosted-glass look + hover lift */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    background: rgba(255, 255, 255, 0.035);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 28px rgba(45, 212, 191, 0.18);
    border-color: rgba(45, 212, 191, 0.45) !important;
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
    font-weight: 800 !important;
}

/* Landing page hero */
.hero-subtitle {
    color: #9fb0c3;
    font-size: 1.05rem;
    margin-top: -0.5rem;
    margin-bottom: 1.25rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0e1b33 0%, #0b1220 100%);
    border-right: 1px solid rgba(45, 212, 191, 0.15);
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
    background: radial-gradient(circle, rgba(45, 212, 191, 0.28), rgba(45, 212, 191, 0.06));
    border: 1px solid rgba(45, 212, 191, 0.4);
}
.badge-green {
    background: radial-gradient(circle, rgba(132, 204, 22, 0.28), rgba(132, 204, 22, 0.06));
    border: 1px solid rgba(132, 204, 22, 0.4);
}
.badge-orange {
    background: radial-gradient(circle, rgba(249, 115, 22, 0.28), rgba(249, 115, 22, 0.06));
    border: 1px solid rgba(249, 115, 22, 0.4);
}
.badge-purple {
    background: radial-gradient(circle, rgba(167, 139, 250, 0.28), rgba(167, 139, 250, 0.06));
    border: 1px solid rgba(167, 139, 250, 0.4);
}
.badge-pink {
    background: radial-gradient(circle, rgba(236, 72, 153, 0.28), rgba(236, 72, 153, 0.06));
    border: 1px solid rgba(236, 72, 153, 0.4);
}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)
