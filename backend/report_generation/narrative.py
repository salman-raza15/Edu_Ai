"""
narrative.py
------------
This module converts analytics numbers into a human-readable summary text.

Two modes are supported:
1. LLM mode (Claude API) — used automatically if an API key is available
   in the ANTHROPIC_API_KEY environment variable. temperature=0 is used
   so the same input always produces the same (or near-identical) text.
2. Rule-based fallback — used automatically if no API key is set, so the
   system keeps working (with 100% deterministic text) even without one.
"""

import os
import json
import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL_NAME = "claude-sonnet-5"

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODEL_NAME = "gemini-3.6-flash"


def build_narrative(analytics: dict, scope_label: str) -> str:
    """
    MAIN ENTRY POINT.
    Provider priority: Gemini (if GEMINI_API_KEY is set) -> Claude (if
    ANTHROPIC_API_KEY is set) -> rule-based fallback (always available).
    This lets the module keep working even if one provider's credits run out.
    """
    if "error" in analytics:
        return "No data is available for this scope."

    gemini_key = os.environ.get("GEMINI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if gemini_key:
        try:
            return _build_narrative_with_gemini(analytics, scope_label, gemini_key)
        except Exception as e:
            print(f"[WARNING] Gemini API call failed ({e}). Trying next option.")

    if anthropic_key:
        try:
            return _build_narrative_with_claude(analytics, scope_label, anthropic_key)
        except Exception as e:
            print(f"[WARNING] Claude API call failed ({e}). Falling back to rule-based summary.")

    return _build_narrative_rule_based(analytics, scope_label)


def _build_prompt(analytics: dict, scope_label: str) -> str:
    return f"""You are writing a short performance summary for an academic report.

Scope: {scope_label}
Analytics data (JSON): {json.dumps(analytics, default=str)}

Write a professional 3-4 sentence summary that covers:
- Overall performance level (based on average_percentage)
- Highest and lowest scores
- Pass rate
- The weakest rubric criteria (from rubric_analysis) and a brief suggestion
- The performance trend, if trend data is present

Rules:
- Use ONLY the numbers given above. Do not invent or estimate any numbers.
- Do not use markdown formatting.
- Output only the summary paragraph, nothing else."""


def _build_narrative_with_gemini(analytics: dict, scope_label: str, api_key: str) -> str:
    """Generates the narrative using the Gemini API (free tier). temperature=0 for consistency."""
    url = GEMINI_API_URL.format(model=GEMINI_MODEL_NAME)
    response = requests.post(
        url,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        json={
            "contents": [{"parts": [{"text": _build_prompt(analytics, scope_label)}]}],
            "generationConfig": {"temperature": 0},
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise Exception(f"{response.status_code} - {response.text}")

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _build_narrative_with_claude(analytics: dict, scope_label: str, api_key: str) -> str:
    """Generates the narrative using the Claude API. temperature=0 for consistency."""
    response = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": CLAUDE_MODEL_NAME,
            "max_tokens": 300,
            "temperature": 0,
            "messages": [{"role": "user", "content": _build_prompt(analytics, scope_label)}],
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise Exception(f"{response.status_code} - {response.text}")

    data = response.json()
    return data["content"][0]["text"].strip()


def _build_narrative_rule_based(analytics: dict, scope_label: str) -> str:
    """Deterministic, template-based summary. Used when no API key is available."""
    avg = analytics["average_percentage"]
    highest = analytics["highest_percentage"]
    lowest = analytics["lowest_percentage"]
    pass_rate = analytics["pass_rate"]
    total = analytics["total_students"]

    if avg >= 75:
        level = "strong"
    elif avg >= 50:
        level = "satisfactory"
    else:
        level = "concerning"

    rubric = analytics.get("rubric_analysis", {})
    weakest = min(rubric, key=rubric.get) if rubric else None

    text = (
        f"{scope_label} performance overview: data for {total} student(s) was processed. "
        f"The average score was {avg}%, indicating overall {level} performance. "
        f"The highest score recorded was {highest}%, and the lowest was {lowest}%. "
        f"The pass rate was {pass_rate}%."
    )

    if weakest:
        text += (
            f" Rubric-wise analysis shows that students are weakest in the "
            f"'{weakest}' criteria overall ({rubric[weakest]}% average) — "
            f"extra focus could be given to this area."
        )

    if "trend" in analytics:
        dates = list(analytics["trend"].keys())
        vals = list(analytics["trend"].values())
        if len(vals) >= 2:
            direction = "an improving" if vals[-1] > vals[0] else "a declining"
            text += f" Performance shows {direction} trend over time."

    return text
