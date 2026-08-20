from fastapi import UploadFile

from backend.assignment_evaluation.file_service import extract_text
from backend.assignment_evaluation.evaluation_agent import (
    evaluate_assignment,
    generate_assignment_rubric,
)


# ============================================================
# PROCESS AI RUBRIC GENERATION
# ============================================================

async def process_assignment_rubric_generation(
    assignment_file: UploadFile,
):

    # ========================================================
    # VALIDATE ASSIGNMENT FILE
    # ========================================================

    if assignment_file is None:

        raise ValueError(
            "Assignment file is required."
        )


    # ========================================================
    # EXTRACT ASSIGNMENT TEXT
    # ========================================================

    assignment_text = await extract_text(
        assignment_file
    )


    if (
        not assignment_text
        or
        not assignment_text.strip()
    ):

        raise ValueError(
            "No readable assignment content was found."
        )


    # ========================================================
    # GENERATE RUBRIC WITH AZURE AI FOUNDRY AGENT
    # ========================================================

    rubric_result = generate_assignment_rubric(
        assignment_text=assignment_text
    )


    # ========================================================
    # CHECK RUBRIC GENERATION ERROR
    # ========================================================

    if (
        isinstance(
            rubric_result,
            dict,
        )
        and rubric_result.get(
            "error"
        )
    ):

        return {
            "assignment_file":
                assignment_file.filename,

            "rubric":
                rubric_result,
        }


    # ========================================================
    # RETURN GENERATED RUBRIC
    # ========================================================

    return {
        "assignment_file":
            assignment_file.filename,

        "rubric":
            rubric_result,
    }


# ============================================================
# PROCESS ASSIGNMENT EVALUATION
# ============================================================

async def process_assignment_evaluation(
    assignment_file: UploadFile,
    rubric_file: UploadFile,
    submission_file: UploadFile,
):

    # ========================================================
    # VALIDATE UPLOADED FILES
    # ========================================================

    if assignment_file is None:

        raise ValueError(
            "Assignment file is required."
        )


    if rubric_file is None:

        raise ValueError(
            "Rubric file is required."
        )


    if submission_file is None:

        raise ValueError(
            "Student submission file is required."
        )


    # ========================================================
    # EXTRACT ASSIGNMENT TEXT
    # ========================================================

    assignment_text = await extract_text(
        assignment_file
    )


    # ========================================================
    # EXTRACT RUBRIC TEXT
    # ========================================================

    rubric_text = await extract_text(
        rubric_file
    )


    # ========================================================
    # EXTRACT STUDENT SUBMISSION TEXT
    # ========================================================

    submission_text = await extract_text(
        submission_file
    )


    # ========================================================
    # VALIDATE EXTRACTED CONTENT
    # ========================================================

    if (
        not assignment_text
        or
        not assignment_text.strip()
    ):

        raise ValueError(
            "No readable assignment content was found."
        )


    if (
        not rubric_text
        or
        not rubric_text.strip()
    ):

        raise ValueError(
            "No readable rubric content was found."
        )


    if (
        not submission_text
        or
        not submission_text.strip()
    ):

        raise ValueError(
            "No readable student submission content was found."
        )


    # ========================================================
    # SEND TO ASSIGNMENT EVALUATION AGENT
    # ========================================================

    evaluation_result = evaluate_assignment(
        assignment_text=assignment_text,
        rubric_text=rubric_text,
        submission_text=submission_text,
    )


    # ========================================================
    # CHECK EVALUATION ERROR
    # ========================================================

    if (
        isinstance(
            evaluation_result,
            dict,
        )
        and evaluation_result.get(
            "error"
        )
    ):

        return {
            "assignment_file":
                assignment_file.filename,

            "rubric_file":
                rubric_file.filename,

            "submission_file":
                submission_file.filename,

            "evaluation":
                evaluation_result,
        }


    # ========================================================
    # RETURN FINAL RESULT
    # ========================================================

    return {
        "assignment_file":
            assignment_file.filename,

        "rubric_file":
            rubric_file.filename,

        "submission_file":
            submission_file.filename,

        "evaluation":
            evaluation_result,
    }