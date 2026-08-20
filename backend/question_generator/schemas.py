from pydantic import BaseModel, ConfigDict
from typing import Optional



# =====================================
# QUESTION GENERATOR REQUEST
# =====================================

class QuestionGeneratorRequest(BaseModel):

    source_type: str

    topic: Optional[str] = None

    material_content: Optional[str] = None

    question_type: str

    difficulty: str

    number_of_questions: int

    total_marks: int




# =====================================
# QUESTION RESPONSE
# =====================================

class QuestionResponse(BaseModel):

    id: int

    question_set_id: int

    question_number: int

    type: str

    question_text: str

    options: Optional[list] = None

    correct_answer: Optional[str] = None

    marks: int


    model_config = ConfigDict(
        from_attributes=True
    )




# =====================================
# QUESTION SET RESPONSE
# =====================================

class QuestionSetResponse(BaseModel):

    id: int

    course_id: Optional[int] = None

    title: str

    source_type: str

    topic: Optional[str] = None

    difficulty: str

    total_questions: int

    total_marks: int


    model_config = ConfigDict(
        from_attributes=True
    )




# =====================================
# QUESTION SET DETAIL RESPONSE
# =====================================

class QuestionSetDetailResponse(BaseModel):

    question_set: QuestionSetResponse

    questions: list[QuestionResponse]




# =====================================
# QUESTION UPDATE REQUEST
# =====================================

class QuestionUpdateRequest(BaseModel):

    question_text: Optional[str] = None

    type: Optional[str] = None

    options: Optional[list] = None

    correct_answer: Optional[str] = None

    marks: Optional[int] = None