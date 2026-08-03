"""Minimal Gemini API client using plain HTTP (via `requests`) rather than
Google's official SDK. The official SDK depends on google-auth, which
depends on `cryptography` — a package that needs a Rust toolchain this
environment doesn't have (same issue we hit with Google OAuth). Gemini API
keys are simple bearer keys (not OAuth), so a raw REST call works fine
without any of that.
"""

import base64
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-flash-lite-latest"
# Tried in order — if the primary model is having its own outage (this has
# happened: gemini-flash-latest had a multi-hour 503 "high demand" outage
# while gemini-flash-lite-latest kept working fine), fall through to the
# next one instead of failing outright.
MODEL_FALLBACKS = [MODEL, "gemini-2.0-flash", "gemini-flash-latest"]
API_BASE = "https://generativelanguage.googleapis.com/v1beta"

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 4


class GeminiUnavailableError(Exception):
    """Raised when Gemini is unreachable or overloaded after retries.
    Callers should catch this and show a friendly "try again" message
    rather than a raw error.
    """


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


def _post(body, timeout):
    last_error = None
    for model in MODEL_FALLBACKS:
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.post(
                    f"{API_BASE}/models/{model}:generateContent",
                    headers={"x-goog-api-key": _api_key(), "Content-Type": "application/json"},
                    json=body,
                    timeout=timeout,
                )
                if resp.status_code in RETRYABLE_STATUS_CODES:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    time.sleep(min(2 ** attempt, 10))
                    continue
                if not resp.ok:
                    # Not retryable (bad API key, malformed request, etc.) —
                    # retrying across every model/attempt would just waste
                    # over a minute before failing the same way every time.
                    raise GeminiUnavailableError(f"Gemini API error HTTP {resp.status_code}: {resp.text[:200]}")
                return resp.json()
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                time.sleep(min(2 ** attempt, 10))
        # Every retry on this model was retryable-but-failed — try the next
        # model in the fallback list before giving up entirely.
    raise GeminiUnavailableError(
        f"Gemini API unavailable after trying {len(MODEL_FALLBACKS)} model(s): {last_error}"
    )


def generate(system_prompt, messages, max_tokens=500):
    """messages: list of {"role": "user"|"assistant", "content": str}.
    Returns the model's reply text. Raises GeminiUnavailableError on
    persistent failure.
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

    data = _post(body, timeout=30)
    return data["candidates"][0]["content"]["parts"][0]["text"]


def extract_from_document(prompt_text, file_bytes, mime_type, response_schema, max_tokens=1500):
    """Sends a single user turn containing text + an inline file (image or
    PDF) and asks for a JSON reply matching response_schema (Gemini's
    OpenAPI-subset schema format). Returns the parsed JSON (dict). Raises
    GeminiUnavailableError on persistent failure.
    """
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt_text},
                    {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(file_bytes).decode()}},
                ],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }

    data = _post(body, timeout=60)
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)
