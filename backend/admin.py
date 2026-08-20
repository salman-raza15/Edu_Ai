from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .database import get_db
from .models import Course, CourseAssignment, User
from .security import hash_password, require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


class InstructorCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class CourseCreateRequest(BaseModel):
    name: str
    description: str | None = None


class CourseAssignRequest(BaseModel):
    instructor_id: int
    course_id: int


@router.get("/instructors")
def list_instructors(
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    instructors = (
        db.query(User)
        .filter(User.role == "INSTRUCTOR")
        .order_by(User.name.asc())
        .all()
    )
    return [
        {
            "id": item.id,
            "name": item.name,
            "email": item.email,
            "role": item.role,
        }
        for item in instructors
    ]


@router.post("/create-instructor")
def create_instructor(
    payload: InstructorCreateRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if len(payload.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters.",
        )

    email = payload.email.lower().strip()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    instructor = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="INSTRUCTOR",
    )
    db.add(instructor)
    db.commit()
    db.refresh(instructor)

    return {
        "message": "Instructor created successfully",
        "id": instructor.id,
        "name": instructor.name,
        "email": instructor.email,
    }


@router.delete("/delete-instructor/{instructor_id}")
def delete_instructor(
    instructor_id: int,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    instructor = (
        db.query(User)
        .filter(
            User.id == instructor_id,
            User.role == "INSTRUCTOR",
        )
        .first()
    )

    if not instructor:
        raise HTTPException(
            status_code=404,
            detail="Instructor not found",
        )

    db.delete(instructor)
    db.commit()

    return {"message": "Instructor deleted successfully"}


@router.get("/courses")
def list_courses(
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    courses = db.query(Course).order_by(Course.name.asc()).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
        }
        for item in courses
    ]


@router.post("/create-course")
def create_course(
    payload: CourseCreateRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = payload.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Course name is required.",
        )

    course = Course(
        name=name,
        description=(payload.description or "").strip() or None,
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    return {
        "message": "Course created successfully",
        "id": course.id,
        "name": course.name,
    }


@router.post("/assign-course")
def assign_course(
    payload: CourseAssignRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    instructor = (
        db.query(User)
        .filter(
            User.id == payload.instructor_id,
            User.role == "INSTRUCTOR",
        )
        .first()
    )

    if not instructor:
        raise HTTPException(
            status_code=404,
            detail="Instructor not found",
        )

    course = db.query(Course).filter(Course.id == payload.course_id).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found",
        )

    existing = (
        db.query(CourseAssignment)
        .filter(
            CourseAssignment.instructor_id == payload.instructor_id,
            CourseAssignment.course_id == payload.course_id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Course is already assigned to this instructor.",
        )

    assignment = CourseAssignment(
        instructor_id=payload.instructor_id,
        course_id=payload.course_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return {
        "message": "Course assigned successfully",
        "assignment_id": assignment.id,
    }


@router.get("/assignments")
def list_assignments(
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    assignments = (
        db.query(CourseAssignment)
        .order_by(CourseAssignment.id.desc())
        .all()
    )

    return [
        {
            "id": item.id,
            "instructor_id": item.instructor_id,
            "instructor_name": item.instructor.name,
            "course_id": item.course_id,
            "course_name": item.course.name,
        }
        for item in assignments
    ]
