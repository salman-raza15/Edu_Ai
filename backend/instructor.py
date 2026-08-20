from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import CourseAssignment, User
from .security import get_current_user


router = APIRouter(
    prefix="/instructor",
    tags=["Instructor"],
)


@router.get("/me/courses")
def get_my_courses(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return only the courses assigned to the currently
    authenticated instructor.

    The instructor is identified from the Bearer token,
    so the client does not need to send an instructor ID.
    """

    if current_user["role"] != "INSTRUCTOR":
        raise HTTPException(
            status_code=403,
            detail="Instructor access required",
        )

    instructor = (
        db.query(User)
        .filter(
            User.id == current_user["id"],
            User.role == "INSTRUCTOR",
        )
        .first()
    )

    if not instructor:
        raise HTTPException(
            status_code=404,
            detail="Instructor record not found",
        )

    assignments = (
        db.query(CourseAssignment)
        .filter(
            CourseAssignment.instructor_id == instructor.id
        )
        .order_by(CourseAssignment.id.desc())
        .all()
    )

    return {
        "instructor_id": instructor.id,
        "instructor_name": instructor.name,
        "courses": [
            {
                "id": assignment.course.id,
                "name": assignment.course.name,
                "description": assignment.course.description,
                "assignment_id": assignment.id,
            }
            for assignment in assignments
            if assignment.course is not None
        ],
    }