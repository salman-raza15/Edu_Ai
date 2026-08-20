from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from . import models

from .auth import router as auth_router
from .admin import router as admin_router
from .instructor import router as instructor_router

from .question_generator.router import (
    router as question_generator_router,
)
from .question_generator.crud_router import (
    router as question_management_router,
)
from .assignment_evaluation.router import (
    router as assignment_evaluation_router,
)
from .report_generation.router import (
    router as report_generation_router,
)


# =========================================================
# CREATE ALL DATABASE TABLES
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="EduAI Intelligent Assessment Platform",
    description=(
        "AI-powered assessment platform with Admin RBAC, "
        "Question Generator, AI Rubric Generation, "
        "AI Assignment Evaluation, and Report Generation"
    ),
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# AUTH / ADMIN / INSTRUCTOR RBAC
# =========================================================

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(instructor_router)


# =========================================================
# INSTRUCTOR MODULES
# =========================================================

app.include_router(question_generator_router)
app.include_router(question_management_router)
app.include_router(assignment_evaluation_router)
app.include_router(report_generation_router)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "EduAI Backend Running",
        "modules": [
            "Authentication",
            "Admin RBAC",
            "Instructor Course Assignments",
            "Question Generator",
            "AI Rubric Generation",
            "AI Assignment Evaluation",
            "Report Generation",
        ],
        "database": "Connected",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "EduAI",
    }
