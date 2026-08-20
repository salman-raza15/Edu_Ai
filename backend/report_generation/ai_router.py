"""
ai_router.py
------------
AI-DRIVEN request interpretation — instead of the caller passing structured
parameters (scope="course", scope_id="COURSE_AI101", ...) directly, this
module lets Claude read a natural-language request (e.g. "give me last
week's report for course AI101") and figure out the structured parameters
itself.

This is what makes the Master Agent "AI-driven": Claude is deciding WHICH
scope/report type/date-range the user is asking for, rather than a fixed
Python if/else block.

Falls back to raising a clear error if no API key is set, since routing
cannot proceed without a decision being made somehow.
"""

import os
import json
import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL_NAME = "claude-sonnet-5"

VALID_SCOPES = ["individual", "course", "cohort", "assignment"]
VALID_REPORT_TYPES = ["individual", "assignment", "course", "cohort", "weekly", "monthly", "custom"]


def interpret_request_with_ai(user_query: str, known_ids: dict) -> dict:
    """
    MAIN ENTRY POINT.
    user_query: a natural-language request, e.g. "weekly report for COURSE_AI101"
    known_ids: dict like {"students": [...], "courses": [...], "cohorts": [...]}
               used so the AI only picks IDs that actually exist in the data

    Returns a dict: {scope, scope_id, report_type, date_from, date_to}
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "AI routing requires ANTHROPIC_API_KEY to be set. "
            "No deterministic fallback is used here because routing itself "
            "must be decided by AI, per project requirements."
        )

    prompt = f"""You are a routing assistant for a student performance reporting system.

Interpret the following request and extract structured parameters.

Request: "{user_query}"

Valid students/courses/cohorts in the system:
{json.dumps(known_ids)}

Respond with ONLY a single valid JSON object with exactly these keys:
- scope: one of "individual", "course", "cohort", "assignment"
- scope_id: the matching ID from the valid list above (must exist in the list)
- report_type: one of "individual", "assignment", "course", "cohort", "weekly", "monthly", "custom"
- date_from: a date string "YYYY-MM-DD" if the request implies a date range, else null
- date_to: a date string "YYYY-MM-DD" if the request implies a date range, else null

No markdown, no explanation — JSON only."""

    response = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": MODEL_NAME,
            "max_tokens": 300,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise Exception(f"{response.status_code} - {response.text}")

    data = response.json()
    text = data["content"][0]["text"].strip()
    text = text.replace("```json", "").replace("```", "").strip()
    result = json.loads(text)

    _validate_routing_result(result, known_ids)
    return result


def _validate_routing_result(result: dict, known_ids: dict):
    """Sanity-checks the AI's routing decision before we act on it."""
    if result.get("scope") not in VALID_SCOPES:
        raise ValueError(f"AI returned invalid scope: {result.get('scope')}")
    if result.get("report_type") not in VALID_REPORT_TYPES:
        raise ValueError(f"AI returned invalid report_type: {result.get('report_type')}")

    scope = result["scope"]
    scope_id = result.get("scope_id")
    id_list_map = {"individual": "students", "course": "courses", "cohort": "cohorts", "assignment": "assignments"}
    valid_id_list = known_ids.get(id_list_map[scope], [])
    if scope_id not in valid_id_list:
        raise ValueError(f"AI returned scope_id '{scope_id}' which is not in the known {id_list_map[scope]} list")
