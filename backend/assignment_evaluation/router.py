from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import base64

from backend.database import get_db
from backend import models


from backend.assignment_evaluation.evaluation_service import (
    process_assignment_evaluation,
    process_assignment_rubric_generation,
)


router = APIRouter(
    prefix="/assignment-evaluation",
    tags=["AI Assignment Evaluation"],
)


# ============================================================
# HEALTH
# ============================================================

@router.get("/health")
def assignment_evaluation_health():

    return {
        "status": "healthy",
        "module": "AI Assignment Evaluation",
    }


# ============================================================
# GENERATE RUBRIC FROM ASSIGNMENT
# ============================================================

@router.post("/generate-rubric")
async def generate_assignment_rubric_endpoint(
    assignment_file: UploadFile = File(...),
):

    try:

        result = await process_assignment_rubric_generation(
            assignment_file=assignment_file,
        )


        # ----------------------------------------------------
        # If the service returned a structured AI error,
        # convert it into a clean HTTP 400 response.
        # ----------------------------------------------------

        rubric = (
            result.get("rubric")
            if isinstance(result, dict)
            else None
        )


        if (
            isinstance(rubric, dict)
            and rubric.get("error")
        ):

            detail = (
                rubric.get("details")
                or rubric.get("message")
                or rubric.get("error")
                or "Rubric generation failed."
            )


            raise HTTPException(
                status_code=400,
                detail=str(detail),
            )


        return result


    except HTTPException:

        raise


    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI rubric generation failed: "
                f"{str(error)}"
            ),
        ) from error


# ============================================================
# EVALUATE ASSIGNMENT
# ============================================================

@router.post("/evaluate")
async def evaluate_assignment_endpoint(
    assignment_file: UploadFile = File(...),
    rubric_file: UploadFile = File(...),
    submission_file: UploadFile = File(...),
):

    try:

        return await process_assignment_evaluation(
            assignment_file=assignment_file,
            rubric_file=rubric_file,
            submission_file=submission_file,
        )


    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Assignment evaluation failed: "
                f"{str(error)}"
            ),
        ) from error

# ============================================================
# SAVE ZIP BATCH RESULTS FOR REPORT GENERATION
# ============================================================

class BatchEvaluationRow(BaseModel):
    student_id: str
    student_name: str
    course_id: str
    cohort_id: str
    assignment_id: str
    criteria: str
    max_marks: float
    obtained_marks: float
    evaluation_date: str
    remarks: Optional[str] = None


class BatchEvaluationSaveRequest(BaseModel):
    source_filename: Optional[str] = None
    xlsx_filename: str
    xlsx_base64: str
    rows: List[BatchEvaluationRow]


@router.post("/batch-results/save")
def save_batch_results_for_reporting(
    payload: BatchEvaluationSaveRequest,
    db: Session = Depends(get_db),
):
    if not payload.rows:
        raise HTTPException(status_code=400, detail="No evaluation rows were provided.")

    try:
        xlsx_bytes = base64.b64decode(payload.xlsx_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid XLSX payload.") from exc

    first = payload.rows[0]
    batch = models.EvaluationBatch(
        assignment_id=first.assignment_id,
        course_id=first.course_id,
        cohort_id=first.cohort_id,
        source_filename=payload.source_filename,
        xlsx_filename=payload.xlsx_filename,
        xlsx_data=xlsx_bytes,
    )
    db.add(batch)
    db.flush()

    stored_rows = []
    for row in payload.rows:
        record = models.EvaluationResult(
            batch_id=batch.id,
            student_id=row.student_id,
            student_name=row.student_name,
            course_id=row.course_id,
            cohort_id=row.cohort_id,
            assignment_id=row.assignment_id,
            criteria=row.criteria,
            max_marks=row.max_marks,
            obtained_marks=row.obtained_marks,
            evaluation_date=row.evaluation_date,
            remarks=row.remarks,
        )
        db.add(record)
        stored_rows.append(row.model_dump())

    db.commit()

    # Make these exact DB rows the live input for Report Generation immediately.
    try:
        from backend.report_generation.router import activate_evaluation_rows
        activate_evaluation_rows(
            stored_rows,
            filename=payload.xlsx_filename,
            batch_id=batch.id,
        )
    except Exception:
        # Persistence succeeded; Report Generation can still restore latest DB data on restart.
        pass

    return {
        "message": "Batch evaluation XLSX and report-ready rows saved successfully.",
        "batch_id": batch.id,
        "rows": len(stored_rows),
        "xlsx_filename": payload.xlsx_filename,
    }