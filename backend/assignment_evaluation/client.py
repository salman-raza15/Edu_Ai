import os
from pathlib import Path

from dotenv import load_dotenv


# =========================================================
# PROJECT ROOT / ENV
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_ROOT / ".env"
)


# =========================================================
# GEMINI CONFIGURATION
# Used by BOTH:
# - AI Assignment Evaluation
# - AI Rubric Generation
# =========================================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash",
)


try:
    from google import genai
    from google.genai import types as genai_types

except ImportError:
    genai = None
    genai_types = None


gemini_client = None


if (
    genai is not None
    and GEMINI_API_KEY
):

    try:

        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    except Exception:

        # Do not crash FastAPI while importing this module.
        # A clear error will be raised when validation runs.
        gemini_client = None


# =========================================================
# GEMINI CONFIGURATION VALIDATION
# =========================================================

def validate_gemini_configuration():

    if genai is None:

        raise ValueError(
            "The 'google-genai' package is required. "
            "Run: pip install -U google-genai"
        )


    if genai_types is None:

        raise ValueError(
            "google.genai.types could not be imported."
        )


    if not GEMINI_API_KEY:

        raise ValueError(
            "GEMINI_API_KEY is missing in final_ui/.env."
        )


    if not GEMINI_MODEL:

        raise ValueError(
            "GEMINI_MODEL is missing in final_ui/.env."
        )


    if gemini_client is None:

        raise ValueError(
            "The Gemini client could not be initialized. "
            "Check GEMINI_API_KEY and restart the backend."
        )


    return True


# =========================================================
# GET GEMINI CLIENT
# =========================================================

def get_gemini_client():

    validate_gemini_configuration()

    return gemini_client


# =========================================================
# BACKWARD-COMPATIBLE VALIDATION NAMES
#
# These names are kept so existing imports do not immediately
# break while evaluation_agent.py is being migrated to Gemini.
# Both now validate the same Gemini configuration.
# =========================================================

def validate_evaluation_configuration():

    return validate_gemini_configuration()


def validate_rubric_configuration():

    return validate_gemini_configuration()