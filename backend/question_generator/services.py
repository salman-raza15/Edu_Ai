import json
import re

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

from .schemas import QuestionGeneratorRequest


# ==========================================
# AZURE AI FOUNDRY CONNECTION
# ==========================================

PROJECT_ENDPOINT = (
    "https://eduai-question-generato-resource.services.ai.azure.com/api/projects/eduai-question-generator"
)

AGENT_NAME = "question-generator-agent"

AGENT_VERSION = "3"


def run_agent(prompt: str):

    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential()
    )

    openai_client = project_client.get_openai_client()

    response = openai_client.responses.create(
        input=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        extra_body={
            "agent_reference": {
                "name": AGENT_NAME,
                "type": "agent_reference"
            }
        }
    )

    return response.output_text


# ==========================================
# CLEAN AI JSON RESPONSE
# ==========================================

def clean_json_response(text: str):

    if not text:
        raise ValueError(
            "AI returned empty response"
        )

    text = text.strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```",
        "",
        text
    )

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "No JSON found"
        )

    return json.loads(
        text[start:end + 1]
    )


# ==========================================
# REMOVE LETTERHEAD INSTRUCTION LEAK
# ==========================================

def sanitize_questions(data):

    cleaned = data.copy()

    cleaned_questions = []

    for q in data.get("questions", []):

        question = q.get(
            "question",
            ""
        )

        # Remove everything before actual question

        patterns = [
            r".*?(?=What is)",
            r".*?(?=Which)",
            r".*?(?=Explain)",
            r".*?(?=Define)",
            r".*?(?=Describe)"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                question,
                flags=re.DOTALL
            )

            if match:

                question = question[
                    match.end():
                ]

                break

        remove_words = [
            "Create a professional academic question paper header.",
            "Create a professional letterhead.",
            "Header:",
            "Footer:",
            "Body:",
            "Information section:",
            "Add a placeholder logo area",
            "Add university name",
            "Add department name",
            "Add a blue horizontal line",
            "Powered by EduAI Assessment Platform"
        ]

        for word in remove_words:

            question = question.replace(
                word,
                ""
            )

        cleaned_questions.append({

            "question_number": q.get(
                "question_number"
            ),

            "type": q.get(
                "type"
            ),

            "question": question.strip(),

            "options": q.get(
                "options",
                []
            ),

            "correct_answer": q.get(
                "correct_answer",
                ""
            ),

            "marks": q.get(
                "marks"
            )

        })

    cleaned["questions"] = cleaned_questions

    return cleaned


# ==========================================
# GENERATE QUESTIONS
# ==========================================

def generate_questions_with_ai(
    request: QuestionGeneratorRequest
):

    prompt = f"""

Generate assessment questions.

Topic:

{request.topic}


Material:

{request.material_content}


Question Type:

{request.question_type}


Difficulty:

{request.difficulty}


Number of Questions:

{request.number_of_questions}


Total Marks:

{request.total_marks}


STRICT RULES:

Return ONLY JSON.

Never include:

- letterhead instructions
- document formatting instructions
- header information
- footer information
- logo instructions
- PDF instructions


The questions array must contain ONLY actual assessment questions.


Required JSON:

{{
"topic":"",
"difficulty":"",
"total_questions":0,
"total_marks":0,
"questions":[
{{
"question_number":1,
"type":"",
"question":"",
"options":[],
"correct_answer":"",
"marks":0
}}
]
}}

"""

    response = run_agent(
        prompt
    )

    result = clean_json_response(
        response
    )

    result = sanitize_questions(
        result
    )

    required_keys = [
        "topic",
        "difficulty",
        "total_questions",
        "total_marks",
        "questions"
    ]

    for key in required_keys:

        if key not in result:

            raise ValueError(
                f"Missing key: {key}"
            )

    return result