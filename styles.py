"""Injects custom CSS for the "Calm Drift" look (light mode) or its dark
counterpart. The Streamlit theme in .streamlit/config.toml is fixed to
light, so dark mode is done entirely via CSS override -- Streamlit's own
theme config can't change per-user/per-session. One real limitation: canvas-
rendered widgets (st.dataframe's grid) bake in the light theme's colors at
render time and won't fully adapt.
"""

import streamlit as st

LIGHT = {
    "bg": (
        "radial-gradient(circle at 18% 12%, rgba(147, 168, 224, 0.30) 0%, transparent 45%),"
        "radial-gradient(circle at 85% 18%, rgba(196, 167, 231, 0.26) 0%, transparent 45%),"
        "radial-gradient(circle at 50% 105%, rgba(251, 191, 165, 0.16) 0%, transparent 55%),"
        "#f9f4f2"
    ),
    "card_bg": "rgba(255, 255, 255, 0.55)",
    "card_border_hover": "rgba(0, 97, 239, 0.35)",
    "card_shadow_hover": "rgba(0, 97, 239, 0.14)",
    "accent": "#0061ef",
    "accent_soft": "rgba(0, 97, 239, 0.30)",
    "accent_shadow": "rgba(0, 97, 239, 0.20)",
    "title_start": "#2d2c2b",
    "title_end": "#0061ef",
    "text_primary": "#2d2c2b",
    "text_secondary": "#756e68",
    "sidebar_start": "#fffdfb",
    "sidebar_end": "#f5efec",
    "sidebar_border": "rgba(0, 97, 239, 0.12)",
    "input_bg": "#fffdfb",
    "input_border": "rgba(45, 44, 43, 0.2)",
    "expander_bg": "rgba(255, 255, 255, 0.4)",
    "expander_border": "rgba(45, 44, 43, 0.12)",
    "tab_inactive": "#756e68",
    "popover_bg": "#fffdfb",
}

DARK = {
    "bg": (
        "radial-gradient(circle at 18% 10%, rgba(91, 157, 255, 0.14) 0%, transparent 45%),"
        "radial-gradient(circle at 85% 20%, rgba(167, 139, 250, 0.12) 0%, transparent 45%),"
        "radial-gradient(circle at 50% 105%, rgba(91, 157, 255, 0.08) 0%, transparent 55%),"
        "#0d1117"
    ),
    "card_bg": "rgba(255, 255, 255, 0.04)",
    "card_border_hover": "rgba(91, 157, 255, 0.35)",
    "card_shadow_hover": "rgba(91, 157, 255, 0.18)",
    "accent": "#5b9dff",
    "accent_soft": "rgba(91, 157, 255, 0.35)",
    "accent_shadow": "rgba(91, 157, 255, 0.25)",
    "title_start": "#e8e6e3",
    "title_end": "#5b9dff",
    "text_primary": "#e8e6e3",
    "text_secondary": "#9a978f",
    "sidebar_start": "#11151c",
    "sidebar_end": "#0b0e13",
    "sidebar_border": "rgba(91, 157, 255, 0.15)",
    "input_bg": "#1a1f2b",
    "input_border": "rgba(255, 255, 255, 0.15)",
    "expander_bg": "rgba(255, 255, 255, 0.03)",
    "expander_border": "rgba(255, 255, 255, 0.1)",
    "tab_inactive": "#9a978f",
    "popover_bg": "#151a24",
}


def _css(c):
    return f"""
<style>
.stApp {{
    background: {c["bg"]};
    background-attachment: fixed;
}}

/* Bordered containers (service cards) get a soft frosted look + hover lift */
div[data-testid="stVerticalBlock"]:has(> div[class*="st-key-open_"]) {{
    border-radius: 16px !important;
    background: {c["card_bg"]};
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    position: relative;
    cursor: pointer;
}}
div[data-testid="stVerticalBlock"]:has(> div[class*="st-key-open_"]):hover {{
    transform: translateY(-3px);
    box-shadow: 0 12px 28px {c["card_shadow_hover"]};
    border-color: {c["card_border_hover"]} !important;
}}
/* The "Open" button becomes an invisible full-card click target so the whole
   card is clickable, not just a small button at the bottom. Both the wrapper
   AND the button itself need "position: absolute; inset: 0" -- percentage
   height on the button alone doesn't reliably cascade through Streamlit's
   own layout, which left only a ~40px strip near the top of each card
   actually clickable. */
div[data-testid="stVerticalBlock"] > div[class*="st-key-open_"] {{
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
    z-index: 5;
}}
div[data-testid="stVerticalBlock"] > div[class*="st-key-open_"] button {{
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
    /* iOS Safari doesn't reliably dispatch tap events to fully transparent
       (opacity: 0) elements -- staying fully opaque but visually blank
       (transparent fill/text) keeps it invisible while staying tappable
       everywhere, including in stricter automated/accessibility click paths. */
    opacity: 1;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: transparent !important;
    cursor: pointer;
}}

/* Borderless "back" links: plain clickable text, no button box */
div[class*="st-key-back_link"] button {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: {c["accent"]} !important;
    padding: 0.2rem 0 !important;
    font-weight: 600;
}}
div[class*="st-key-back_link"] button:hover {{
    text-decoration: underline;
    transform: none !important;
    box-shadow: none !important;
}}

/* Search bar: minimal underline style instead of a boxed input + separate button */
div[class*="st-key-site_search_query"] input {{
    border: none !important;
    border-bottom: 2px solid {c["accent_soft"]} !important;
    border-radius: 0 !important;
    background: transparent !important;
    color: {c["text_primary"]} !important;
    padding-left: 0.2rem !important;
    transition: border-color 0.15s ease;
}}
div[class*="st-key-site_search_query"] input:focus {{
    border-bottom-color: {c["accent"]} !important;
    box-shadow: none !important;
}}
div[class*="st-key-search_submit"] button {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: {c["accent"]} !important;
    font-size: 1.3rem !important;
}}
div[class*="st-key-search_submit"] button:hover {{
    transform: scale(1.15) !important;
    box-shadow: none !important;
}}

/* Buttons: rounded, accent-colored hover */
.stButton > button, .stFormSubmitButton > button, .stLinkButton > a {{
    border-radius: 10px !important;
    transition: transform 0.1s ease, box-shadow 0.15s ease;
    background: {c["input_bg"]};
    color: {c["text_primary"]};
    border: 1px solid {c["input_border"]};
}}
.stButton > button:hover, .stFormSubmitButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 12px {c["accent_shadow"]};
}}

/* Title styling */
h1 {{
    background: linear-gradient(90deg, {c["title_start"]} 0%, {c["title_end"]} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
    font-weight: 800 !important;
}}
h2, h3, h4, h5 {{ color: {c["text_primary"]} !important; }}

/* Landing page hero */
.hero-subtitle {{
    color: {c["text_secondary"]};
    font-size: 1.05rem;
    margin-top: -0.5rem;
    margin-bottom: 1.25rem;
}}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {c["sidebar_start"]} 0%, {c["sidebar_end"]} 100%) !important;
    border-right: 1px solid {c["sidebar_border"]} !important;
}}

/* Body text, captions, and widget labels */
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
[data-testid="stCaptionContainer"], [data-testid="stWidgetLabel"] p,
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
    color: {c["text_primary"]};
}}
[data-testid="stCaptionContainer"] {{ color: {c["text_secondary"]} !important; }}

/* Native form controls: text/number/date inputs, textareas, selectboxes */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input, [data-testid="stDateInput"] input,
[data-baseweb="select"] > div, [data-baseweb="input"] {{
    background-color: {c["input_bg"]} !important;
    color: {c["text_primary"]} !important;
    border-color: {c["input_border"]} !important;
}}

/* Secondary (non-custom-styled) buttons, e.g. admin dashboard actions */
[data-testid="stBaseButton-secondary"] {{
    background-color: {c["input_bg"]} !important;
    color: {c["text_primary"]} !important;
    border-color: {c["input_border"]} !important;
}}

/* Expanders */
[data-testid="stExpander"] {{
    background: {c["expander_bg"]} !important;
    border-color: {c["expander_border"]} !important;
    border-radius: 10px !important;
}}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab"] {{ color: {c["tab_inactive"]} !important; }}
[data-testid="stTabs"] [aria-selected="true"] {{ color: {c["accent"]} !important; }}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ background-color: {c["accent"]} !important; }}

/* Popovers (Menu, Messages) */
[data-testid="stPopoverBody"] {{
    background: {c["popover_bg"]} !important;
    border-color: {c["input_border"]} !important;
}}

/* Service icon badges */
.service-icon-badge {{
    width: 60px;
    height: 60px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px;
    margin-bottom: 0.6rem;
}}
.badge-teal {{
    background: radial-gradient(circle, rgba(13, 148, 136, 0.24), rgba(13, 148, 136, 0.05));
    border: 1px solid rgba(13, 148, 136, 0.35);
}}
.badge-green {{
    background: radial-gradient(circle, rgba(101, 163, 13, 0.24), rgba(101, 163, 13, 0.05));
    border: 1px solid rgba(101, 163, 13, 0.35);
}}
.badge-orange {{
    background: radial-gradient(circle, rgba(234, 88, 12, 0.24), rgba(234, 88, 12, 0.05));
    border: 1px solid rgba(234, 88, 12, 0.35);
}}
.badge-purple {{
    background: radial-gradient(circle, rgba(124, 58, 237, 0.24), rgba(124, 58, 237, 0.05));
    border: 1px solid rgba(124, 58, 237, 0.35);
}}
.badge-pink {{
    background: radial-gradient(circle, rgba(219, 39, 119, 0.24), rgba(219, 39, 119, 0.05));
    border: 1px solid rgba(219, 39, 119, 0.35);
}}
.badge-blue {{
    background: radial-gradient(circle, rgba(0, 97, 239, 0.24), rgba(0, 97, 239, 0.05));
    border: 1px solid rgba(0, 97, 239, 0.35);
}}
</style>
"""


def inject(dark_mode=False):
    st.markdown(_css(DARK if dark_mode else LIGHT), unsafe_allow_html=True)
