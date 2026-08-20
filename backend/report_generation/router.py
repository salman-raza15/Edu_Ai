import io
import os
import base64
import tempfile
import json
import re
import requests
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd

from backend.database import SessionLocal
from backend import models

from .loaders import load_data, load_data_from_stream
from .database import (
    init_db,
    get_report,
    list_all_reports,
    get_reports_by_scope_id,
    update_report_fields,
    delete_report,
)
from .master_agent import generate_report
from .exporter import export_pdf, export_excel, export_csv


router = APIRouter(
    prefix="/report-generation",
    tags=["Report Generation"],
)


# ============================================================
# PATHS / ACTIVE DATASET
# ============================================================

MODULE_DIR = os.path.dirname(__file__)

DATA_DIR = os.path.join(
    MODULE_DIR,
    "data",
)

os.makedirs(DATA_DIR, exist_ok=True)

DATA_PATH = os.path.join(
    DATA_DIR,
    "sample_results.csv",
)

ACTIVE_DATASET_META = os.path.join(
    DATA_DIR,
    "active_dataset.json",
)

DOWNLOAD_DIR = os.path.join(
    MODULE_DIR,
    "downloads",
)

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


ALLOWED_UPLOAD_EXTENSIONS = (
    ".csv",
    ".pdf",
    ".xlsx",
    ".docx",
    ".pptx",
    ".zip",
)




def _evaluation_batch_dataframe(batch_id: int):
    """Load one persisted AI Evaluation batch from PostgreSQL by ID."""
    db = SessionLocal()
    try:
        batch = (
            db.query(models.EvaluationBatch)
            .filter(models.EvaluationBatch.id == batch_id)
            .first()
        )
        if batch is None:
            return None, None

        records = (
            db.query(models.EvaluationResult)
            .filter(models.EvaluationResult.batch_id == batch.id)
            .order_by(models.EvaluationResult.id.asc())
            .all()
        )
        if not records:
            return None, None

        rows = [{
            "student_id": r.student_id,
            "student_name": r.student_name,
            "course_id": r.course_id,
            "cohort_id": r.cohort_id,
            "assignment_id": r.assignment_id,
            "criteria": r.criteria,
            "max_marks": r.max_marks,
            "obtained_marks": r.obtained_marks,
            "evaluation_date": r.evaluation_date,
        } for r in records]
        return pd.DataFrame(rows), {
            "filename": batch.xlsx_filename,
            "rows": len(rows),
            "persistent": True,
            "source": "AI Evaluation database",
            "batch_id": batch.id,
            "assignment_id": batch.assignment_id,
            "course_id": batch.course_id,
            "cohort_id": batch.cohort_id,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
        }
    finally:
        db.close()


def _latest_evaluation_dataframe():
    """Load the newest persisted AI Evaluation batch from PostgreSQL."""
    db = SessionLocal()
    try:
        latest = (
            db.query(models.EvaluationBatch)
            .order_by(models.EvaluationBatch.created_at.desc(), models.EvaluationBatch.id.desc())
            .first()
        )
        latest_id = latest.id if latest is not None else None
    finally:
        db.close()

    if latest_id is None:
        return None, None
    return _evaluation_batch_dataframe(latest_id)


def activate_evaluation_rows(rows, filename="AI_Evaluation_Results.xlsx", batch_id=None):
    """Immediately switch Report Generation to the rows just saved by AI Evaluation."""
    global _df, _data_source
    frame = pd.DataFrame(rows)
    required = [
        "student_id", "student_name", "course_id", "cohort_id",
        "assignment_id", "criteria", "max_marks", "obtained_marks", "evaluation_date"
    ]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"Saved evaluation rows are missing report fields: {missing}")
    _df = frame[required].copy()
    _data_source = {
        "filename": filename,
        "rows": len(_df),
        "persistent": True,
        "source": "AI Evaluation database",
        "batch_id": batch_id,
    }
    return _data_source

# ============================================================
# ACTIVE DATASET LOADING
# ============================================================

def _find_active_dataset():
    """
    Return the persisted uploaded dataset path if one exists.

    The file is stored as:
        backend/report_generation/data/active_dataset.<ext>

    This makes the uploaded dataset survive a FastAPI restart.
    """

    try:
        if os.path.exists(ACTIVE_DATASET_META):
            with open(
                ACTIVE_DATASET_META,
                "r",
                encoding="utf-8",
            ) as f:
                metadata = json.load(f)

            stored_path = metadata.get(
                "path"
            )

            if (
                stored_path
                and os.path.isfile(stored_path)
            ):
                return stored_path

    except Exception:
        pass

    # Fallback: look directly for active_dataset.*
    try:
        for filename in os.listdir(DATA_DIR):
            if filename.startswith(
                "active_dataset."
            ):
                candidate = os.path.join(
                    DATA_DIR,
                    filename,
                )

                if os.path.isfile(candidate):
                    return candidate
    except Exception:
        pass

    return None


def _load_startup_dataset():
    """Prefer latest AI Evaluation DB batch; otherwise use uploaded/sample data."""

    try:
        evaluation_df, evaluation_source = _latest_evaluation_dataframe()
        if evaluation_df is not None and not evaluation_df.empty:
            return evaluation_df, evaluation_source
    except Exception:
        pass

    active_path = _find_active_dataset()

    if active_path:
        try:
            dataframe = load_data(
                active_path
            )

            if dataframe is not None and not dataframe.empty:
                return dataframe, {
                    "filename": os.path.basename(
                        active_path
                    ),
                    "rows": len(dataframe),
                    "persistent": True,
                }

        except Exception:
            # If the persisted file is damaged or incompatible,
            # safely fall back to the original sample dataset.
            pass

    dataframe = load_data(
        DATA_PATH
    )

    return dataframe, {
        "filename": (
            os.path.basename(DATA_PATH)
            + " (sample/demo data)"
        ),
        "rows": len(dataframe),
        "persistent": False,
    }


init_db()

_df, _data_source = _load_startup_dataset()


# ============================================================
# PERSIST UPLOADED DATASET
# ============================================================

def _persist_uploaded_dataset(
    filename: str,
    contents: bytes,
):
    """
    Save the uploaded source file to disk so the active dataset
    survives a FastAPI restart.

    Only one active dataset is kept at a time.
    """

    original_ext = os.path.splitext(
        filename or ""
    )[1].lower()

    if not original_ext:
        original_ext = ".csv"

    active_path = os.path.join(
        DATA_DIR,
        "active_dataset" + original_ext,
    )

    # Remove an older active dataset with a different extension.
    try:
        for existing in os.listdir(DATA_DIR):
            if (
                existing.startswith(
                    "active_dataset."
                )
                and existing != os.path.basename(
                    active_path
                )
            ):
                existing_path = os.path.join(
                    DATA_DIR,
                    existing,
                )

                if os.path.isfile(existing_path):
                    os.remove(existing_path)
    except Exception:
        pass

    with open(
        active_path,
        "wb",
    ) as f:
        f.write(contents)

    with open(
        ACTIVE_DATASET_META,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "original_filename": filename,
                "path": active_path,
            },
            f,
            indent=2,
        )

    return active_path


# ============================================================
# HEALTH
# ============================================================

@router.get("/health")
def report_health():
    return {
        "status": "healthy",
        "rows": len(_df),
        "data_source": _data_source,
    }


# ============================================================
# DATA UPLOAD
# ============================================================

@router.post("/data/upload")
async def upload_data(
    file: UploadFile = File(...)
):
    global _df, _data_source

    filename = file.filename or ""

    ext = os.path.splitext(
        filename
    )[1].lower()

    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Allowed: "
                f"{', '.join(ALLOWED_UPLOAD_EXTENSIONS)}"
            ),
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    # First validate the upload in memory.
    try:
        new_df, warnings = load_data_from_stream(
            filename,
            io.BytesIO(contents),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if new_df is None or new_df.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded file contained "
                "no usable rows."
            ),
        )

    # Persist ONLY after validation succeeds.
    try:
        active_path = _persist_uploaded_dataset(
            filename,
            contents,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "The dataset was valid but could not "
                f"be saved for persistence: {exc}"
            ),
        ) from exc

    _df = new_df

    _data_source = {
        "filename": filename,
        "rows": len(_df),
        "persistent": True,
        "path": active_path,
    }

    return {
        "message": (
            f"Loaded {len(_df)} row(s) "
            f"from '{filename}'. "
            "This is now the active dataset and "
            "will remain active after backend restart."
        ),
        "rows": len(_df),
        "students": (
            _df["student_id"].nunique()
            if "student_id" in _df.columns
            else 0
        ),
        "courses": sorted(
            _df["course_id"]
            .unique()
            .tolist()
        ) if "course_id" in _df.columns else [],
        "cohorts": sorted(
            _df["cohort_id"]
            .unique()
            .tolist()
        ) if "cohort_id" in _df.columns else [],
        "warnings": warnings,
        "persistent": True,
    }


# ============================================================
# DATA STATUS
# ============================================================

@router.get("/data/status")
def data_status():
    return _data_source


@router.get("/data/evaluation-batches")
def list_evaluation_batches():
    """Return all saved AI Evaluation XLSX batches for report selection."""
    db = SessionLocal()
    try:
        batches = (
            db.query(models.EvaluationBatch)
            .order_by(models.EvaluationBatch.created_at.desc(), models.EvaluationBatch.id.desc())
            .all()
        )

        result = []
        for batch in batches:
            row_count = (
                db.query(models.EvaluationResult)
                .filter(models.EvaluationResult.batch_id == batch.id)
                .count()
            )
            result.append({
                "batch_id": batch.id,
                "xlsx_filename": batch.xlsx_filename,
                "source_filename": batch.source_filename,
                "assignment_id": batch.assignment_id,
                "course_id": batch.course_id,
                "cohort_id": batch.cohort_id,
                "rows": row_count,
                "created_at": batch.created_at.isoformat() if batch.created_at else None,
            })
        return result
    finally:
        db.close()


@router.post("/data/evaluation-batches/{batch_id}/activate")
def activate_evaluation_batch(batch_id: int):
    """Make the selected saved AI Evaluation batch the active report dataset."""
    global _df, _data_source

    frame, source = _evaluation_batch_dataframe(batch_id)
    if frame is None or frame.empty or source is None:
        raise HTTPException(status_code=404, detail="Evaluation batch not found or contains no report rows.")

    _df = frame.copy()
    _data_source = source
    return {
        "message": f"'{source.get('filename', 'Evaluation batch')}' is now the active report dataset.",
        **source,
    }


# ============================================================
# DATA OPTIONS
# ============================================================

@router.get("/data/options")
def data_options():

    students = []

    if (
        "student_id" in _df.columns
        and "student_name" in _df.columns
    ):
        students = (
            _df[
                [
                    "student_id",
                    "student_name",
                ]
            ]
            .drop_duplicates()
            .sort_values("student_id")
            .to_dict(
                orient="records"
            )
        )

    return {
        "individual": students,

        "course": sorted(
            _df["course_id"]
            .unique()
            .tolist()
        ) if "course_id" in _df.columns else [],

        "cohort": sorted(
            _df["cohort_id"]
            .unique()
            .tolist()
        ) if "cohort_id" in _df.columns else [],

        "assignment": sorted(
            _df["assignment_id"]
            .unique()
            .tolist()
        ) if "assignment_id" in _df.columns else [],
    }


# ============================================================
# LIVE ANALYTICS
# ============================================================

@router.get("/analytics")
def analytics(
    scope: str,
    scope_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    if scope not in (
        "individual",
        "course",
        "cohort",
        "assignment",
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid analytics scope.",
        )

    fn = {
        "individual": (
            lambda d, i:
            d[d["student_id"] == i]
        ),
        "course": (
            lambda d, i:
            d[d["course_id"] == i]
        ),
        "cohort": (
            lambda d, i:
            d[d["cohort_id"] == i]
        ),
        "assignment": (
            lambda d, i:
            d[d["assignment_id"] == i]
        ),
    }[scope]

    filtered = fn(
        _df,
        scope_id,
    )

    if date_from:
        filtered = filtered[
            filtered["evaluation_date"]
            >= date_from
        ]

    if date_to:
        filtered = filtered[
            filtered["evaluation_date"]
            <= date_to
        ]

    from .analytics import calculate_analytics

    result = calculate_analytics(
        filtered
    )

    if "error" in result:
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )

    return {
        "scope": scope,
        "scope_id": scope_id,
        "date_from": date_from,
        "date_to": date_to,
        "analytics": result,
    }


# ============================================================
# ANALYTICS HISTORY
# ============================================================

@router.get("/analytics/history")
def analytics_history(
    scope: Optional[str] = None,
    scope_id: Optional[str] = None,
):
    from .analytics import calculate_analytics

    filtered = _df

    if scope and scope_id:

        if scope == "individual":
            filtered = filtered[
                filtered["student_id"]
                == scope_id
            ]

        elif scope == "course":
            filtered = filtered[
                filtered["course_id"]
                == scope_id
            ]

        elif scope == "cohort":
            filtered = filtered[
                filtered["cohort_id"]
                == scope_id
            ]

        elif scope == "assignment":
            filtered = filtered[
                filtered["assignment_id"]
                == scope_id
            ]

        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid analytics scope.",
            )

    result = calculate_analytics(
        filtered
    )

    if "error" in result:
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )

    return {
        "scope": scope,
        "scope_id": scope_id,
        "history": result.get(
            "evaluation_history",
            [],
        ),
    }


# ============================================================
# CREATE REPORT REQUEST
# ============================================================

class CreateReportRequest(BaseModel):
    scope: str
    scope_id: str
    report_type: str = "custom"
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    save: bool = True

    letterhead_mode: str = "default"
    letterhead_name: Optional[str] = None
    letterhead_data: Optional[str] = None


# ============================================================
# UPDATE REPORT REQUEST
# ============================================================

class UpdateReportRequest(BaseModel):
    regenerate: bool = False
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    report_type: Optional[str] = None
    narrative_text: Optional[str] = None
    analytics: Optional[dict] = None


class SendReportEmailRequest(BaseModel):
    recipient_email: str


# ============================================================
# CREATE REPORT
# ============================================================

@router.post("/reports")
def create_report(
    request: CreateReportRequest
):

    if request.scope not in (
        "individual",
        "course",
        "cohort",
        "assignment",
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid report scope.",
        )

    if request.report_type not in (
        "individual",
        "assignment",
        "course",
        "cohort",
        "weekly",
        "monthly",
        "custom",
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid report type.",
        )

    result = generate_report(
        _df,
        scope=request.scope,
        scope_id=request.scope_id,
        report_type=request.report_type,
        date_from=request.date_from,
        date_to=request.date_to,
        save=request.save,
    )

    if "error" in result:
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )

    return result


# ============================================================
# GENERATE AND DOWNLOAD REPORT
# ============================================================

@router.post("/reports/download")
def generate_and_download_report(
    request: CreateReportRequest,
    format: str = "pdf",
):

    if format not in (
        "pdf",
        "excel",
        "csv",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "format must be "
                "'pdf', 'excel', or 'csv'"
            ),
        )

    result = generate_report(
        _df,
        scope=request.scope,
        scope_id=request.scope_id,
        report_type=request.report_type,
        date_from=request.date_from,
        date_to=request.date_to,
        save=request.save,
    )

    if "error" in result:
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )

    return _export_response(
        result,
        format,
        f"report_{result['cache_key']}",
        letterhead_mode=request.letterhead_mode,
        letterhead_name=request.letterhead_name,
        letterhead_data=request.letterhead_data,
    )


# ============================================================
# GET ALL REPORTS
# ============================================================

@router.get("/reports")
def read_all_reports():
    return list_all_reports()


# ============================================================
# GET REPORTS BY STUDENT
# ============================================================

@router.get("/reports/student/{student_id}")
def read_reports_by_student(
    student_id: str
):

    reports = get_reports_by_scope_id(
        "individual",
        student_id,
    )

    if not reports:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No saved reports found "
                f"for student '{student_id}'"
            ),
        )

    return reports


# ============================================================
# GET REPORT BY ID
# ============================================================

@router.get("/reports/{cache_key}")
def read_report_by_id(
    cache_key: str
):

    report = get_report(
        cache_key
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No report found with ID "
                f"'{cache_key}'"
            ),
        )

    return report


# ============================================================
# UPDATE REPORT
# ============================================================

@router.put("/reports/{cache_key}")
def update_report(
    cache_key: str,
    request: UpdateReportRequest,
):

    existing = get_report(
        cache_key
    )

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No report found with ID "
                f"'{cache_key}'"
            ),
        )

    if request.regenerate:

        result = generate_report(
            _df,

            scope=existing["scope"],

            scope_id=existing["scope_id"],

            report_type=(
                request.report_type
                or existing["report_type"]
            ),

            date_from=(
                request.date_from
                if request.date_from is not None
                else existing["date_from"]
            ),

            date_to=(
                request.date_to
                if request.date_to is not None
                else existing["date_to"]
            ),

            save=True,

            force_regenerate=True,
        )

        if "error" in result:
            raise HTTPException(
                status_code=404,
                detail=result["error"],
            )

        return result

    fields = {}

    for field in (
        "narrative_text",
        "analytics",
        "report_type",
        "date_from",
        "date_to",
    ):

        value = getattr(
            request,
            field,
        )

        if value is not None:
            fields[field] = value

    if not fields:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide regenerate=true "
                "or at least one field to edit."
            ),
        )

    return update_report_fields(
        cache_key,
        fields,
    )


# ============================================================
# DELETE REPORT
# ============================================================

@router.delete("/reports/{cache_key}")
def delete_report_endpoint(
    cache_key: str
):

    if not delete_report(
        cache_key
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                f"No report found with ID "
                f"'{cache_key}'"
            ),
        )

    return {
        "message": (
            f"Report '{cache_key}' "
            "deleted successfully."
        )
    }


# ============================================================
# DOWNLOAD SAVED REPORT
# ============================================================

@router.post(
    "/reports/{cache_key}/send-email"
)
def send_report_email(
    cache_key: str,
    request: SendReportEmailRequest,
):
    """
    Generate the selected report as PDF and send it to the
    configured n8n webhook.

    Environment variable required:
        N8N_REPORT_EMAIL_WEBHOOK_URL

    n8n receives multipart form-data:
        recipient_email
        report_id
        filename
        report_type
        scope
        scope_id
        file (PDF binary)
    """

    recipient = request.recipient_email.strip()

    if not re.fullmatch(
        r"[^\s@]+@[^\s@]+\.[^\s@]+",
        recipient,
    ):
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid recipient email address.",
        )

    webhook_url = os.getenv(
        "N8N_REPORT_EMAIL_WEBHOOK_URL"
    )

    if not webhook_url:
        raise HTTPException(
            status_code=503,
            detail=(
                "Email service is not configured. "
                "Set N8N_REPORT_EMAIL_WEBHOOK_URL "
                "in the backend environment."
            ),
        )

    report = get_report(cache_key)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No report found with ID '{cache_key}'"
            ),
        )

    pdf_path = None

    try:
        pdf_path = export_pdf(
            report,
            DOWNLOAD_DIR,
            f"report_{cache_key}_email",
        )

        with open(pdf_path, "rb") as pdf_file:
            files = {
                "file": (
                    os.path.basename(pdf_path),
                    pdf_file,
                    "application/pdf",
                )
            }

            data = {
                "recipient_email": recipient,
                "report_id": cache_key,
                "filename": os.path.basename(pdf_path),
                "report_type": str(
                    report.get("report_type", "")
                ),
                "scope": str(
                    report.get("scope", "")
                ),
                "scope_id": str(
                    report.get("scope_id", "")
                ),
            }

            try:
                response = requests.post(
                    webhook_url,
                    data=data,
                    files=files,
                    timeout=60,
                )
            except requests.RequestException as exc:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Could not reach the n8n email workflow: "
                        f"{exc}"
                    ),
                ) from exc

        if not 200 <= response.status_code < 300:
            raise HTTPException(
                status_code=502,
                detail=(
                    "n8n rejected the email request. "
                    f"HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                ),
            )

        return {
            "message": (
                f"Report has been sent to {recipient}."
            ),
            "recipient_email": recipient,
            "report_id": cache_key,
            "workflow_status": "accepted",
        }

    finally:
        if (
            pdf_path
            and os.path.exists(pdf_path)
        ):
            try:
                os.remove(pdf_path)
            except OSError:
                pass


@router.get(
    "/reports/{cache_key}/download"
)
def download_report(
    cache_key: str,
    format: str = "pdf",
):

    report = get_report(
        cache_key
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No report found with ID "
                f"'{cache_key}'"
            ),
        )

    if format not in (
        "pdf",
        "excel",
        "csv",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "format must be "
                "'pdf', 'excel', or 'csv'"
            ),
        )

    return _export_response(
        report,
        format,
        f"report_{cache_key}",
    )


# ============================================================
# DOWNLOAD WITH LETTERHEAD
# ============================================================

@router.post(
    "/reports/{cache_key}/download"
)
def download_report_with_letterhead(
    cache_key: str,
    request: dict,
    format: str = "pdf",
):

    report = get_report(
        cache_key
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No report found with ID "
                f"'{cache_key}'"
            ),
        )

    if format != "pdf":
        raise HTTPException(
            status_code=400,
            detail=(
                "This endpoint accepts "
                "PDF downloads only."
            ),
        )

    return _export_response(
        report,
        "pdf",
        f"report_{cache_key}",
        letterhead_mode=request.get(
            "letterhead_mode",
            "default",
        ),
        letterhead_name=request.get(
            "letterhead_name"
        ),
        letterhead_data=request.get(
            "letterhead_data"
        ),
    )


# ============================================================
# EXPORT RESPONSE
# ============================================================

def _export_response(
    report: dict,
    format: str,
    filename_prefix: str,
    letterhead_mode: str = "default",
    letterhead_name: Optional[str] = None,
    letterhead_data: Optional[str] = None,
):

    # ========================================================
    # PDF
    # ========================================================

    if format == "pdf":

        custom_path = None

        if (
            letterhead_mode == "custom"
            and letterhead_data
        ):

            try:

                raw = base64.b64decode(
                    letterhead_data
                )

                suffix = os.path.splitext(
                    letterhead_name or ".png"
                )[1].lower()

                if suffix not in (
                    ".pdf",
                    ".png",
                    ".jpg",
                    ".jpeg",
                ):
                    raise ValueError(
                        "Letterhead must be "
                        "PDF, PNG, JPG, or JPEG."
                    )

                fd, custom_path = tempfile.mkstemp(
                    prefix="eduai_letterhead_",
                    suffix=suffix,
                )

                with os.fdopen(
                    fd,
                    "wb",
                ) as f:
                    f.write(raw)

                # ------------------------------------------------
                # PDF LETTERHEAD
                # ------------------------------------------------

                if suffix == ".pdf":

                    try:

                        try:
                            import pymupdf as fitz
                        except ImportError:
                            import fitz

                        with fitz.open(
                            custom_path
                        ) as pdf_doc:

                            if pdf_doc.page_count < 1:
                                raise ValueError(
                                    "The uploaded letterhead "
                                    "PDF has no pages."
                                )

                            page = pdf_doc.load_page(0)

                            rect = page.rect

                            if (
                                rect.width <= 0
                                or rect.height <= 0
                            ):
                                raise ValueError(
                                    "The uploaded letterhead "
                                    "PDF has an invalid "
                                    "page size."
                                )

                            scale = 200 / 72

                            pix = page.get_pixmap(
                                matrix=fitz.Matrix(
                                    scale,
                                    scale,
                                ),
                                alpha=False,
                                colorspace=fitz.csRGB,
                            )

                            png_path = (
                                custom_path[:-4]
                                + "_first_page.png"
                            )

                            pix.save(
                                png_path
                            )

                        os.remove(
                            custom_path
                        )

                        custom_path = png_path

                    except Exception as exc:

                        if (
                            custom_path
                            and os.path.exists(
                                custom_path
                            )
                        ):
                            try:
                                os.remove(
                                    custom_path
                                )
                            except OSError:
                                pass

                        raise ValueError(
                            "Could not read the uploaded "
                            "PDF letterhead. "
                            "Please make sure the PDF "
                            "opens normally and contains "
                            "at least one page. "
                            f"Details: {exc}"
                        ) from exc

            except Exception as exc:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid custom letterhead: "
                        f"{exc}"
                    ),
                ) from exc

        try:

            path = export_pdf(
                report,
                DOWNLOAD_DIR,
                filename_prefix,
                letterhead_path=custom_path,
            )

        finally:

            if (
                custom_path
                and os.path.exists(
                    custom_path
                )
            ):
                try:
                    os.remove(
                        custom_path
                    )
                except OSError:
                    pass

        media_type = "application/pdf"

    # ========================================================
    # EXCEL
    # ========================================================

    elif format == "excel":

        path = export_excel(
            report,
            DOWNLOAD_DIR,
            filename_prefix,
        )

        media_type = (
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )

    # ========================================================
    # CSV
    # ========================================================

    elif format == "csv":

        path = export_csv(
            report,
            DOWNLOAD_DIR,
            filename_prefix,
        )

        media_type = "text/csv"

    else:

        raise HTTPException(
            status_code=400,
            detail=(
                "format must be "
                "'pdf', 'excel', or 'csv'"
            ),
        )

    return FileResponse(
        path,
        media_type=media_type,
        filename=os.path.basename(path),
    )