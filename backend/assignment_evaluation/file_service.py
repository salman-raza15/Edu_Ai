import io

from fastapi import UploadFile
from pypdf import PdfReader
from docx import Document


# =========================================
# PDF TEXT EXTRACTION
# =========================================

def extract_pdf_text(file_bytes: bytes) -> str:

    pdf_file = io.BytesIO(file_bytes)

    reader = PdfReader(pdf_file)

    text_parts = []

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text_parts.append(page_text)

    return "\n".join(text_parts).strip()


# =========================================
# DOCX TEXT EXTRACTION
# =========================================

def extract_docx_text(file_bytes: bytes) -> str:

    docx_file = io.BytesIO(file_bytes)

    document = Document(docx_file)

    text_parts = []

    for paragraph in document.paragraphs:

        if paragraph.text.strip():
            text_parts.append(paragraph.text)

    return "\n".join(text_parts).strip()


# =========================================
# PLAIN TEXT / CODE EXTRACTION
# =========================================

def extract_plain_text(file_bytes: bytes) -> str:

    try:

        return file_bytes.decode(
            "utf-8"
        ).strip()

    except UnicodeDecodeError:

        return file_bytes.decode(
            "latin-1"
        ).strip()


# =========================================
# MAIN DYNAMIC FILE EXTRACTOR
# =========================================

async def extract_text(
    uploaded_file: UploadFile
) -> str:

    if uploaded_file is None:
        raise ValueError(
            "File is required."
        )

    if not uploaded_file.filename:
        raise ValueError(
            "File name is missing."
        )


    # Read uploaded file dynamically
    file_bytes = await uploaded_file.read()


    if not file_bytes:
        raise ValueError(
            f"{uploaded_file.filename} is empty."
        )


    # Get extension dynamically
    file_extension = (
        uploaded_file.filename
        .rsplit(".", 1)[-1]
        .lower()
        if "." in uploaded_file.filename
        else ""
    )


    # =====================================
    # PDF
    # =====================================

    if file_extension == "pdf":

        text = extract_pdf_text(
            file_bytes
        )


    # =====================================
    # DOCX
    # =====================================

    elif file_extension == "docx":

        text = extract_docx_text(
            file_bytes
        )


    # =====================================
    # TEXT / PROGRAMMING FILES
    # =====================================

    elif file_extension in {
        "txt",
        "py",
        "java",
        "cpp",
        "c",
        "html",
        "css",
        "js",
        "json",
        "sql",
        "md"
    }:

        text = extract_plain_text(
            file_bytes
        )


    # =====================================
    # UNSUPPORTED FILE
    # =====================================

    else:

        raise ValueError(
            f"Unsupported file type: .{file_extension}"
        )


    # =====================================
    # CHECK EXTRACTED CONTENT
    # =====================================

    if not text.strip():

        raise ValueError(
            f"No readable text found in "
            f"{uploaded_file.filename}"
        )


    return text