import json
import re
import time
from typing import Any, Dict, List

from pydantic import BaseModel

STRUCTURED_OUTPUT_VERSION = "2026-08-17-FIX-4"

from backend.assignment_evaluation.client import (
    GEMINI_MODEL,
    gemini_client,
    validate_gemini_configuration,
)


# ============================================================
# STRUCTURED OUTPUT MODELS
# ============================================================

class RubricCriterionOutput(BaseModel):
    name: str
    description: str
    max_marks: float
    weight: float


class RubricOutput(BaseModel):
    title: str
    total_marks: float
    criteria: List[RubricCriterionOutput]


class EvaluationDeductionOutput(BaseModel):
    question: str
    marks_deducted: float
    reason: str


class EvaluationOutput(BaseModel):
    assignment_name: str
    total_marks: float
    obtained_marks: float
    percentage: float
    remarks: str
    deductions: List[EvaluationDeductionOutput]


# ============================================================
# COMMON HELPERS
# ============================================================

def to_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid numeric value returned: {value}"
        )


def _clean_number(value: float):
    value = float(value)
    return int(value) if value.is_integer() else value


def _model_to_dict(value) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    raise ValueError(
        "Gemini structured response could not be converted to a dictionary."
    )


def _is_retryable_gemini_error(error: Exception) -> bool:
    """
    Retry temporary Gemini capacity/rate-limit failures only.
    Permanent validation/authentication errors are returned immediately.
    """

    status_code = (
        getattr(error, "status_code", None)
        or getattr(error, "code", None)
    )

    error_text = str(error).lower()

    return (
        status_code in {429, 503}
        or "429" in error_text
        or "503" in error_text
        or "resource_exhausted" in error_text
        or "unavailable" in error_text
        or "high demand" in error_text
        or "temporarily overloaded" in error_text
    )


def _structured_gemini_call(
    prompt: str,
    response_schema,
) -> Dict[str, Any]:
    """
    Ask Gemini for schema-constrained JSON.

    Temporary 429/503 Gemini errors are retried with exponential backoff:
    1s -> 2s -> 4s -> 8s (maximum 4 attempts).
    """

    validate_gemini_configuration()

    max_attempts = 4
    delay_seconds = 1

    for attempt in range(1, max_attempts + 1):
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                    "temperature": 0.0,
                },
            )

            parsed = getattr(
                response,
                "parsed",
                None,
            )

            if parsed is not None:
                return _model_to_dict(
                    parsed
                )

            # Compatibility fallback for SDK versions where parsed is unavailable.
            response_text = getattr(
                response,
                "text",
                None,
            )

            if not response_text:
                raise ValueError(
                    "Gemini returned an empty structured response."
                )

            try:
                if hasattr(
                    response_schema,
                    "model_validate_json",
                ):
                    validated = response_schema.model_validate_json(
                        response_text
                    )
                else:
                    validated = response_schema.parse_raw(
                        response_text
                    )
            except Exception as error:
                raise ValueError(
                    "Gemini response did not match the required structured schema."
                ) from error

            return _model_to_dict(
                validated
            )

        except Exception as error:
            if (
                attempt >= max_attempts
                or not _is_retryable_gemini_error(error)
            ):
                raise

            time.sleep(
                delay_seconds
            )

            delay_seconds *= 2

    raise RuntimeError(
        "Gemini request failed after retry attempts."
    )


# ============================================================
# EXPLICIT TOTAL MARKS DETECTION
# ============================================================

TOTAL_MARK_PATTERNS = [
    # Common exam/assignment header format used in uploaded papers, e.g. "Marks: 20"
    r"(?im)^\s*marks?\s*[:=\-]\s*(\d+(?:\.\d+)?)\s*$",
    r"\btotal\s+marks?\s*[:=\-]?\s*(\d+(?:\.\d+)?)\b",
    r"\bmaximum\s+marks?\s*[:=\-]?\s*(\d+(?:\.\d+)?)\b",
    r"\bmax(?:imum)?\s+marks?\s*[:=\-]?\s*(\d+(?:\.\d+)?)\b",
    r"\btotal\s+points?\s*[:=\-]?\s*(\d+(?:\.\d+)?)\b",
    r"\bworth\s+(\d+(?:\.\d+)?)\s+marks?\b",
]


def _extract_explicit_total_marks(
    assignment_text: str,
):
    raw_text = assignment_text or ""

    # First preserve line boundaries so document-level headers such as
    # "Marks: 20" can be detected safely without confusing them with
    # question labels like "Q1. ... — 2 Marks".
    for pattern in TOTAL_MARK_PATTERNS:
        match = re.search(
            pattern,
            raw_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        if match:
            marks = float(
                match.group(1)
            )

            if marks > 0:
                return marks

    # Fallback normalization for formats such as "Total Marks 20".
    normalized_text = " ".join(
        raw_text.split()
    )

    fallback_patterns = TOTAL_MARK_PATTERNS[1:]

    for pattern in fallback_patterns:
        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )

        if match:
            marks = float(
                match.group(1)
            )

            if marks > 0:
                return marks

    return None


# ============================================================
# RUBRIC GENERATION
# ============================================================

RUBRIC_GENERATION_INSTRUCTIONS = """
You are the EduAI Rubric Generator.

Generate a fair and measurable rubric strictly from the supplied assignment.

RULES:
1. Use only requirements explicitly stated in the assignment.
2. Do not invent unrelated grading requirements.
3. Do not expand a short requirement into extra technical requirements.
4. Do not assume testing, comments, documentation, modular design,
   data types, edge cases, or implementation details unless explicitly stated.
5. Prefer 3 to 7 criteria unless the assignment requires otherwise.
6. Every criterion must contain:
   name, description, max_marks, weight.
7. Every max_marks value must be greater than zero.
8. Criterion max_marks must sum exactly to the supplied total marks.
9. Criterion weights must sum exactly to 100.
10. Do not create duplicate or overlapping criteria.
11. Do not evaluate a student submission.
12. Do not award obtained marks.
"""


def _normalize_rubric_result(
    result: Dict[str, Any],
    expected_total_marks: float,
) -> Dict[str, Any]:

    title = str(
        result.get(
            "title",
            "",
        )
    ).strip()

    if not title:
        raise ValueError(
            "Rubric title cannot be empty."
        )

    model_total = to_number(
        result.get(
            "total_marks"
        )
    )

    if abs(
        model_total
        - expected_total_marks
    ) > 0.01:
        raise ValueError(
            "Gemini changed the assignment total marks. "
            f"Expected {expected_total_marks}, received {model_total}."
        )

    raw_criteria = result.get(
        "criteria",
        [],
    )

    if (
        not isinstance(
            raw_criteria,
            list,
        )
        or
        not raw_criteria
    ):
        raise ValueError(
            "Generated rubric must contain at least one criterion."
        )

    normalized_criteria = []
    seen_names = set()

    for index, criterion in enumerate(
        raw_criteria,
        start=1,
    ):
        name = str(
            criterion.get(
                "name",
                "",
            )
        ).strip()

        description = str(
            criterion.get(
                "description",
                "",
            )
        ).strip()

        max_marks = to_number(
            criterion.get(
                "max_marks"
            )
        )

        if not name:
            raise ValueError(
                f"Criterion #{index} must have a name."
            )

        if not description:
            raise ValueError(
                f"Criterion #{index} must have a description."
            )

        if max_marks <= 0:
            raise ValueError(
                f"Criterion #{index} marks must be greater than zero."
            )

        key = name.casefold()

        if key in seen_names:
            raise ValueError(
                f"Duplicate rubric criterion detected: {name}."
            )

        seen_names.add(
            key
        )

        normalized_criteria.append(
            {
                "name": name,
                "description": description,
                "max_marks": max_marks,
                "weight": 0.0,
            }
        )

    criteria_total = sum(
        item["max_marks"]
        for item in normalized_criteria
    )

    if abs(
        criteria_total
        - expected_total_marks
    ) > 0.01:
        raise ValueError(
            "Rubric criterion marks do not match total marks. "
            f"Criteria total: {criteria_total}; "
            f"expected total: {expected_total_marks}."
        )

    # Backend recalculates weights so total is exactly 100%.
    running_weight = 0.0

    for index, criterion in enumerate(
        normalized_criteria
    ):
        if index == len(
            normalized_criteria
        ) - 1:
            weight = round(
                100.0 - running_weight,
                2,
            )
        else:
            weight = round(
                (
                    criterion["max_marks"]
                    / expected_total_marks
                )
                * 100,
                2,
            )
            running_weight += weight

        criterion["weight"] = weight
        criterion["max_marks"] = _clean_number(
            criterion["max_marks"]
        )

    return {
        "title": title,
        "total_marks": _clean_number(
            expected_total_marks
        ),
        "criteria": normalized_criteria,
    }


def generate_assignment_rubric(
    assignment_text: str,
) -> Dict[str, Any]:

    validate_gemini_configuration()

    if (
        not assignment_text
        or
        not assignment_text.strip()
    ):
        raise ValueError(
            "Assignment text is required for rubric generation."
        )

    total_marks = _extract_explicit_total_marks(
        assignment_text
    )

    if total_marks is None:
        return {
            "error": "TOTAL_MARKS_NOT_FOUND",
            "message": (
                "The assignment does not clearly specify total marks."
            ),
        }

    prompt = f"""
{RUBRIC_GENERATION_INSTRUCTIONS}

ASSIGNMENT TOTAL MARKS
----------------------
{total_marks}

ASSIGNMENT
----------
{assignment_text}

Generate the rubric.

Important:
- total_marks MUST be exactly {total_marks}.
- Criterion max_marks MUST sum exactly to {total_marks}.
- Every criterion must be grounded only in the assignment.
"""

    try:
        first_result = _structured_gemini_call(
            prompt,
            RubricOutput,
        )

        try:
            return _normalize_rubric_result(
                first_result,
                total_marks,
            )

        except Exception as validation_error:
            correction_prompt = f"""
{RUBRIC_GENERATION_INSTRUCTIONS}

ASSIGNMENT TOTAL MARKS
----------------------
{total_marks}

ASSIGNMENT
----------
{assignment_text}

PREVIOUS RUBRIC
---------------
{json.dumps(
    first_result,
    ensure_ascii=False
)}

VALIDATION ERROR
----------------
{str(validation_error)}

Return a corrected rubric only.

Rules:
- total_marks MUST remain exactly {total_marks}.
- Criterion marks MUST sum exactly to {total_marks}.
- Do not invent assignment requirements.
"""

            corrected_result = _structured_gemini_call(
                correction_prompt,
                RubricOutput,
            )

            return _normalize_rubric_result(
                corrected_result,
                total_marks,
            )

    except Exception as error:
        return {
            "error": "AI rubric generation failed.",
            "details": str(error),
        }


# ============================================================
# ASSIGNMENT EVALUATION
# ============================================================

EVALUATION_INSTRUCTIONS = """
You are the EduAI Assignment Evaluation Agent.

Evaluate the student's submission strictly according to the supplied rubric.
The rubric is the only authority for awarding marks.

RULES:
1. Evaluate only requirements represented in the rubric.
2. Award marks only when clear evidence exists in the submission.
3. Never assume missing work exists.
4. Award partial marks only for clearly partial satisfaction.
5. Never create new grading criteria.
6. Never award more than the allowed maximum.
7. Apply the same grading standard throughout the submission.
8. total_marks must come from the rubric.
9. obtained_marks must be between 0 and total_marks.
10. Sum of marks_deducted must equal total_marks - obtained_marks.
11. If no marks were deducted, deductions must be an empty list.
"""


def _normalize_evaluation_result(
    result: Dict[str, Any],
) -> Dict[str, Any]:

    total_marks = to_number(
        result.get(
            "total_marks"
        )
    )

    obtained_marks = to_number(
        result.get(
            "obtained_marks"
        )
    )

    if total_marks <= 0:
        raise ValueError(
            "Evaluation total marks must be greater than zero."
        )

    if obtained_marks < 0:
        raise ValueError(
            "Obtained marks cannot be negative."
        )

    if obtained_marks > total_marks:
        raise ValueError(
            "Obtained marks cannot exceed total marks."
        )

    raw_deductions = result.get(
        "deductions",
        [],
    )

    if not isinstance(
        raw_deductions,
        list,
    ):
        raise ValueError(
            "Evaluation deductions must be a list."
        )

    deductions = []

    for index, item in enumerate(
        raw_deductions,
        start=1,
    ):
        marks_deducted = to_number(
            item.get(
                "marks_deducted",
                0,
            )
        )

        if marks_deducted < 0:
            raise ValueError(
                f"Deduction #{index} cannot be negative."
            )

        if marks_deducted == 0:
            continue

        deductions.append(
            {
                "question": str(
                    item.get(
                        "question"
                    )
                    or
                    f"Item {index}"
                ),
                "marks_deducted": _clean_number(
                    marks_deducted
                ),
                "reason": str(
                    item.get(
                        "reason"
                    )
                    or
                    "Rubric requirement not fully satisfied."
                ),
            }
        )

    total_deducted = sum(
        to_number(
            item["marks_deducted"]
        )
        for item in deductions
    )

    expected_deduction = (
        total_marks - obtained_marks
    )

    if abs(
        total_deducted
        - expected_deduction
    ) > 0.01:
        raise ValueError(
            "Evaluation calculation mismatch: "
            f"deductions total {total_deducted}, "
            f"expected {expected_deduction}."
        )

    percentage = round(
        (
            obtained_marks
            / total_marks
        )
        * 100,
        2,
    )

    return {
        "assignment_name": str(
            result.get(
                "assignment_name"
            )
            or
            "Assignment Evaluation"
        ),
        "total_marks": _clean_number(
            total_marks
        ),
        "obtained_marks": _clean_number(
            obtained_marks
        ),
        "percentage": percentage,
        "remarks": str(
            result.get(
                "remarks"
            )
            or
            ""
        ),
        "deductions": deductions,
    }


def evaluate_assignment(
    assignment_text: str,
    rubric_text: str,
    submission_text: str,
):

    validate_gemini_configuration()

    if (
        not assignment_text
        or
        not assignment_text.strip()
    ):
        raise ValueError(
            "Assignment text is required."
        )

    if (
        not rubric_text
        or
        not rubric_text.strip()
    ):
        raise ValueError(
            "Rubric text is required."
        )

    if (
        not submission_text
        or
        not submission_text.strip()
    ):
        raise ValueError(
            "Student submission text is required."
        )

    prompt = f"""
{EVALUATION_INSTRUCTIONS}

ASSIGNMENT
----------
{assignment_text}

RUBRIC
------
{rubric_text}

STUDENT SUBMISSION
------------------
{submission_text}

Evaluate the submission now.

Before returning:
- verify total_marks against the rubric;
- verify obtained_marks does not exceed total_marks;
- verify deductions total equals total_marks - obtained_marks;
- verify percentage arithmetic.
"""

    try:
        first_result = _structured_gemini_call(
            prompt,
            EvaluationOutput,
        )

        try:
            return _normalize_evaluation_result(
                first_result
            )

        except Exception as validation_error:
            correction_prompt = f"""
{EVALUATION_INSTRUCTIONS}

ASSIGNMENT
----------
{assignment_text}

RUBRIC
------
{rubric_text}

STUDENT SUBMISSION
------------------
{submission_text}

PREVIOUS EVALUATION
-------------------
{json.dumps(
    first_result,
    ensure_ascii=False
)}

VALIDATION ERROR
----------------
{str(validation_error)}

Return a corrected evaluation only.

Preserve the same rubric-based judgment as closely as possible.
Do not invent grading criteria.
Do not exceed rubric marks.
"""

            corrected_result = _structured_gemini_call(
                correction_prompt,
                EvaluationOutput,
            )

            return _normalize_evaluation_result(
                corrected_result
            )

    except Exception as error:
        return {
            "error": "Assignment evaluation failed.",
            "details": str(error),
        }