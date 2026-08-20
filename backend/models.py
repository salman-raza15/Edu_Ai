from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Float,
    LargeBinary,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


# =========================================================
# RBAC / ADMIN / COURSE MODELS
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="INSTRUCTOR")

    courses = relationship(
        "CourseAssignment",
        back_populates="instructor",
        cascade="all, delete-orphan",
    )


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    assignments = relationship(
        "CourseAssignment",
        back_populates="course",
        cascade="all, delete-orphan",
    )


class CourseAssignment(Base):
    __tablename__ = "course_assignments"

    id = Column(Integer, primary_key=True, index=True)
    instructor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )

    instructor = relationship("User", back_populates="courses")
    course = relationship("Course", back_populates="assignments")

    __table_args__ = (
        UniqueConstraint(
            "instructor_id",
            "course_id",
            name="uq_instructor_course",
        ),
    )


# =========================================================
# INSTRUCTOR / ASSESSMENT MODELS
# =========================================================

class QuestionSet(Base):
    __tablename__ = "question_sets"

    id = Column(Integer, primary_key=True, index=True)

    course_id = Column(
        Integer,
        nullable=True,
    )

    title = Column(
        String,
        nullable=False,
    )

    source_type = Column(
        String,
        nullable=False,
    )

    topic = Column(
        String,
        nullable=True,
    )

    difficulty = Column(
        String,
        nullable=False,
    )

    total_questions = Column(
        Integer,
        nullable=False,
    )

    total_marks = Column(
        Integer,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    questions = relationship(
        "Question",
        back_populates="question_set",
        cascade="all, delete",
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)

    question_set_id = Column(
        Integer,
        ForeignKey("question_sets.id"),
        nullable=False,
    )

    question_number = Column(
        Integer,
        nullable=False,
    )

    type = Column(
        String,
        nullable=False,
    )

    question_text = Column(
        Text,
        nullable=False,
    )

    options = Column(
        JSON,
        nullable=True,
    )

    correct_answer = Column(
        Text,
        nullable=True,
    )

    marks = Column(
        Integer,
        nullable=False,
    )

    question_set = relationship(
        "QuestionSet",
        back_populates="questions",
    )


# =========================================================
# AI EVALUATION -> REPORTING INTEGRATION
# =========================================================

class EvaluationBatch(Base):
    __tablename__ = "evaluation_batches"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(String(255), nullable=False, index=True)
    course_id = Column(String(255), nullable=False, index=True)
    cohort_id = Column(String(255), nullable=False, index=True)
    source_filename = Column(String(255), nullable=True)
    xlsx_filename = Column(String(255), nullable=False)
    xlsx_data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    results = relationship(
        "EvaluationResult",
        back_populates="batch",
        cascade="all, delete-orphan",
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(
        Integer,
        ForeignKey("evaluation_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(String(255), nullable=False, index=True)
    student_name = Column(String(255), nullable=False)
    course_id = Column(String(255), nullable=False, index=True)
    cohort_id = Column(String(255), nullable=False, index=True)
    assignment_id = Column(String(255), nullable=False, index=True)
    criteria = Column(String(255), nullable=False)
    max_marks = Column(Float, nullable=False)
    obtained_marks = Column(Float, nullable=False)
    evaluation_date = Column(String(10), nullable=False, index=True)
    remarks = Column(Text, nullable=True)

    batch = relationship("EvaluationBatch", back_populates="results")