from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
)

import os
import uuid


from .schemas import (
    QuestionGeneratorRequest,
)

from .services import (
    generate_questions_with_ai,
)

from .file_reader import (
    extract_text,
)



router = APIRouter(
    prefix="/question-generator",
    tags=["Question Generator"]
)



# ==========================================
# Topic / Text Based Question Generation
# NO DATABASE SAVE
# ==========================================

@router.post("/generate")
def generate_questions(
    request: QuestionGeneratorRequest
):

    result = generate_questions_with_ai(
        request
    )


    return result




# ==========================================
# File Based Question Generation
# PDF / DOCX / PPTX
# NO DATABASE SAVE
# ==========================================

@router.post("/generate-from-file")
async def generate_questions_from_file(

    file: UploadFile = File(...),

    question_type: str = Form("MCQ"),

    difficulty: str = Form("Medium"),

    number_of_questions: int = Form(5),

    total_marks: int = Form(10)

):


    allowed_extensions = [

        ".pdf",
        ".docx",
        ".pptx",

    ]


    MAX_FILE_SIZE = (
        25 * 1024 * 1024
    )


    filename = file.filename.lower()



    if not any(
        filename.endswith(ext)
        for ext in allowed_extensions
    ):

        raise HTTPException(

            status_code=400,

            detail=(
                "Only PDF, DOCX and PPTX "
                "files are supported"
            )

        )



    file_content = await file.read()



    if not file_content:

        raise HTTPException(

            status_code=400,

            detail="Uploaded file is empty"

        )



    if len(file_content) > MAX_FILE_SIZE:

        raise HTTPException(

            status_code=400,

            detail="File size exceeds 25MB limit"

        )



    temp_filename = (

        f"temp_{uuid.uuid4()}_{file.filename}"

    )



    try:


        with open(
            temp_filename,
            "wb"
        ) as buffer:

            buffer.write(
                file_content
            )



        try:

            extracted_text = extract_text(
                temp_filename
            )


        except Exception as e:

            raise HTTPException(

                status_code=400,

                detail=f"File extraction failed: {str(e)}"

            )



        if not extracted_text.strip():

            raise HTTPException(

                status_code=400,

                detail="No readable text found"

            )



        request = QuestionGeneratorRequest(

            source_type="material",

            topic=None,

            material_content=extracted_text,

            question_type=question_type,

            difficulty=difficulty,

            number_of_questions=number_of_questions,

            total_marks=total_marks

        )



        result = generate_questions_with_ai(
            request
        )


        return result



    finally:


        if os.path.exists(
            temp_filename
        ):

            os.remove(
                temp_filename
            )