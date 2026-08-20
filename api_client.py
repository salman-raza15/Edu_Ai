import os
import requests


# =========================================================
# API CONFIGURATION
# =========================================================

# EduAI backend
# Authentication and instructor features use the same backend.
BASE_URL = os.getenv(
    "EDUAI_INSTRUCTOR_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

DEFAULT_TIMEOUT = 60


# =========================================================
# ERROR HANDLER
# =========================================================

def handle_response(
    response,
    action="Request",
):

    if response.ok:
        return

    try:
        error_data = response.json()

    except Exception:
        error_data = response.text

    raise RuntimeError(
        f"{action} failed "
        f"[HTTP {response.status_code}]: "
        f"{error_data}"
    )


# =========================================================
# FILE HELPER
# =========================================================

def _file_to_request_tuple(
    uploaded_file,
):

    if uploaded_file is None:
        return None

    file_name = getattr(
        uploaded_file,
        "name",
        "uploaded_file",
    )

    file_type = getattr(
        uploaded_file,
        "type",
        "application/octet-stream",
    )

    try:
        file_bytes = uploaded_file.getvalue()

    except Exception:

        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        file_bytes = uploaded_file.read()

    return (
        file_name,
        file_bytes,
        file_type,
    )


# =========================================================
# GENERATE QUESTIONS FROM TOPIC
# =========================================================

def generate_questions(
    payload,
):

    try:

        response = requests.post(
            f"{BASE_URL}/question-generator/generate",
            json=payload,
            timeout=DEFAULT_TIMEOUT,
        )

    except requests.exceptions.ConnectionError as error:

        raise RuntimeError(
            f"Could not connect to the EduAI backend at "
            f"{BASE_URL}. "
            f"Please make sure the FastAPI server is running."
        ) from error

    except requests.exceptions.Timeout as error:

        raise RuntimeError(
            "Question generation request timed out."
        ) from error

    handle_response(
        response,
        "Question generation",
    )

    return response.json()


# =========================================================
# GENERATE QUESTIONS FROM FILE
# =========================================================

def generate_questions_from_file(
    file,
    question_type,
    difficulty,
    number_of_questions,
    total_marks,
):

    if file is None:
        raise ValueError(
            "Learning material file is required."
        )

    file_tuple = _file_to_request_tuple(file)

    files = {
        "file": file_tuple,
    }

    data = {
        "question_type":
            question_type,

        "difficulty":
            difficulty,

        "number_of_questions":
            number_of_questions,

        "total_marks":
            total_marks,
    }

    try:

        response = requests.post(
            f"{BASE_URL}/question-generator/generate-from-file",
            files=files,
            data=data,
            timeout=120,
        )

    except requests.exceptions.ConnectionError as error:

        raise RuntimeError(
            f"Could not connect to the EduAI backend at "
            f"{BASE_URL}. "
            f"Please make sure the FastAPI server is running."
        ) from error

    except requests.exceptions.Timeout as error:

        raise RuntimeError(
            "File-based question generation request timed out."
        ) from error

    handle_response(
        response,
        "File-based question generation",
    )

    return response.json()


# =========================================================
# SAVE QUESTION SET
# =========================================================

def save_question_set(
    payload,
):

    response = requests.post(
        f"{BASE_URL}/question-management/save",
        json=payload,
        timeout=DEFAULT_TIMEOUT,
    )

    handle_response(
        response,
        "Save question set",
    )

    return response.json()


# =========================================================
# GET ALL QUESTION SETS
# =========================================================

def get_question_sets():

    response = requests.get(
        f"{BASE_URL}/question-management/sets",
        timeout=DEFAULT_TIMEOUT,
    )

    handle_response(
        response,
        "Load question sets",
    )

    return response.json()


# =========================================================
# GET SINGLE QUESTION SET
# =========================================================

def get_question_set(
    set_id,
):

    response = requests.get(
        f"{BASE_URL}/question-management/sets/{set_id}",
        timeout=DEFAULT_TIMEOUT,
    )

    handle_response(
        response,
        "Load question set",
    )

    return response.json()


# =========================================================
# UPDATE QUESTION
# =========================================================

def update_question(
    question_id,
    payload,
):

    response = requests.put(
        (
            f"{BASE_URL}/question-management/"
            f"questions/{question_id}"
        ),
        json=payload,
        timeout=DEFAULT_TIMEOUT,
    )

    handle_response(
        response,
        "Update question",
    )

    # Some APIs return 204 No Content
    if response.status_code == 204:
        return {
            "message":
                "Question updated successfully."
        }

    try:
        return response.json()

    except Exception:
        return {
            "message":
                "Question updated successfully."
        }


# =========================================================
# DELETE QUESTION SET
# =========================================================

def delete_question_set(
    set_id,
):

    response = requests.delete(
        f"{BASE_URL}/question-management/sets/{set_id}",
        timeout=DEFAULT_TIMEOUT,
    )

    handle_response(
        response,
        "Delete question set",
    )

    if response.status_code == 204:
        return {
            "message":
                "Question set deleted successfully."
        }

    try:
        return response.json()

    except Exception:
        return {
            "message":
                "Question set deleted successfully."
        }


# =========================================================
# DOWNLOAD PDF
# =========================================================

def download_pdf(
    set_id,
):

    response = requests.get(
        (
            f"{BASE_URL}/question-management/"
            f"sets/{set_id}/export/pdf"
        ),
        timeout=DEFAULT_TIMEOUT,
    )

    handle_response(
        response,
        "PDF download",
    )

    return response.content


# =========================================================
# DOWNLOAD DOCX
# =========================================================

def download_docx(
    set_id,
):

    response = requests.get(
        (
            f"{BASE_URL}/question-management/"
            f"sets/{set_id}/export/docx"
        ),
        timeout=DEFAULT_TIMEOUT,
    )

    handle_response(
        response,
        "DOCX download",
    )

    return response.content


# =========================================================
# BACKWARD-COMPATIBLE EXPORT NAMES
# =========================================================

def export_pdf(
    set_id,
):

    return download_pdf(
        set_id
    )


def export_docx(
    set_id,
):

    return download_docx(
        set_id
    )


# =========================================================
# AI ASSIGNMENT EVALUATION HEALTH
# =========================================================

def check_assignment_evaluation_health():

    try:

        response = requests.get(
            f"{BASE_URL}/assignment-evaluation/health",
            timeout=10,
        )

        handle_response(
            response,
            "Assignment evaluation health check",
        )

        return response.json()

    except Exception as error:

        return {
            "status": "unavailable",
            "error": str(error),
        }


# =========================================================
# AI RUBRIC GENERATION FROM ASSIGNMENT
# =========================================================

def generate_assignment_rubric(
    assignment_file,
):

    if assignment_file is None:

        raise ValueError(
            "Assignment file is required."
        )

    files = {
        "assignment_file":
            _file_to_request_tuple(
                assignment_file
            ),
    }

    try:

        response = requests.post(
            (
                f"{BASE_URL}/assignment-evaluation/"
                "generate-rubric"
            ),
            files=files,
            timeout=180,
        )

        handle_response(
            response,
            "AI rubric generation",
        )

        result = response.json()

        if not isinstance(
            result,
            dict,
        ):

            raise RuntimeError(
                "AI rubric generation returned an invalid response."
            )

        rubric = result.get(
            "rubric"
        )

        if not isinstance(
            rubric,
            dict,
        ):

            raise RuntimeError(
                "AI rubric generation did not return a rubric."
            )

        return result

    except requests.ConnectionError as error:

        raise RuntimeError(
            "Could not connect to the EduAI backend."
        ) from error

    except requests.Timeout as error:

        raise RuntimeError(
            "AI rubric generation request timed out."
        ) from error


# =========================================================
# AI ASSIGNMENT EVALUATION
# =========================================================

def evaluate_assignment(
    assignment_file,
    rubric_file,
    submission_file,
):

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

    files = {

        "assignment_file":
            _file_to_request_tuple(
                assignment_file
            ),

        "rubric_file":
            _file_to_request_tuple(
                rubric_file
            ),

        "submission_file":
            _file_to_request_tuple(
                submission_file
            ),
    }

    try:

        response = requests.post(
            f"{BASE_URL}/assignment-evaluation/evaluate",
            files=files,
            timeout=180,
        )

        handle_response(
            response,
            "AI assignment evaluation",
        )

        return response.json()

    except requests.ConnectionError as error:

        raise RuntimeError(
            "Could not connect to the EduAI backend."
        ) from error

    except requests.Timeout as error:

        raise RuntimeError(
            "Assignment evaluation request timed out."
        ) from error

# =========================================================
# SAVE ZIP BATCH RESULTS FOR REPORT GENERATION
# =========================================================

def save_batch_evaluation_results(payload):
    try:
        response = requests.post(
            f"{BASE_URL}/assignment-evaluation/batch-results/save",
            json=payload,
            timeout=120,
        )
    except requests.ConnectionError as error:
        raise RuntimeError("Could not connect to the EduAI backend.") from error
    except requests.Timeout as error:
        raise RuntimeError("Saving batch evaluation results timed out.") from error

    handle_response(response, "Save batch evaluation results")
    return response.json()
