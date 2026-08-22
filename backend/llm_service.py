import os
import json
import time

from dotenv import load_dotenv
from groq import Groq


# ============================================================
# ENVIRONMENT SETUP
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ENV_PATH = os.path.join(
    BASE_DIR,
    ".env"
)

load_dotenv(ENV_PATH)

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        "GROQ_API_KEY not found. "
        "Please add GROQ_API_KEY to Render Environment Variables "
        "or backend/.env for local development."
    )


# ============================================================
# GROQ CLIENT
# ============================================================

client = Groq(
    api_key=api_key,
    timeout=60.0
)

MODEL_NAME = "openai/gpt-oss-20b"


# ============================================================
# BASIC LLM FUNCTION
# ============================================================

def generate_response(
    prompt: str,
    temperature: float = 0.3,
    json_mode: bool = False,
    max_tokens: int = 2000
) -> str:

    if not prompt or not prompt.strip():
        raise ValueError(
            "LLM prompt cannot be empty."
        )

    last_error = None

    # --------------------------------------------------------
    # Retry up to 3 times
    # --------------------------------------------------------

    for attempt in range(3):

        try:

            request_data = {
                "model": MODEL_NAME,

                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                "temperature": temperature,

                "max_tokens": max_tokens
            }

            # ------------------------------------------------
            # JSON MODE
            # ------------------------------------------------

            if json_mode:

                request_data["response_format"] = {
                    "type": "json_object"
                }

            response = client.chat.completions.create(
                **request_data
            )

            # ------------------------------------------------
            # Validate choices
            # ------------------------------------------------

            if not response:
                raise RuntimeError(
                    "Groq returned no response."
                )

            if not response.choices:
                raise RuntimeError(
                    "Groq returned no response choices."
                )

            message = response.choices[0].message

            if not message:
                raise RuntimeError(
                    "Groq returned an empty message."
                )

            content = message.content

            # ------------------------------------------------
            # Empty response
            # ------------------------------------------------

            if content is None:
                raise RuntimeError(
                    "Groq returned an empty response."
                )

            content = str(content).strip()

            if not content:

                raise RuntimeError(
                    "Groq returned an empty response."
                )

            print(
                f"Groq response received successfully "
                f"on attempt {attempt + 1}."
            )

            return content

        except Exception as e:

            last_error = e

            print(
                f"Groq attempt {attempt + 1} failed:",
                repr(e)
            )

            # -----------------------------------------------
            # Wait before retry
            # -----------------------------------------------

            if attempt < 2:
                time.sleep(1.5)

    # --------------------------------------------------------
    # All retries failed
    # --------------------------------------------------------

    raise RuntimeError(
        f"Groq returned no usable response after 3 attempts: "
        f"{last_error}"
    )


# ============================================================
# ROBUST JSON PARSER
# ============================================================

def parse_json_response(
    response: str
):

    if not response:
        return {}

    response = response.strip()

    # --------------------------------------------------------
    # Remove markdown fences
    # --------------------------------------------------------

    if response.startswith("```json"):

        response = response[
            len("```json"):
        ]

    elif response.startswith("```"):

        response = response[
            len("```"):
        ]

    if response.endswith("```"):

        response = response[
            :-3
        ]

    response = response.strip()

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:

        return json.loads(
            response
        )

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Find JSON object
    # --------------------------------------------------------

    start = response.find("{")
    end = response.rfind("}")

    if start != -1 and end != -1:

        json_text = response[
            start:end + 1
        ]

        try:

            return json.loads(
                json_text
            )

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # Find JSON array
    # --------------------------------------------------------

    start = response.find("[")
    end = response.rfind("]")

    if start != -1 and end != -1:

        json_text = response[
            start:end + 1
        ]

        try:

            return json.loads(
                json_text
            )

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # Parsing failed
    # --------------------------------------------------------

    print(
        "JSON parsing failed. Raw response:"
    )

    print(response)

    return {
        "raw_response": response
    }


# ============================================================
# RESUME ANALYSIS
# ============================================================

def analyze_resume(
    resume_text: str
):

    prompt = f"""
You are an expert technical recruiter and resume analyst.

Analyze the candidate resume carefully.

RESUME:
-------------------------
{resume_text}
-------------------------

Return ONLY valid JSON.

Use exactly this structure:

{{
    "summary": "Short professional summary",

    "skills": [
        "skill 1",
        "skill 2",
        "skill 3"
    ],

    "projects": [
        {{
            "name": "Project name",
            "description": "Short project description"
        }}
    ],

    "experience": [
        {{
            "company": "Company name",
            "role": "Role",
            "description": "Short description"
        }}
    ],

    "education": [
        {{
            "degree": "Degree",
            "institution": "Institution",
            "details": "Relevant details"
        }}
    ],

    "strengths": [
        "Strength 1",
        "Strength 2"
    ],

    "areas_to_improve": [
        "Improvement 1",
        "Improvement 2"
    ]
}}
"""

    response = generate_response(
        prompt,
        temperature=0.2,
        json_mode=True,
        max_tokens=1800
    )

    result = parse_json_response(
        response
    )

    if not isinstance(
        result,
        dict
    ):
        return {}

    return result


# ============================================================
# GENERATE INTERVIEW QUESTIONS
# ============================================================

def generate_interview_questions(
    resume_text: str,
    num_questions: int = 5
):

    prompt = f"""
You are an expert technical interviewer.

Analyze the candidate resume and create exactly
{num_questions} interview questions.

The questions should be based on the candidate's actual
skills, projects, education and experience.

Include:

1. Resume-based questions
2. Project-based questions
3. Technical questions
4. AI/ML questions
5. Programming/CS fundamentals

RESUME:
-------------------------
{resume_text}
-------------------------

Return ONLY valid JSON.

Use exactly:

{{
    "questions": [
        {{
            "question": "Question text",
            "category": "Technical"
        }}
    ]
}}

There must be exactly {num_questions} questions.
"""

    response = generate_response(
        prompt,
        temperature=0.4,
        json_mode=True,
        max_tokens=1500
    )

    result = parse_json_response(
        response
    )

    if (
        isinstance(result, dict)
        and isinstance(
            result.get("questions"),
            list
        )
    ):

        return result["questions"]

    return []


# ============================================================
# EVALUATE INTERVIEW ANSWER
# ============================================================

def evaluate_answer(
    question: str,
    answer: str,
    resume_text: str = ""
):

    prompt = f"""
You are an expert AI/ML technical interviewer.

Evaluate ONLY the candidate's answer to the exact question.

QUESTION:
{question}

CANDIDATE ANSWER:
{answer}

CANDIDATE RESUME:
{resume_text}

Evaluate:

1. Technical Accuracy
2. Clarity
3. Depth
4. Relevance

Every score must be between 0 and 10.

Also provide:

- strengths
- areas_to_improve
- overall_feedback

IMPORTANT:

Keep feedback concise.

Do NOT write a very long explanation.

Return ONLY valid JSON.

Use exactly:

{{
    "technical_accuracy": 0,
    "clarity": 0,
    "depth": 0,
    "relevance": 0,
    "strengths": [],
    "areas_to_improve": [],
    "overall_feedback": ""
}}
"""

    response = generate_response(
        prompt,
        temperature=0.2,
        json_mode=True,
        max_tokens=1200
    )

    result = parse_json_response(
        response
    )

    if not isinstance(
        result,
        dict
    ):
        result = {}

    # --------------------------------------------------------
    # SAFE SCORE
    # --------------------------------------------------------

    def safe_score(value):

        try:
            value = float(value)

        except Exception:
            return 0

        return round(
            max(
                0,
                min(
                    10,
                    value
                )
            ),
            1
        )

    technical_accuracy = safe_score(
        result.get(
            "technical_accuracy",
            0
        )
    )

    clarity = safe_score(
        result.get(
            "clarity",
            0
        )
    )

    depth = safe_score(
        result.get(
            "depth",
            0
        )
    )

    relevance = safe_score(
        result.get(
            "relevance",
            0
        )
    )

    overall_score = round(
        (
            technical_accuracy
            + clarity
            + depth
            + relevance
        ) / 4,
        2
    )

    strengths = result.get(
        "strengths",
        []
    )

    weaknesses = result.get(
        "areas_to_improve",
        []
    )

    if not isinstance(
        strengths,
        list
    ):
        strengths = []

    if not isinstance(
        weaknesses,
        list
    ):
        weaknesses = []

    return {

        "score":
            overall_score,

        "technical_accuracy":
            technical_accuracy,

        "clarity":
            clarity,

        "depth":
            depth,

        "relevance":
            relevance,

        "strengths":
            strengths,

        "weaknesses":
            weaknesses,

        "feedback":
            result.get(
                "overall_feedback",
                ""
            ),

        "ideal_answer":
            ""
    }


# ============================================================
# FOLLOW-UP QUESTION
# ============================================================

def generate_follow_up_question(
    question: str,
    answer: str,
    resume_text: str = ""
):

    prompt = f"""
You are conducting a professional technical interview.

PREVIOUS QUESTION:
{question}

CANDIDATE ANSWER:
{answer}

CANDIDATE RESUME:
{resume_text}

Generate ONE meaningful follow-up technical question.

Requirements:

1. Test deeper understanding.
2. Relate it to the candidate's answer.
3. Do not repeat the previous question.
4. Keep it concise.
5. Prefer AI/ML, project, programming or CS concepts.

Return ONLY the question text.
"""

    try:

        response = generate_response(
            prompt,
            temperature=0.4,
            json_mode=False,
            max_tokens=300
        )

        response = response.strip()

        if response:
            return response

    except Exception as e:

        print(
            "Follow-up question generation failed:",
            repr(e)
        )

    # --------------------------------------------------------
    # Guaranteed fallback
    # --------------------------------------------------------

    return (
        "Can you explain the technical reasoning behind "
        "your approach and discuss one limitation or "
        "trade-off you would consider?"
    )


# ============================================================
# GENERATE NEXT INTERVIEW QUESTION
# ============================================================

def generate_next_question(
    resume_text: str,
    previous_question: str,
    candidate_answer: str,
    evaluation: dict,
    interview_type: str = "AI/ML",
    asked_questions=None,
    asked_topics=None
):

    if asked_questions is None:
        asked_questions = []

    if asked_topics is None:
        asked_topics = []

    previous_questions_text = "\n".join(
        [
            f"- {question}"
            for question in asked_questions
        ]
    )

    if not previous_questions_text:
        previous_questions_text = "- None"

    prompt = f"""
You are an expert AI/ML technical interviewer.

INTERVIEW TYPE:
{interview_type}

CANDIDATE RESUME:
-------------------------
{resume_text}
-------------------------

PREVIOUS QUESTION:
{previous_question}

CANDIDATE ANSWER:
{candidate_answer}

EVALUATION:
{json.dumps(
    evaluation,
    ensure_ascii=False
)}

QUESTIONS ALREADY ASKED:
{previous_questions_text}

Generate EXACTLY ONE NEXT interview question.

Rules:

1. Do NOT repeat previous questions.
2. Continue logically from the interview.
3. Consider the candidate's answer.
4. If the answer is weak, test the same concept deeper.
5. If the answer is strong, increase difficulty slightly.
6. Prefer AI/ML, project, programming or CS questions.
7. Do not ask for an introduction.
8. Return ONLY the question text.
9. Do NOT return JSON.
10. Do not include "Question:" or any heading.
"""

    # --------------------------------------------------------
    # Primary generation
    # --------------------------------------------------------

    try:

        next_question = generate_response(
            prompt,
            temperature=0.4,
            json_mode=False,
            max_tokens=300
        )

        next_question = next_question.strip()

        # -----------------------------------------------
        # Remove quotes
        # -----------------------------------------------

        if (
            next_question.startswith('"')
            and next_question.endswith('"')
        ):

            next_question = next_question[
                1:-1
            ].strip()

        # -----------------------------------------------
        # Remove common prefixes
        # -----------------------------------------------

        prefixes = [
            "Question:",
            "question:",
            "Next Question:",
            "Next question:",
            "NEXT QUESTION:"
        ]

        for prefix in prefixes:

            if next_question.startswith(
                prefix
            ):

                next_question = next_question[
                    len(prefix):
                ].strip()

        if next_question:

            print(
                "Next interview question generated successfully."
            )

            return next_question

    except Exception as e:

        print(
            "Next question generation failed:",
            repr(e)
        )

    # --------------------------------------------------------
    # FALLBACK QUESTION
    # --------------------------------------------------------

    fallback_question = generate_follow_up_question(
        previous_question,
        candidate_answer,
        resume_text
    )

    if fallback_question:

        return fallback_question

    # --------------------------------------------------------
    # Absolute fallback
    # --------------------------------------------------------

    return (
        "What are the main limitations of the approach "
        "you described, and how would you improve it?"
    )


# ============================================================
# TEST GROQ CONNECTION
# ============================================================

def test_groq_connection():

    try:

        response = generate_response(
            "Reply with exactly: Groq connection successful",
            temperature=0,
            json_mode=False,
            max_tokens=50
        )

        return {
            "success": True,
            "response": response
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }