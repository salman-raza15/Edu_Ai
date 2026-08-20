"""Analytics engine for EduAI reports.

All core metrics are calculated deterministically from the active evaluation
DataFrame.  The AI helper remains available as an optional enhancement, but
reports never depend on an external LLM just to calculate numbers.
"""

import os
import json
import requests
import pandas as pd

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL_NAME = "claude-sonnet-5"
PASS_THRESHOLD = 40

REQUIRED_KEYS = [
    "total_students", "total_submissions", "average_percentage",
    "highest_percentage", "lowest_percentage", "pass_rate",
    "rubric_analysis", "student_breakdown", "trend", "evaluation_history",
]


def _assignment_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Return one score per student + assignment."""
    if df.empty:
        return pd.DataFrame()

    grouped = (
        df.groupby(["student_id", "student_name", "assignment_id"], as_index=False)
        .agg(total_obtained=("obtained_marks", "sum"), total_max=("max_marks", "sum"))
    )
    grouped = grouped[grouped["total_max"] > 0].copy()
    grouped["percentage"] = (grouped["total_obtained"] / grouped["total_max"] * 100).round(2)
    grouped["pass_status"] = grouped["percentage"] >= PASS_THRESHOLD
    return grouped


def _history(df: pd.DataFrame) -> list:
    """Build date-wise evaluation history used for trends and exports."""
    if df.empty:
        return []

    # Score each student/assignment first, then attach its evaluation date.
    scored = _assignment_scores(df)
    dates = (
        df[["student_id", "assignment_id", "evaluation_date"]]
        .drop_duplicates(["student_id", "assignment_id", "evaluation_date"])
    )
    scored = scored.merge(dates, on=["student_id", "assignment_id"], how="left")
    scored = scored.dropna(subset=["evaluation_date"])

    history = []
    for evaluation_date, g in scored.groupby("evaluation_date", sort=True):
        history.append({
            "evaluation_date": str(evaluation_date),
            "submissions": int(len(g)),
            "average_percentage": round(float(g["percentage"].mean()), 2),
            "highest_percentage": round(float(g["percentage"].max()), 2),
            "lowest_percentage": round(float(g["percentage"].min()), 2),
            "pass_rate": round(float(g["pass_status"].mean() * 100), 2),
        })
    return history


def calculate_analytics(df: pd.DataFrame) -> dict:
    """Calculate report analytics for an already-filtered dataset."""
    if df.empty:
        return {"error": "No data available for given filters"}

    student_totals = _assignment_scores(df)
    if student_totals.empty:
        return {"error": "No valid scored submissions are available."}

    rubric_analysis = {}
    for criteria, g in df.groupby("criteria"):
        max_total = float(g["max_marks"].sum())
        obtained_total = float(g["obtained_marks"].sum())
        rubric_analysis[str(criteria)] = round(
            obtained_total / max_total * 100, 2
        ) if max_total else 0.0

    history = _history(df)
    trend = {item["evaluation_date"]: item["average_percentage"] for item in history}

    return {
        "total_students": int(student_totals["student_id"].nunique()),
        "total_submissions": int(len(student_totals)),
        "average_percentage": round(float(student_totals["percentage"].mean()), 2),
        "highest_percentage": round(float(student_totals["percentage"].max()), 2),
        "lowest_percentage": round(float(student_totals["percentage"].min()), 2),
        "pass_rate": round(float(student_totals["pass_status"].mean() * 100), 2),
        "rubric_analysis": rubric_analysis,
        "student_breakdown": student_totals.to_dict(orient="records"),
        "trend": trend,
        "evaluation_history": history,
    }


def calculate_analytics_with_ai(df, scope_label: str) -> dict:
    """Optional AI analytics path with deterministic fallback."""
    if df.empty:
        return {"error": "No data available for given filters"}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return calculate_analytics(df)

    try:
        records = df.to_dict(orient="records")
        result = _call_claude_for_analytics(records, scope_label, api_key)
        _validate_analytics_result(result)
        # The AI response may not contain the richer history fields; fill them
        # deterministically so the UI/export contract is always complete.
        deterministic = calculate_analytics(df)
        for key in ("trend", "evaluation_history"):
            result.setdefault(key, deterministic.get(key, {} if key == "trend" else []))
        return result
    except Exception as exc:
        print(f"[WARNING] AI analytics failed ({exc}). Using deterministic analytics.")
        return calculate_analytics(df)


def _call_claude_for_analytics(records: list, scope_label: str, api_key: str) -> dict:
    prompt = f"""You are a precise data analyst. Analyze evaluation records for {scope_label}.
Use a 40% pass threshold. Calculate one submission per unique student_id + assignment_id.
Return JSON only with: total_students, total_submissions, average_percentage,
highest_percentage, lowest_percentage, pass_rate, rubric_analysis, student_breakdown.
Round percentages to 2 decimals.

Records:
{json.dumps(records, default=str)}"""
    response = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": MODEL_NAME,
            "max_tokens": 4000,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code} - {response.text}")
    text = response.json()["content"][0]["text"].strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def _validate_analytics_result(result: dict):
    missing = [key for key in REQUIRED_KEYS if key not in result and key not in ("trend", "evaluation_history")]
    if missing:
        raise ValueError(f"AI response missing required keys: {missing}")
