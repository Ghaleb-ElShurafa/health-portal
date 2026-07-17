# Personal Doctor

A Streamlit app that lets a user log bloodwork results over time, flags
out-of-range values against standard clinical reference ranges, and uses the
Claude API to generate a plain-language summary and general diet/lifestyle
suggestions — always flagging when a result should be discussed with a doctor.

**⚠️ Not medical advice.** This is an educational/portfolio project. It does
not diagnose or treat any condition, and "consult a doctor" flags are always
computed with local rule-based logic (`reference_ranges.py`), independent of
the AI — the model is only responsible for the explanatory text, never for
deciding what's urgent.

## Features

- Manual entry of a lipid panel, glucose/HbA1c, and blood pressure
- Rule-based flagging against standard adult reference ranges (NCEP ATP III
  cholesterol guidelines, ADA glucose/A1c thresholds, AHA blood pressure
  categories)
- AI-generated plain-language summary and lifestyle suggestions (Claude API)
- Trend charts across entries stored locally in SQLite

## Setup

```
pip install -r requirements.txt
cp .env.example .env        # then edit .env and add your own Anthropic API key
streamlit run app.py
```

Without an API key configured, the app still works — it shows the rule-based
results and flags, just without the AI-generated summary.

## Project structure

```
app.py                 Streamlit UI
reference_ranges.py     reference ranges + flagging rules
ai_advice.py             Claude API prompt + call
db.py                    local SQLite storage for entry history
```

## Scope note

This is a working prototype demonstrating the full pipeline (data entry →
rule-based analysis → AI explanation → trend visualization) using data you
enter yourself. It intentionally does **not** implement file uploads, user
accounts, or storage of real patient records — turning this into something
a healthcare company could deploy with real patient data would require
HIPAA/PIPEDA-compliant infrastructure (encryption at rest, access controls,
audit logging, BAAs with any third-party APIs used) that's out of scope here.
