"""
database.py
-----------
Handles all database operations using SQLite.

SQLite is a single-file, serverless database — perfect for a standalone
project like this one. No separate database server needs to be installed
or run; everything lives inside one file: eduai_reports.db

This module replaces the old JSON-file cache (report_cache/ folder) with
a proper database table.
"""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "eduai_reports.db")


def get_connection():
    """Opens a connection to the SQLite database file (creates it if it doesn't exist)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """
    Creates the 'reports' table if it doesn't already exist.
    Call this once when the application starts.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            cache_key TEXT PRIMARY KEY,
            scope TEXT NOT NULL,
            scope_id TEXT NOT NULL,
            report_type TEXT NOT NULL,
            date_from TEXT,
            date_to TEXT,
            narrative_text TEXT,
            analytics_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_report(cache_key: str):
    """
    Looks up a report by its cache_key.
    Returns a dict if found, or None if it doesn't exist yet.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE cache_key = ?", (cache_key,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "cache_key": row["cache_key"],
        "scope": row["scope"],
        "scope_id": row["scope_id"],
        "report_type": row["report_type"],
        "date_from": row["date_from"],
        "date_to": row["date_to"],
        "narrative_text": row["narrative_text"],
        "analytics": json.loads(row["analytics_json"]),
        "created_at": row["created_at"],
    }


def save_report(report: dict):
    """Saves (or overwrites) a report record in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO reports
        (cache_key, scope, scope_id, report_type, date_from, date_to, narrative_text, analytics_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report["cache_key"],
        report["scope"],
        report["scope_id"],
        report["report_type"],
        report.get("date_from"),
        report.get("date_to"),
        report["narrative_text"],
        json.dumps(report["analytics"], default=str),
    ))
    conn.commit()
    conn.close()


def list_all_reports():
    """Returns a summary list of every report saved so far (useful for a history view)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cache_key, scope, scope_id, report_type, date_from, date_to, created_at
        FROM reports ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_reports_by_scope_id(scope: str, scope_id: str):
    """
    Looks up all reports matching a given scope_id (e.g. all reports for
    student 'STU101', or all reports for course 'COURSE_AI101').
    Returns a list of full report dicts (same shape as get_report()).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM reports WHERE scope = ? AND scope_id = ? ORDER BY created_at DESC",
        (scope, scope_id),
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "cache_key": row["cache_key"],
            "scope": row["scope"],
            "scope_id": row["scope_id"],
            "report_type": row["report_type"],
            "date_from": row["date_from"],
            "date_to": row["date_to"],
            "narrative_text": row["narrative_text"],
            "analytics": json.loads(row["analytics_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def update_report_fields(cache_key: str, fields: dict):
    """
    Partially updates a saved report. Only the keys present in `fields`
    are changed; everything else stays as-is.

    Supported keys: narrative_text, analytics (a dict — will be stored as JSON),
    report_type, date_from, date_to.

    Returns the updated report dict, or None if no report with this cache_key exists.
    """
    existing = get_report(cache_key)
    if existing is None:
        return None

    narrative_text = fields.get("narrative_text", existing["narrative_text"])
    analytics = fields.get("analytics", existing["analytics"])
    report_type = fields.get("report_type", existing["report_type"])
    date_from = fields.get("date_from", existing["date_from"])
    date_to = fields.get("date_to", existing["date_to"])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE reports
        SET narrative_text = ?, analytics_json = ?, report_type = ?, date_from = ?, date_to = ?
        WHERE cache_key = ?
    """, (
        narrative_text,
        json.dumps(analytics, default=str),
        report_type,
        date_from,
        date_to,
        cache_key,
    ))
    conn.commit()
    conn.close()

    return get_report(cache_key)


def delete_report(cache_key: str):
    """Deletes a specific report from the database. Returns True if a row was deleted."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports WHERE cache_key = ?", (cache_key,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted