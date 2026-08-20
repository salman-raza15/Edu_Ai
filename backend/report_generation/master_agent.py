"""
master_agent.py
----------------
MASTER AGENT: Looks at the incoming request and decides which scope
(individual/course/cohort) applies, filters the data according to that
scope, and routes it to the correct sub-agent.

CONSISTENCY: Every generated report is saved to a local JSON "cache"
(in the real project this will be a Database). If the same request comes
in again, instead of generating a new report, the previously saved report
is returned — this guarantees "same report, same result, every time."
"""

import hashlib
from datetime import date, timedelta
import pandas as pd

from .analytics import calculate_analytics, calculate_analytics_with_ai
from .narrative import build_narrative
from . import database


def _make_cache_key(scope, scope_id, report_type, date_from, date_to):
    """Builds a unique, deterministic ID from the request parameters."""
    raw = f"{scope}|{scope_id}|{report_type}|{date_from}|{date_to}"
    return hashlib.md5(raw.encode()).hexdigest()


def _auto_date_range(report_type: str, df=None):
    """
    Computes the default date window for "weekly" / "monthly" reports when
    the caller didn't explicitly supply date_from/date_to:
      - weekly:  Monday of the current week -> today
      - monthly: 1st of the current month -> today
    Returns (date_from, date_to) as "YYYY-MM-DD" strings, or (None, None)
    for any other report_type (no auto-restriction applied).
    """
    # Prefer the latest date in the active dataset so historical/demo data
    # still produces a useful weekly/monthly report.
    today = date.today()
    if df is not None and not df.empty and "evaluation_date" in df.columns:
        try:
            latest = pd.to_datetime(df["evaluation_date"], errors="coerce").max()
            if pd.notna(latest):
                today = latest.date()
        except Exception:
            pass
    if report_type == "weekly":
        start = today - timedelta(days=today.weekday())  # Monday of this week
        return start.isoformat(), today.isoformat()
    if report_type == "monthly":
        start = today.replace(day=1)
        return start.isoformat(), today.isoformat()
    return None, None


def _filter_by_date(df, date_from, date_to):
    if date_from:
        df = df[df["evaluation_date"] >= date_from]
    if date_to:
        df = df[df["evaluation_date"] <= date_to]
    return df


# --------------------------- SUB-AGENTS ---------------------------

def individual_agent(df: pd.DataFrame, scope_id: str) -> pd.DataFrame:
    """Filters data for one specific student."""
    return df[df["student_id"] == scope_id]


def course_agent(df: pd.DataFrame, scope_id: str) -> pd.DataFrame:
    """Filters data for all students in one specific course."""
    return df[df["course_id"] == scope_id]


def cohort_agent(df: pd.DataFrame, scope_id: str) -> pd.DataFrame:
    """Filters data for all students in one specific cohort/batch."""
    return df[df["cohort_id"] == scope_id]


def assignment_agent(df: pd.DataFrame, scope_id: str) -> pd.DataFrame:
    """Filters data for all students' records on one specific assignment."""
    return df[df["assignment_id"] == scope_id]


SCOPE_AGENTS = {
    "individual": individual_agent,
    "course": course_agent,
    "cohort": cohort_agent,
    "assignment": assignment_agent,
}


# --------------------------- MASTER AGENT ---------------------------

def generate_report(
    df: pd.DataFrame,
    scope: str,
    scope_id: str,
    report_type: str = "custom",
    date_from: str = None,
    date_to: str = None,
    save: bool = True,
    force_regenerate: bool = False,
):
    """
    MAIN ENTRY POINT.

    scope: "individual" | "course" | "cohort" | "assignment"
    scope_id: e.g. "STU101" or "COURSE_AI101" or "COHORT_A" or "ASG_1"
    report_type: "individual" | "assignment" | "course" | "cohort" |
                 "weekly" | "monthly" | "custom"
    date_from / date_to: "YYYY-MM-DD" (for weekly/monthly/custom reports).
        If both are left as None and report_type is "weekly" or "monthly",
        they're auto-filled to the current week (Mon->today) or current
        month (1st->today) respectively. Pass explicit dates to override.
    save: True -> saved to cache/DB; False -> returned only (download-only)
    force_regenerate: set True to bypass the cache (useful for testing)

    Returns: a dict containing analytics, narrative_text, and metadata
    """
    if scope not in SCOPE_AGENTS:
        raise ValueError(f"Invalid scope: {scope}. Options: {list(SCOPE_AGENTS.keys())}")

    # Weekly/Monthly reports default to the current week/month when the
    # caller doesn't explicitly pass date_from/date_to — so selecting
    # report_type="weekly" actually restricts the data, instead of being
    # just a label with no effect.
    if date_from is None and date_to is None:
        auto_from, auto_to = _auto_date_range(report_type, df)
        date_from = date_from or auto_from
        date_to = date_to or auto_to

    cache_key = _make_cache_key(scope, scope_id, report_type, date_from, date_to)

    # ---- CONSISTENCY CHECK: has this exact report already been generated? ----
    if not force_regenerate:
        cached = database.get_report(cache_key)
        if cached is not None:
            cached["_from_cache"] = True
            return cached

    # ---- Generate a new report ----
    sub_agent_fn = SCOPE_AGENTS[scope]
    filtered_df = sub_agent_fn(df, scope_id)
    filtered_df = _filter_by_date(filtered_df, date_from, date_to)

    if filtered_df.empty:
        return {"error": f"No data found for '{scope_id}' ({scope})."}

    analytics = calculate_analytics(filtered_df)
    scope_label = f"{scope.capitalize()} ({scope_id})"
    narrative_text = build_narrative(analytics, scope_label)

    result = {
        "cache_key": cache_key,
        "scope": scope,
        "scope_id": scope_id,
        "report_type": report_type,
        "date_from": date_from,
        "date_to": date_to,
        "analytics": analytics,
        "narrative_text": narrative_text,
        "_from_cache": False,
    }

    # ---- Save it, or just return for direct download ----
    if save:
        database.save_report(result)

    return result


# --------------------------- FULLY AI-DRIVEN MODE ---------------------------
# The functions below make the Master Agent, sub-agents, and analytics all
# AI-driven end-to-end, per the instructor's requirement that every part of
# the pipeline (not just the narrative text) be handled by AI.
#
# NOTE ON CONSISTENCY: this mode does NOT guarantee identical results on
# every run. Only the narrative text generation used temperature=0 for
# determinism in the original design; here, the AI is also doing routing
# and arithmetic, which introduces some variability. This trade-off was
# explicitly requested and is documented in the project documentation.

from .ai_router import interpret_request_with_ai


def generate_report_ai(
    df: pd.DataFrame,
    user_query: str,
    known_ids: dict,
    save: bool = True,
    force_regenerate: bool = False,
):
    """
    FULLY AI-DRIVEN ENTRY POINT.

    Instead of structured parameters, this takes a natural-language request
    and lets AI: (1) interpret it into scope/report_type/date-range,
    (2) calculate analytics from the filtered data, and (3) write the
    narrative summary. All three AI calls use temperature=0, but exact
    reproducibility is not guaranteed the way the deterministic pipeline
    guarantees it.

    user_query: natural-language request, e.g. "weekly report for COURSE_AI101"
    known_ids: {"students": [...], "courses": [...], "cohorts": [...]}
    """
    # Step 1: AI decides scope/report_type/date-range from the natural-language request
    routing = interpret_request_with_ai(user_query, known_ids)
    scope = routing["scope"]
    scope_id = routing["scope_id"]
    report_type = routing["report_type"]
    date_from = routing.get("date_from")
    date_to = routing.get("date_to")

    cache_key = _make_cache_key(scope, scope_id, report_type, date_from, date_to)

    if not force_regenerate:
        cached = database.get_report(cache_key)
        if cached is not None:
            cached["_from_cache"] = True
            cached["_routing"] = routing
            return cached

    # Step 2: filter data for the decided scope (still deterministic filtering,
    # since this is just selecting rows, not "processing" them)
    sub_agent_fn = SCOPE_AGENTS[scope]
    filtered_df = sub_agent_fn(df, scope_id)
    filtered_df = _filter_by_date(filtered_df, date_from, date_to)

    if filtered_df.empty:
        return {"error": f"No data found for '{scope_id}' ({scope})."}

    # Step 3: AI calculates the analytics (average, pass rate, rubric analysis, etc.)
    scope_label = f"{scope.capitalize()} ({scope_id})"
    analytics = calculate_analytics_with_ai(filtered_df, scope_label)

    # Step 4: AI writes the narrative summary
    narrative_text = build_narrative(analytics, scope_label)

    result = {
        "cache_key": cache_key,
        "scope": scope,
        "scope_id": scope_id,
        "report_type": report_type,
        "date_from": date_from,
        "date_to": date_to,
        "analytics": analytics,
        "narrative_text": narrative_text,
        "_from_cache": False,
        "_routing": routing,
    }

    if save:
        database.save_report(result)

    return result
