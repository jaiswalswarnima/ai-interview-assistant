import json
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pymupdf

from backend.resume_parser import parse_resume
from backend.llm_service import (
    analyze_resume,
    generate_response,
    generate_next_question,
    evaluate_answer
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Interview Assistant",
    description="AI-powered AI/ML interview preparation and evaluation system",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# INTERVIEW SESSION STORAGE
# ============================================================

interview_sessions = {}


# ============================================================
# REQUEST MODELS
# ============================================================

class InterviewStartRequest(BaseModel):
    resume_text: str
    interview_type: str = "AI/ML"


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "AI Interview Assistant API is running"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


# ============================================================
# UPLOAD RESUME
# ============================================================

@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...)
):

    # --------------------------------------------------------
    # Validate file
    # --------------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    # --------------------------------------------------------
    # Read PDF
    # --------------------------------------------------------

    try:

        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded PDF is empty."
            )

        pdf_document = pymupdf.open(
            stream=file_content,
            filetype="pdf"
        )

        resume_pages = []

        for page in pdf_document:

            page_text = page.get_text()

            if page_text:
                resume_pages.append(
                    page_text
                )

        pdf_document.close()

        resume_text = "\n".join(
            resume_pages
        ).strip()

    except HTTPException:
        raise

    except Exception as e:

        print(
            "PDF extraction error:",
            repr(e)
        )

        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF: {str(e)}"
        )

    # --------------------------------------------------------
    # Validate extracted text
    # --------------------------------------------------------

    if not resume_text:

        raise HTTPException(
            status_code=400,
            detail="Could not extract text from the PDF."
        )

    # --------------------------------------------------------
    # Local resume parser
    # --------------------------------------------------------

    try:

        resume_data = parse_resume(
            resume_text
        )

    except Exception as e:

        print(
            "Resume parser error:",
            repr(e)
        )

        resume_data = {
            "error": "Resume parsing failed",
            "details": str(e)
        }

    # --------------------------------------------------------
    # AI resume analysis
    #
    # This is done ONLY once during upload.
    # --------------------------------------------------------

    try:

        ai_analysis = analyze_resume(
            resume_text
        )

    except Exception as e:

        print(
            "Resume AI analysis error:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=f"Resume AI analysis failed: {str(e)}"
        )

    # --------------------------------------------------------
    # Return resume result
    # --------------------------------------------------------

    return {

        "filename":
            file.filename,

        "message":
            "Resume analyzed successfully",

        "resume_text":
            resume_text,

        "resume_data":
            resume_data,

        "ai_analysis":
            ai_analysis
    }


# ============================================================
# START INTERVIEW
# ============================================================

@app.post("/start-interview")
async def start_interview(
    request: InterviewStartRequest
):

    resume_text = request.resume_text.strip()

    if not resume_text:

        raise HTTPException(
            status_code=400,
            detail="Resume text is empty."
        )

    total_questions = 5

    # --------------------------------------------------------
    # Generate first question
    #
    # IMPORTANT:
    # We DO NOT call analyze_resume() again.
    # --------------------------------------------------------

    first_question_prompt = f"""
You are an expert AI/ML technical interviewer.

You are starting a technical interview.

INTERVIEW TYPE:
{request.interview_type}

CANDIDATE RESUME:
-------------------------
{resume_text}
-------------------------

Generate EXACTLY ONE first interview question.

Rules:

1. The question must be directly related to the candidate's resume.
2. Prefer the candidate's strongest AI/ML project or technical skill.
3. Ask a technical interview question.
4. Do not ask "Tell me about yourself".
5. Do not provide an answer.
6. Do not provide feedback.
7. Return ONLY the question text.
"""

    try:

        first_question = generate_response(
            first_question_prompt,
            temperature=0.4,
            json_mode=False,
            max_tokens=400
        ).strip()

    except Exception as e:

        print(
            "First question generation error:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=f"Could not generate first interview question: {str(e)}"
        )

    # --------------------------------------------------------
    # Clean question
    # --------------------------------------------------------

    if (
        first_question.startswith('"')
        and first_question.endswith('"')
    ):

        first_question = first_question[
            1:-1
        ].strip()

    if not first_question:

        raise HTTPException(
            status_code=500,
            detail="AI returned an empty first question."
        )

    # --------------------------------------------------------
    # Create session
    # --------------------------------------------------------

    session_id = str(
        uuid.uuid4()
    )

    interview_sessions[session_id] = {

        "resume_text":
            resume_text,

        "interview_type":
            request.interview_type,

        "questions": [
            first_question
        ],

        "current_question":
            0,

        "total_questions":
            total_questions,

        "answers": [],

        "evaluations": [],

        "asked_questions": [
            first_question
        ],

        "asked_topics": []
    }

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {

        "message":
            "Interview started successfully",

        "session_id":
            session_id,

        "interview_type":
            request.interview_type,

        "total_questions":
            total_questions,

        "current_question_number":
            1,

        "question":
            first_question
    }


# ============================================================
# SUBMIT ANSWER
# ============================================================

@app.post("/submit-answer")
async def submit_answer(
    request: AnswerRequest
):

    # --------------------------------------------------------
    # Check session
    # --------------------------------------------------------

    if request.session_id not in interview_sessions:

        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )

    session = interview_sessions[
        request.session_id
    ]

    answer = request.answer.strip()

    if not answer:

        raise HTTPException(
            status_code=400,
            detail="Answer cannot be empty."
        )

    current_index = session[
        "current_question"
    ]

    total_questions = session[
        "total_questions"
    ]

    # --------------------------------------------------------
    # Check completion
    # --------------------------------------------------------

    if current_index >= total_questions:

        raise HTTPException(
            status_code=400,
            detail="Interview already completed."
        )

    # --------------------------------------------------------
    # Get EXACT current question
    # --------------------------------------------------------

    current_question = session[
        "questions"
    ][current_index]

    # ========================================================
    # EVALUATE ANSWER
    # ========================================================

    try:

        evaluation = evaluate_answer(

            question=
                current_question,

            answer=
                answer,

            resume_text=
                session["resume_text"]
        )

    except Exception as e:

        print(
            "Evaluation generation error:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=f"AI evaluation failed: {str(e)}"
        )

    # --------------------------------------------------------
    # Make sure evaluation is a dictionary
    # --------------------------------------------------------

    if not isinstance(
        evaluation,
        dict
    ):

        evaluation = {

            "score":
                0,

            "technical_accuracy":
                0,

            "clarity":
                0,

            "depth":
                0,

            "relevance":
                0,

            "strengths":
                [],

            "weaknesses":
                [
                    "Evaluation response was invalid."
                ],

            "feedback":
                "AI evaluation response was invalid.",

            "ideal_answer":
                ""
        }

    # ========================================================
    # NORMALIZE SCORES
    # ========================================================

    def safe_score(value):

        try:

            value = float(
                value
            )

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
            2
        )

    evaluation["technical_accuracy"] = safe_score(
        evaluation.get(
            "technical_accuracy",
            0
        )
    )

    evaluation["clarity"] = safe_score(
        evaluation.get(
            "clarity",
            0
        )
    )

    evaluation["depth"] = safe_score(
        evaluation.get(
            "depth",
            0
        )
    )

    evaluation["relevance"] = safe_score(
        evaluation.get(
            "relevance",
            0
        )
    )

    # --------------------------------------------------------
    # Calculate overall question score
    # --------------------------------------------------------

    evaluation["score"] = round(
        (
            evaluation["technical_accuracy"]
            + evaluation["clarity"]
            + evaluation["depth"]
            + evaluation["relevance"]
        ) / 4,
        2
    )

    # --------------------------------------------------------
    # Ensure arrays
    # --------------------------------------------------------

    if not isinstance(
        evaluation.get("strengths"),
        list
    ):

        evaluation["strengths"] = []

    if not isinstance(
        evaluation.get("weaknesses"),
        list
    ):

        evaluation["weaknesses"] = []

    # ========================================================
    # STORE ANSWER
    # ========================================================

    session["answers"].append({

        "question":
            current_question,

        "answer":
            answer
    })

    # ========================================================
    # STORE EVALUATION
    # ========================================================

    session["evaluations"].append(
        evaluation
    )

    answered_questions = len(
        session["answers"]
    )

    # ========================================================
    # INTERVIEW COMPLETED
    # ========================================================

    if answered_questions >= total_questions:

        final_result = build_final_result(
            session
        )

        return {

            "message":
                "Interview completed",

            "session_id":
                request.session_id,

            "evaluation":
                evaluation,

            "interview_completed":
                True,

            "current_question_number":
                total_questions,

            "total_questions":
                total_questions,

            "final_result":
                final_result
        }

    # ========================================================
    # GENERATE NEXT QUESTION
    # ========================================================

    try:

        next_question = generate_next_question(

            resume_text=
                session["resume_text"],

            previous_question=
                current_question,

            candidate_answer=
                answer,

            evaluation=
                evaluation,

            interview_type=
                session["interview_type"],

            asked_questions=
                session["asked_questions"],

            asked_topics=
                session["asked_topics"]
        )

    except Exception as e:

        print(
            "Next question generation error:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=f"Could not generate next question: {str(e)}"
        )

    # --------------------------------------------------------
    # Handle dictionary response just in case
    # --------------------------------------------------------

    if isinstance(
        next_question,
        dict
    ):

        next_question = next_question.get(
            "question",
            ""
        )

    next_question = str(
        next_question
    ).strip()

    if not next_question:

        raise HTTPException(
            status_code=500,
            detail="Could not generate next interview question."
        )

    # ========================================================
    # STORE NEXT QUESTION
    # ========================================================

    session["asked_questions"].append(
        next_question
    )

    session["questions"].append(
        next_question
    )

    session["current_question"] += 1

    next_question_number = (
        session["current_question"] + 1
    )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "message":
            "Answer evaluated successfully",

        "session_id":
            request.session_id,

        "evaluation":
            evaluation,

        "interview_completed":
            False,

        "current_question_number":
            next_question_number,

        "total_questions":
            total_questions,

        "next_question":
            next_question
    }


# ============================================================
# BUILD FINAL RESULT
# ============================================================

def build_final_result(
    session
):

    evaluations = session[
        "evaluations"
    ]

    total_questions = session[
        "total_questions"
    ]

    # --------------------------------------------------------
    # No evaluations
    # --------------------------------------------------------

    if not evaluations:

        return {

            "total_questions":
                total_questions,

            "total_answered":
                0,

            "total_score":
                0,

            "average_score":
                0,

            "average_technical":
                0,

            "average_clarity":
                0,

            "average_depth":
                0,

            "average_relevance":
                0,

            "question_wise_results":
                []
        }

    # --------------------------------------------------------
    # Score lists
    # --------------------------------------------------------

    scores = []

    technical_scores = []

    clarity_scores = []

    depth_scores = []

    relevance_scores = []

    question_wise_results = []

    # --------------------------------------------------------
    # Process each question
    # --------------------------------------------------------

    for index, evaluation in enumerate(
        evaluations
    ):

        score = float(
            evaluation.get(
                "score",
                0
            )
        )

        technical = float(
            evaluation.get(
                "technical_accuracy",
                0
            )
        )

        clarity = float(
            evaluation.get(
                "clarity",
                0
            )
        )

        depth = float(
            evaluation.get(
                "depth",
                0
            )
        )

        relevance = float(
            evaluation.get(
                "relevance",
                0
            )
        )

        scores.append(
            score
        )

        technical_scores.append(
            technical
        )

        clarity_scores.append(
            clarity
        )

        depth_scores.append(
            depth
        )

        relevance_scores.append(
            relevance
        )

        # ----------------------------------------------------
        # Question and answer
        # ----------------------------------------------------

        question = ""

        candidate_answer = ""

        if index < len(
            session["answers"]
        ):

            question = session[
                "answers"
            ][index].get(
                "question",
                ""
            )

            candidate_answer = session[
                "answers"
            ][index].get(
                "answer",
                ""
            )

        # ----------------------------------------------------
        # Question-wise result
        # ----------------------------------------------------

        question_wise_results.append({

            "question_number":
                index + 1,

            "question":
                question,

            "answer":
                candidate_answer,

            "score":
                round(
                    score,
                    2
                ),

            "technical_accuracy":
                round(
                    technical,
                    2
                ),

            "clarity":
                round(
                    clarity,
                    2
                ),

            "depth":
                round(
                    depth,
                    2
                ),

            "relevance":
                round(
                    relevance,
                    2
                ),

            "strengths":
                evaluation.get(
                    "strengths",
                    []
                ),

            "weaknesses":
                evaluation.get(
                    "weaknesses",
                    []
                ),

            "feedback":
                evaluation.get(
                    "feedback",
                    ""
                ),

            "ideal_answer":
                evaluation.get(
                    "ideal_answer",
                    ""
                )
        })

    # --------------------------------------------------------
    # Count
    # --------------------------------------------------------

    count = len(
        scores
    )

    # --------------------------------------------------------
    # Averages
    # --------------------------------------------------------

    average_score = round(
        sum(scores) / count,
        2
    )

    average_technical = round(
        sum(technical_scores) / count,
        2
    )

    average_clarity = round(
        sum(clarity_scores) / count,
        2
    )

    average_depth = round(
        sum(depth_scores) / count,
        2
    )

    average_relevance = round(
        sum(relevance_scores) / count,
        2
    )

    total_score = round(
        sum(scores),
        2
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    return {

        "total_questions":
            total_questions,

        "total_answered":
            len(
                session["answers"]
            ),

        "total_score":
            total_score,

        "average_score":
            average_score,

        "average_technical":
            average_technical,

        "average_clarity":
            average_clarity,

        "average_depth":
            average_depth,

        "average_relevance":
            average_relevance,

        "question_wise_results":
            question_wise_results
    }


# ============================================================
# GET INTERVIEW SESSION
# ============================================================

@app.get("/interview/{session_id}")
async def get_interview(
    session_id: str
):

    if session_id not in interview_sessions:

        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )

    session = interview_sessions[
        session_id
    ]

    return {

        "session_id":
            session_id,

        "interview_type":
            session["interview_type"],

        "total_questions":
            session["total_questions"],

        "current_question_number":
            session["current_question"] + 1,

        "questions":
            session["questions"],

        "asked_questions":
            session["asked_questions"],

        "answers":
            session["answers"],

        "evaluations":
            session["evaluations"]
    }


# ============================================================
# GET FINAL INTERVIEW RESULT
# ============================================================

@app.get(
    "/interview/{session_id}/result"
)
async def get_interview_result(
    session_id: str
):

    if session_id not in interview_sessions:

        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )

    session = interview_sessions[
        session_id
    ]

    evaluations = session[
        "evaluations"
    ]

    total_questions = session[
        "total_questions"
    ]

    # --------------------------------------------------------
    # Still in progress
    # --------------------------------------------------------

    if len(evaluations) < total_questions:

        return {

            "message":
                "Interview is still in progress.",

            "completed_questions":
                len(evaluations),

            "total_questions":
                total_questions
        }

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    result = build_final_result(
        session
    )

    return {

        "message":
            "Interview result generated successfully",

        "session_id":
            session_id,

        "interview_type":
            session["interview_type"],

        **result
    }