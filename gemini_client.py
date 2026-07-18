"""Minimal Gemini API client using plain HTTP (via `requests`) rather than
Google's official SDK. The official SDK depends on google-auth, which
depends on `cryptography` — a package that needs a Rust toolchain this
environment doesn't have (same issue we hit with Google OAuth). Gemini API
keys are simple bearer keys (not OAuth), so a raw REST call works fine
without any of that.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-flash-latest"
API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        import streamlit as st

        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None


def is_configured():
    return bool(_api_key())


def generate(system_prompt, messages, max_tokens=500):
    """messages: list of {"role": "user"|"assistant", "content": str}.
    Returns the model's reply text, or raises requests.HTTPError on failure.
    """
    contents = [
        {
            "role": "model" if m["role"] == "assistant" else "user",
            "parts": [{"text": m["content"]}],
        }
        for m in messages
    ]
    body = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            # Without this, the model spends most of maxOutputTokens on an
            # invisible internal reasoning pass and the visible reply gets
            # cut off short.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    resp = requests.post(
        f"{API_BASE}/models/{MODEL}:generateContent",
        headers={"x-goog-api-key": _api_key(), "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]
