"""
schema_mapper.py
-----------------
Makes the module SCHEMA-INDEPENDENT: any instructor's CSV/PDF, with any
column names, can be used — an AI reads the actual column headers and a
few sample rows, and figures out which column corresponds to which
required field (student_id, criteria, marks, etc.).

This removes the earlier limitation where the system only worked if the
uploaded file used our exact assumed column names.

Design (safety-first, matching the project's data-validation philosophy):
  1. If the columns ALREADY match our required names exactly, skip the AI
     call entirely (fast path, no cost, no dependency on API availability).
  2. Otherwise, ask the AI to map the actual columns to our required schema.
  3. VALIDATE the AI's mapping — if any required field could not be
     confidently mapped, raise a clear error rather than guessing wrong
     and silently producing an incorrect report.
  4. If no API key is available, fall back to a small built-in alias
     dictionary for common naming variations (e.g. "roll_no" -> student_id).
     If that still can't cover every required field, a clear error is
     raised asking the user to either configure an AI key or rename columns.
"""

import os
import json
import requests

REQUIRED_FIELDS = [
    "student_id", "student_name", "course_id", "cohort_id",
    "assignment_id", "criteria", "max_marks", "obtained_marks", "evaluation_date"
]

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL_NAME = "claude-sonnet-5"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODEL_NAME = "gemini-3.6-flash"

# Last-resort fallback (used only if no API key is configured at all)
COMMON_ALIASES = {
    "student_id": ["student_id", "roll_number", "roll_no", "rollno", "id", "sid", "student id"],
    "student_name": ["student_name", "full_name", "name", "student name"],
    "course_id": ["course_id", "class_code", "course", "class", "course id"],
    "cohort_id": ["cohort_id", "batch", "cohort", "group"],
    "assignment_id": ["assignment_id", "task_id", "assignment", "task", "task id"],
    "criteria": ["criteria", "rubric_item", "rubric_name", "rubric", "parameter"],
    "max_marks": ["max_marks", "total_points", "max_points", "total_marks", "max"],
    "obtained_marks": ["obtained_marks", "points_earned", "score", "marks_obtained", "obtained"],
    "evaluation_date": ["evaluation_date", "date_graded", "date", "graded_on"],
}


def map_columns_to_schema(df) -> dict:
    """
    MAIN ENTRY POINT.
    Given a raw DataFrame with unknown column names, returns a mapping dict:
        {"student_id": "<actual column name in df>", ...}
    Raises ValueError with a clear message if any required field cannot be
    confidently identified.
    """
    normalized_cols = {c.strip().lower().replace(" ", "_"): c for c in df.columns}

    # Fast path: columns already match exactly
    if all(field in normalized_cols for field in REQUIRED_FIELDS):
        return {field: normalized_cols[field] for field in REQUIRED_FIELDS}

    gemini_key = os.environ.get("GEMINI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if gemini_key:
        try:
            return _map_with_ai(df, "gemini", gemini_key)
        except Exception as e:
            print(f"[WARNING] Gemini schema mapping failed ({e}). Trying next option.")

    if anthropic_key:
        try:
            return _map_with_ai(df, "claude", anthropic_key)
        except Exception as e:
            print(f"[WARNING] Claude schema mapping failed ({e}). Trying alias fallback.")

    return _map_with_aliases(df)


def _build_mapping_prompt(df) -> str:
    columns = list(df.columns)
    sample_rows = df.head(3).to_dict(orient="records")
    return f"""You are mapping a raw spreadsheet's columns to a required schema for an
academic reporting system.

Actual columns in the uploaded file: {json.dumps(columns)}
Sample rows: {json.dumps(sample_rows, default=str)}

Required schema fields and their meaning:
- student_id: a unique identifier for the student (roll number, ID, etc.)
- student_name: the student's full name
- course_id: identifier for the course/class
- cohort_id: identifier for the batch/cohort/group
- assignment_id: identifier for the assignment/task
- criteria: the rubric criterion name (e.g. "Code Quality", "Logic")
- max_marks: the maximum possible marks for that criterion
- obtained_marks: the marks the student actually received for that criterion
- evaluation_date: the date the evaluation was recorded

For EACH required schema field, identify which actual column (from the list above)
corresponds to it, based on the column name and the sample data. If no column
in the file clearly corresponds to a required field, use null for that field —
do NOT guess a column that doesn't actually match.

Respond with ONLY a single valid JSON object with exactly these keys:
student_id, student_name, course_id, cohort_id, assignment_id, criteria,
max_marks, obtained_marks, evaluation_date
Each value must be either an exact column name from the actual columns list, or null.
No markdown, no explanation — JSON only."""


def _map_with_ai(df, provider: str, api_key: str) -> dict:
    prompt = _build_mapping_prompt(df)

    if provider == "gemini":
        url = GEMINI_API_URL.format(model=GEMINI_MODEL_NAME)
        response = requests.post(
            url,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0},
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise Exception(f"{response.status_code} - {response.text}")
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:  # claude
        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": CLAUDE_MODEL_NAME,
                "max_tokens": 500,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise Exception(f"{response.status_code} - {response.text}")
        text = response.json()["content"][0]["text"]

    text = text.strip().replace("```json", "").replace("```", "").strip()
    mapping = json.loads(text)

    _validate_mapping(mapping, df.columns)
    return mapping


def _map_with_aliases(df) -> dict:
    """Last-resort fallback when no AI key is available: matches common naming variations."""
    normalized_cols = {c.strip().lower().replace(" ", "_"): c for c in df.columns}
    mapping = {}

    for field, aliases in COMMON_ALIASES.items():
        found = None
        for alias in aliases:
            alias_norm = alias.replace(" ", "_")
            if alias_norm in normalized_cols:
                found = normalized_cols[alias_norm]
                break
        mapping[field] = found

    _validate_mapping(mapping, df.columns, source="alias fallback (no AI key configured)")
    return mapping


def _validate_mapping(mapping: dict, actual_columns, source="AI"):
    """Ensures every required field was mapped to a real column before we trust it."""
    missing = [f for f in REQUIRED_FIELDS if not mapping.get(f)]
    if missing:
        raise ValueError(
            f"Could not identify a column for these required fields: {missing} "
            f"(via {source}). Actual columns in file: {list(actual_columns)}. "
            f"Please rename the relevant column(s) or ensure an AI API key "
            f"(GEMINI_API_KEY or ANTHROPIC_API_KEY) is configured for automatic mapping."
        )

    invalid = [f for f, col in mapping.items() if col not in actual_columns]
    if invalid:
        raise ValueError(
            f"Mapping (via {source}) referenced column(s) that don't exist in the "
            f"file: {[mapping[f] for f in invalid]}"
        )


def apply_mapping(df, mapping: dict):
    """Renames the DataFrame's columns according to the mapping, producing our standard schema."""
    reverse_mapping = {actual_col: field for field, actual_col in mapping.items()}
    df = df.rename(columns=reverse_mapping)
    return df[REQUIRED_FIELDS]