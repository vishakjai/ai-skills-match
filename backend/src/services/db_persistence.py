"""
Persistence layer for storing JD extractions, CV extractions,
analysis reports, and resolving/creating lightweight app users.

All writes use synchronous psycopg2 (same driver the rest of the app uses).
The module exposes simple functions – no ORM.
"""
import os
import json
import psycopg2
import psycopg2.extras
from typing import Optional, List
from datetime import datetime, timezone


def _get_conn():
    """Return a new psycopg2 connection using the project's DB URL."""
    db_url = os.environ.get("SUPABASE_URL")
    if not db_url:
        return None
    return psycopg2.connect(db_url)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def resolve_user(username: str, email: Optional[str] = None) -> Optional[str]:
    """
    Get or create an app_user by username.  Returns the user UUID (as str).
    """
    conn = _get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        # Try to find existing user
        cur.execute("SELECT id FROM app_users WHERE username = %s", (username,))
        row = cur.fetchone()
        if row:
            cur.close()
            conn.close()
            return str(row[0])

        # Create new user
        cur.execute(
            "INSERT INTO app_users (username, email) VALUES (%s, %s) RETURNING id",
            (username, email),
        )
        user_id = str(cur.fetchone()[0])
        conn.commit()
        cur.close()
        conn.close()
        return user_id
    except Exception as e:
        print(f"⚠️ DB resolve_user error: {e}")
        conn.close()
        return None


# ---------------------------------------------------------------------------
# JD Extractions
# ---------------------------------------------------------------------------

def save_jd_extraction(
    raw_text: str,
    extracted_json: dict,
    uploaded_by: Optional[str] = None,
    filename: Optional[str] = None,
    model_used: Optional[str] = None,
    is_valid: bool = True,
) -> Optional[str]:
    """Persist a JD extraction. Returns the new row UUID."""
    conn = _get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO jd_extractions (uploaded_by, raw_text, filename, extracted_json, model_used, is_valid)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                uploaded_by,
                raw_text,
                filename,
                json.dumps(extracted_json, default=str),
                model_used,
                is_valid,
            ),
        )
        jd_id = str(cur.fetchone()[0])
        conn.commit()
        cur.close()
        conn.close()
        return jd_id
    except Exception as e:
        print(f"⚠️ DB save_jd_extraction error: {e}")
        conn.close()
        return None


# ---------------------------------------------------------------------------
# CV / Resume Extractions
# ---------------------------------------------------------------------------

def save_cv_extraction(
    raw_text: str,
    extracted_json: dict,
    uploaded_by: Optional[str] = None,
    filename: Optional[str] = None,
    model_used: Optional[str] = None,
    is_valid: bool = True,
) -> Optional[str]:
    """Persist a CV extraction. Returns the new row UUID."""
    conn = _get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO cv_extractions (uploaded_by, raw_text, filename, extracted_json, model_used, is_valid)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                uploaded_by,
                raw_text,
                filename,
                json.dumps(extracted_json, default=str),
                model_used,
                is_valid,
            ),
        )
        cv_id = str(cur.fetchone()[0])
        conn.commit()
        cur.close()
        conn.close()
        return cv_id
    except Exception as e:
        print(f"⚠️ DB save_cv_extraction error: {e}")
        conn.close()
        return None


# ---------------------------------------------------------------------------
# Analysis Reports
# ---------------------------------------------------------------------------

def save_analysis_report(
    jd_id: str,
    cv_id: str,
    score: float,
    analysis_json: dict,
    run_by: Optional[str] = None,
) -> Optional[str]:
    """Persist a match/analysis report (upsert).
    Deletes any previous report for the same jd_id+cv_id pair first,
    so only the latest report is kept per CV-JD combination.
    Returns the new row UUID."""
    conn = _get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        # Remove previous report(s) for this JD+CV pair
        cur.execute(
            "DELETE FROM analysis_reports WHERE jd_id = %s AND cv_id = %s",
            (jd_id, cv_id),
        )
        deleted = cur.rowcount
        if deleted:
            print(f"🔄 Replaced {deleted} old report(s) for jd={jd_id} cv={cv_id}")
        cur.execute(
            """
            INSERT INTO analysis_reports (jd_id, cv_id, run_by, score, analysis_json)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                jd_id,
                cv_id,
                run_by,
                score,
                json.dumps(analysis_json, default=str),
            ),
        )
        report_id = str(cur.fetchone()[0])
        conn.commit()
        cur.close()
        conn.close()
        return report_id
    except Exception as e:
        print(f"⚠️ DB save_analysis_report error: {e}")
        conn.close()
        return None


# ---------------------------------------------------------------------------
# READ: JD Extractions
# ---------------------------------------------------------------------------

def list_jd_extractions(limit: int = 50, offset: int = 0) -> List[dict]:
    """Return all JD extractions, newest first."""
    conn = _get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT j.id, j.filename, j.model_used, j.is_valid, j.created_at,
                   j.extracted_json -> 'job_metadata' ->> 'title' AS job_title,
                   j.extracted_json -> 'job_metadata' ->> 'location' AS job_location,
                   u.username AS uploaded_by_name,
                   (SELECT COUNT(*) FROM analysis_reports ar WHERE ar.jd_id = j.id) AS report_count
            FROM jd_extractions j
            LEFT JOIN app_users u ON j.uploaded_by = u.id
            ORDER BY j.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"⚠️ DB list_jd_extractions error: {e}")
        conn.close()
        return []


def get_jd_extraction(jd_id: str) -> Optional[dict]:
    """Return a single JD extraction with full extracted JSON."""
    conn = _get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT j.*, u.username AS uploaded_by_name
            FROM jd_extractions j
            LEFT JOIN app_users u ON j.uploaded_by = u.id
            WHERE j.id = %s
            """,
            (jd_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"⚠️ DB get_jd_extraction error: {e}")
        conn.close()
        return None


def get_cv_extraction(cv_id: str) -> Optional[dict]:
    """Return a single CV extraction with full extracted JSON."""
    conn = _get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT c.*, u.username AS uploaded_by_name
            FROM cv_extractions c
            LEFT JOIN app_users u ON c.uploaded_by = u.id
            WHERE c.id = %s
            """,
            (cv_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"⚠️ DB get_cv_extraction error: {e}")
        conn.close()
        return None


# ---------------------------------------------------------------------------
# READ: CVs linked to a JD (via analysis_reports)
# ---------------------------------------------------------------------------

def count_cvs_for_jd(jd_id: str) -> int:
    """Return the number of distinct CVs linked to a JD via analysis_reports."""
    conn = _get_conn()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(DISTINCT cv_id) FROM analysis_reports WHERE jd_id = %s",
            (jd_id,),
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        print(f"⚠️ DB count_cvs_for_jd error: {e}")
        conn.close()
        return 0


def list_cvs_for_jd(jd_id: str) -> List[dict]:
    """Return all CVs that have been analysed against a given JD, with latest score."""
    conn = _get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT DISTINCT ON (c.id)
                   c.id AS cv_id,
                   c.filename,
                   c.extracted_json -> 'candidate_metadata' ->> 'name' AS candidate_name,
                   c.extracted_json -> 'candidate_metadata' ->> 'location' AS candidate_location,
                   c.model_used,
                   c.is_valid,
                   c.created_at AS cv_uploaded_at,
                   ar.id AS report_id,
                   ar.score,
                   ar.created_at AS analysis_date,
                   u.username AS uploaded_by_name
            FROM analysis_reports ar
            JOIN cv_extractions c ON ar.cv_id = c.id
            LEFT JOIN app_users u ON c.uploaded_by = u.id
            WHERE ar.jd_id = %s
            ORDER BY c.id, ar.created_at DESC
            """,
            (jd_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"⚠️ DB list_cvs_for_jd error: {e}")
        conn.close()
        return []


# ---------------------------------------------------------------------------
# READ: Analysis Reports for a JD
# ---------------------------------------------------------------------------

def list_reports_for_jd(jd_id: str) -> List[dict]:
    """Return all analysis reports for a given JD, newest first."""
    conn = _get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT ar.id AS report_id,
                   ar.score,
                   ar.created_at AS analysis_date,
                   ar.analysis_json,
                   c.id AS cv_id,
                   c.filename AS cv_filename,
                   c.extracted_json -> 'candidate_metadata' ->> 'name' AS candidate_name,
                   ru.username AS run_by_name
            FROM analysis_reports ar
            JOIN cv_extractions c ON ar.cv_id = c.id
            LEFT JOIN app_users ru ON ar.run_by = ru.id
            WHERE ar.jd_id = %s
            ORDER BY ar.created_at DESC
            """,
            (jd_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"⚠️ DB list_reports_for_jd error: {e}")
        conn.close()
        return []


def get_report_detail(report_id: str) -> Optional[dict]:
    """Return a single analysis report with full JSON."""
    conn = _get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT ar.*,
                   c.filename AS cv_filename,
                   c.extracted_json -> 'candidate_metadata' ->> 'name' AS candidate_name,
                   j.extracted_json -> 'job_metadata' ->> 'title' AS job_title,
                   j.filename AS jd_filename,
                   ru.username AS run_by_name
            FROM analysis_reports ar
            JOIN cv_extractions c ON ar.cv_id = c.id
            JOIN jd_extractions j ON ar.jd_id = j.id
            LEFT JOIN app_users ru ON ar.run_by = ru.id
            WHERE ar.id = %s
            """,
            (report_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"⚠️ DB get_report_detail error: {e}")
        conn.close()
        return None


# ---------------------------------------------------------------------------
# WRITE: Update / Delete
# ---------------------------------------------------------------------------

def update_jd_extracted_json(jd_id: str, extracted_json: dict) -> bool:
    """Replace the full extracted_json for a JD extraction."""
    conn = _get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE jd_extractions SET extracted_json = %s WHERE id = %s",
            (json.dumps(extracted_json, default=str), jd_id),
        )
        conn.commit()
        updated = cur.rowcount > 0
        cur.close()
        conn.close()
        return updated
    except Exception as e:
        print(f"⚠️ DB update_jd_extracted_json error: {e}")
        conn.close()
        return False


def update_jd_title(jd_id: str, new_title: str) -> bool:
    """Update the job_metadata.title inside the extracted_json JSONB."""
    conn = _get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE jd_extractions
            SET extracted_json = jsonb_set(extracted_json, '{job_metadata,title}', %s::jsonb)
            WHERE id = %s
            """,
            (json.dumps(new_title), jd_id),
        )
        conn.commit()
        updated = cur.rowcount > 0
        cur.close()
        conn.close()
        return updated
    except Exception as e:
        print(f"⚠️ DB update_jd_title error: {e}")
        conn.close()
        return False


def delete_jd_extraction(jd_id: str) -> bool:
    """
    Delete a JD and all associated data:
      - All analysis_reports for this JD (via CASCADE)
      - All cv_extractions that were linked to this JD
      - The JD itself
    """
    conn = _get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()

        # 0. Verify JD exists
        cur.execute("SELECT id FROM jd_extractions WHERE id = %s", (jd_id,))
        if not cur.fetchone():
            print(f"⚠️ delete_jd_extraction: JD {jd_id} not found")
            cur.close()
            conn.close()
            return False

        # 1. Collect ALL CV IDs linked to this JD (before cascade removes reports)
        cur.execute(
            "SELECT DISTINCT cv_id FROM analysis_reports WHERE jd_id = %s",
            (jd_id,),
        )
        cv_ids = [row[0] for row in cur.fetchall()]
        print(f"🗑️ delete_jd: JD={jd_id}, associated CVs={len(cv_ids)}")

        # 2. Delete the JD — CASCADE auto-deletes its analysis_reports
        cur.execute("DELETE FROM jd_extractions WHERE id = %s", (jd_id,))
        jd_deleted = cur.rowcount > 0
        print(f"🗑️ JD row deleted: {jd_deleted}")

        # 3. Delete associated CVs
        #    Their reports for THIS JD are already gone (cascade).
        #    Reports for OTHER JDs will also cascade-delete when the CV is removed.
        if cv_ids:
            cur.execute(
                "DELETE FROM cv_extractions WHERE id = ANY(%s::uuid[])",
                ([str(c) for c in cv_ids],),
            )
            print(f"🗑️ Deleted {cur.rowcount} associated CVs")

        conn.commit()
        cur.close()
        conn.close()
        return jd_deleted
    except Exception as e:
        print(f"⚠️ DB delete_jd_extraction error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        conn.close()
        return False


def delete_cv_extraction(cv_id: str) -> bool:
    """Delete a CV and its linked analysis reports."""
    conn = _get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM analysis_reports WHERE cv_id = %s", (cv_id,))
        cur.execute("DELETE FROM cv_extractions WHERE id = %s", (cv_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        conn.close()
        return deleted
    except Exception as e:
        print(f"⚠️ DB delete_cv_extraction error: {e}")
        conn.rollback()
        conn.close()
        return False
