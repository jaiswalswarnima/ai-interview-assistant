import { useState } from "react";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

/* =========================================================
   EVALUATION NORMALIZER
========================================================= */

const normalizeEvaluation = (payload) => {

  if (!payload) {
    return null;
  }

  // -------------------------------------------------------
  // STRING
  // -------------------------------------------------------

  if (typeof payload === "string") {

    let text = payload.trim();

    text = text
      .replace(/^```json\s*/i, "")
      .replace(/^```\s*/i, "")
      .replace(/\s*```$/i, "")
      .trim();

    try {

      const parsed = JSON.parse(text);

      return normalizeEvaluation(parsed);

    } catch (error) {
      // Continue
    }

    const firstBrace =
      text.indexOf("{");

    const lastBrace =
      text.lastIndexOf("}");

    if (
      firstBrace !== -1 &&
      lastBrace !== -1
    ) {

      try {

        const parsed =
          JSON.parse(
            text.slice(
              firstBrace,
              lastBrace + 1
            )
          );

        return normalizeEvaluation(
          parsed
        );

      } catch (error) {
        // Continue
      }
    }

    return null;
  }


  // -------------------------------------------------------
  // OBJECT
  // -------------------------------------------------------

  if (
    typeof payload !== "object" ||
    Array.isArray(payload)
  ) {
    return null;
  }


  // -------------------------------------------------------
  // NESTED evaluation
  // -------------------------------------------------------

  if (
    payload.evaluation !== undefined
  ) {

    const nested =
      normalizeEvaluation(
        payload.evaluation
      );

    if (nested) {
      return nested;
    }
  }


  // -------------------------------------------------------
  // OTHER POSSIBLE WRAPPERS
  // -------------------------------------------------------

  for (
    const key of [
      "result",
      "response",
      "data"
    ]
  ) {

    if (
      payload[key] !== undefined
    ) {

      const nested =
        normalizeEvaluation(
          payload[key]
        );

      if (nested) {

        const hasScore =
          nested.score !== null &&
          nested.score !== undefined;

        if (hasScore) {
          return nested;
        }
      }
    }
  }


  // -------------------------------------------------------
  // DIRECT EVALUATION
  // -------------------------------------------------------

  const hasEvaluationFields =
    payload.score !== undefined ||
    payload.technical_accuracy !== undefined ||
    payload.clarity !== undefined ||
    payload.depth !== undefined ||
    payload.relevance !== undefined;

  if (!hasEvaluationFields) {
    return null;
  }


  return {

    score:
      Number(
        payload.score ?? 0
      ),

    technical_accuracy:
      Number(
        payload.technical_accuracy ?? 0
      ),

    clarity:
      Number(
        payload.clarity ?? 0
      ),

    depth:
      Number(
        payload.depth ?? 0
      ),

    relevance:
      Number(
        payload.relevance ?? 0
      ),

    strengths:
      Array.isArray(
        payload.strengths
      )
        ? payload.strengths
        : [],

    weaknesses:
      Array.isArray(
        payload.weaknesses
      )
        ? payload.weaknesses
        : [],

    feedback:
      typeof payload.feedback === "string"
        ? payload.feedback
        : "",

    ideal_answer:
      typeof payload.ideal_answer === "string"
        ? payload.ideal_answer
        : ""
  };
};


/* =========================================================
   APP
========================================================= */

function App() {

  const [resumeFile, setResumeFile] =
    useState(null);

  const [resumeText, setResumeText] =
    useState("");

  const [aiAnalysis, setAiAnalysis] =
    useState(null);

  const [uploading, setUploading] =
    useState(false);

  const [starting, setStarting] =
    useState(false);

  const [submitting, setSubmitting] =
    useState(false);

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");

  const [resumeUploaded, setResumeUploaded] =
    useState(false);

  const [sessionId, setSessionId] =
    useState("");

  const [question, setQuestion] =
    useState("");

  const [answer, setAnswer] =
    useState("");

  const [currentQuestion, setCurrentQuestion] =
    useState(0);

  const [totalQuestions, setTotalQuestions] =
    useState(5);

  const [evaluation, setEvaluation] =
    useState(null);

  const [evaluations, setEvaluations] =
    useState([]);

  const [interviewStarted, setInterviewStarted] =
    useState(false);

  const [interviewCompleted, setInterviewCompleted] =
    useState(false);

  const [finalResult, setFinalResult] =
    useState(null);


  /* =====================================================
     FILE SELECTION
  ===================================================== */

  const handleFileChange = (event) => {

    const file =
      event.target.files?.[0];

    setError("");
    setSuccess("");

    if (!file) {

      setResumeFile(null);

      return;
    }

    if (
      file.type !==
      "application/pdf"
    ) {

      setError(
        "Please upload a PDF resume."
      );

      setResumeFile(null);

      return;
    }

    setResumeFile(file);

    setResumeUploaded(false);

    setResumeText("");

    setAiAnalysis(null);
  };


  /* =====================================================
     UPLOAD RESUME
  ===================================================== */

  const uploadResume = async () => {

    if (!resumeFile) {

      setError(
        "Please select your resume first."
      );

      return;
    }

    setUploading(true);

    setError("");

    setSuccess("");

    try {

      const formData =
        new FormData();

      formData.append(
        "file",
        resumeFile
      );

      const response =
        await fetch(
          `${API_URL}/upload-resume`,
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Failed to upload resume."
        );
      }

      setResumeText(
        data.resume_text || ""
      );

      setAiAnalysis(
        data.ai_analysis || null
      );

      setResumeUploaded(true);

      setSuccess(
        "Resume uploaded and analyzed successfully."
      );

    } catch (err) {

      console.error(err);

      setError(
        err.message ||
        "Failed to upload resume."
      );

    } finally {

      setUploading(false);
    }
  };


  /* =====================================================
     START INTERVIEW
  ===================================================== */

  const startInterview = async () => {

    if (!resumeText) {

      setError(
        "Please upload your resume first."
      );

      return;
    }

    if (!aiAnalysis) {

      setError(
        "Resume analysis is missing. Please upload the resume again."
      );

      return;
    }

    setStarting(true);

    setError("");

    setSuccess("");

    try {

      const response =
        await fetch(
          `${API_URL}/start-interview`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              resume_text:
                resumeText,

              interview_type:
                "AI/ML",

              ai_analysis:
                aiAnalysis,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Could not start interview."
        );
      }

      setSessionId(
        data.session_id || ""
      );

      setQuestion(
        data.question || ""
      );

      setCurrentQuestion(
        data.current_question_number ||
        1
      );

      setTotalQuestions(
        data.total_questions ||
        5
      );

      setInterviewStarted(true);

      setInterviewCompleted(false);

      setEvaluation(null);

      setEvaluations([]);

      setFinalResult(null);

      setAnswer("");

      setSuccess("");

    } catch (err) {

      console.error(err);

      setError(
        err.message ||
        "Could not start interview."
      );

    } finally {

      setStarting(false);
    }
  };


  /* =====================================================
     FETCH FINAL RESULT
  ===================================================== */

  const fetchFinalResult = async (
    id,
    fallbackEvaluations
  ) => {

    try {

      const response =
        await fetch(
          `${API_URL}/interview/${id}/result`
        );

      const data =
        await response.json();

      if (
        response.ok &&
        Array.isArray(
          data.evaluations
        )
      ) {

        return {

          totalScore:
            Number(
              data.total_score || 0
            ),

          averageScore:
            Number(
              data.average_score || 0
            ),

          averageTechnical:
            Number(
              data.average_technical || 0
            ),

          averageClarity:
            Number(
              data.average_clarity || 0
            ),

          averageDepth:
            Number(
              data.average_depth || 0
            ),

          averageRelevance:
            Number(
              data.average_relevance || 0
            ),

          evaluations:
            data.evaluations
        };
      }

      return null;

    } catch (err) {

      console.error(
        "Final result fetch error:",
        err
      );

      return null;
    }
  };


  /* =====================================================
     SUBMIT ANSWER
  ===================================================== */

  const submitAnswer = async () => {

    if (!answer.trim()) {

      setError(
        "Please write your answer before submitting."
      );

      return;
    }

    if (!sessionId) {

      setError(
        "Interview session not found."
      );

      return;
    }

    setSubmitting(true);

    setError("");

    setSuccess("");

    try {

      const response =
        await fetch(
          `${API_URL}/submit-answer`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              session_id:
                sessionId,

              answer:
                answer,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Could not evaluate answer."
        );
      }


      /* =================================================
         BACKEND ALREADY NORMALIZES EVALUATION
      ================================================= */

      const parsedEvaluation =
        normalizeEvaluation(
          data.evaluation
        );


      if (!parsedEvaluation) {

        throw new Error(
          "AI evaluation could not be parsed. Please try submitting again."
        );
      }


      /* =================================================
         STORE CURRENT EVALUATION
      ================================================= */

      const newEvaluation = {

        questionNumber:
          currentQuestion,

        score:
          Number(
            parsedEvaluation.score
          ),

        technical_accuracy:
          Number(
            parsedEvaluation
              .technical_accuracy
          ),

        clarity:
          Number(
            parsedEvaluation.clarity
          ),

        depth:
          Number(
            parsedEvaluation.depth
          ),

        relevance:
          Number(
            parsedEvaluation.relevance
          ),

        strengths:
          parsedEvaluation.strengths || [],

        weaknesses:
          parsedEvaluation.weaknesses || [],

        feedback:
          parsedEvaluation.feedback || "",

        ideal_answer:
          parsedEvaluation.ideal_answer || "",

        question:
          question,

        answer:
          answer
      };


      const updatedEvaluations =
        [
          ...evaluations,
          newEvaluation
        ];


      setEvaluations(
        updatedEvaluations
      );


      setEvaluation(
        parsedEvaluation
      );


      /* =================================================
         INTERVIEW COMPLETED
      ================================================= */

      if (
        data.interview_completed ===
        true
      ) {

        const backendResult =
          await fetchFinalResult(
            sessionId,
            updatedEvaluations
          );


        if (backendResult) {

          setFinalResult(
            backendResult
          );

        } else {

          // Local fallback
          const normalized =
            updatedEvaluations.map(
              normalizeEvaluation
            );

          const totalScore =
            normalized.reduce(
              (
                sum,
                item
              ) =>
                sum +
                Number(
                  item?.score || 0
                ),
              0
            );

          const count =
            normalized.length;

          setFinalResult({

            totalScore,

            averageScore:
              count
                ? totalScore / count
                : 0,

            averageTechnical:
              count
                ? normalized.reduce(
                    (
                      sum,
                      item
                    ) =>
                      sum +
                      Number(
                        item?.technical_accuracy ||
                        0
                      ),
                    0
                  ) / count
                : 0,

            averageClarity:
              count
                ? normalized.reduce(
                    (
                      sum,
                      item
                    ) =>
                      sum +
                      Number(
                        item?.clarity ||
                        0
                      ),
                    0
                  ) / count
                : 0,

            averageDepth:
              count
                ? normalized.reduce(
                    (
                      sum,
                      item
                    ) =>
                      sum +
                      Number(
                        item?.depth ||
                        0
                      ),
                    0
                  ) / count
                : 0,

            averageRelevance:
              count
                ? normalized.reduce(
                    (
                      sum,
                      item
                    ) =>
                      sum +
                      Number(
                        item?.relevance ||
                        0
                      ),
                    0
                  ) / count
                : 0,

            evaluations:
              updatedEvaluations
          });
        }


        setInterviewCompleted(
          true
        );

        setInterviewStarted(
          false
        );

        setAnswer("");

        return;
      }


      /* =================================================
         NEXT QUESTION
      ================================================= */

      setQuestion(
        data.next_question || ""
      );

      setCurrentQuestion(
        data.current_question_number ||
        currentQuestion + 1
      );

      setAnswer("");

    } catch (err) {

      console.error(err);

      setError(
        err.message ||
        "Could not evaluate answer."
      );

    } finally {

      setSubmitting(false);
    }
  };


  /* =====================================================
     RESTART
  ===================================================== */

  const restartInterview = () => {

    setSessionId("");

    setQuestion("");

    setAnswer("");

    setCurrentQuestion(0);

    setEvaluation(null);

    setEvaluations([]);

    setInterviewStarted(false);

    setInterviewCompleted(false);

    setFinalResult(null);

    setError("");

    setSuccess("");
  };


  /* =====================================================
     RESULT PAGE
  ===================================================== */

  if (
    interviewCompleted &&
    finalResult
  ) {

    return (

      <div className="app">

        <main className="result-page">

          <div className="result-header">

            <div className="success-icon">
              ✓
            </div>

            <h1>
              Interview Completed
            </h1>

            <p>
              Your AI/ML interview performance
              has been evaluated successfully.
            </p>

          </div>


          {/* =================================================
              OVERALL
          ================================================= */}

          <div className="overall-score-card">

            <div className="overall-label">
              Overall Score
            </div>

            <div className="overall-score">

              {Number(
                finalResult.averageScore || 0
              ).toFixed(1)}

              <span>
                /10
              </span>

            </div>

            <div className="total-score">

              Total Score:{" "}

              <strong>
                {Number(
                  finalResult.totalScore || 0
                ).toFixed(1)}
              </strong>

              {" "} / {" "}

              {finalResult.evaluations.length * 10}

            </div>

          </div>


          {/* =================================================
              PERFORMANCE
          ================================================= */}

          <div className="performance-grid">

            <div className="performance-card">

              <span>
                Technical Accuracy
              </span>

              <strong>

                {Number(
                  finalResult.averageTechnical ||
                  0
                ).toFixed(1)}

                <small>
                  /10
                </small>

              </strong>

            </div>


            <div className="performance-card">

              <span>
                Clarity
              </span>

              <strong>

                {Number(
                  finalResult.averageClarity ||
                  0
                ).toFixed(1)}

                <small>
                  /10
                </small>

              </strong>

            </div>


            <div className="performance-card">

              <span>
                Depth
              </span>

              <strong>

                {Number(
                  finalResult.averageDepth ||
                  0
                ).toFixed(1)}

                <small>
                  /10
                </small>

              </strong>

            </div>


            <div className="performance-card">

              <span>
                Relevance
              </span>

              <strong>

                {Number(
                  finalResult.averageRelevance ||
                  0
                ).toFixed(1)}

                <small>
                  /10
                </small>

              </strong>

            </div>

          </div>


          {/* =================================================
              QUESTION RESULTS
          ================================================= */}

          <section className="question-results-section">

            <div className="section-heading">

              <h2>
                Question-wise Performance
              </h2>

              <span>
                {finalResult.evaluations.length}
                {" "}Questions
              </span>

            </div>


            <div className="question-results-list">

              {finalResult.evaluations.map(
                (
                  item,
                  index
                ) => {

                  const normalized =
                    normalizeEvaluation(
                      item
                    );

                  if (!normalized) {
                    return null;
                  }

                  return (

                    <div
                      className="question-result-card"
                      key={index}
                    >

                      <div className="question-result-top">

                        <div>

                          <span className="question-number">

                            QUESTION{" "}
                            {index + 1}

                          </span>

                          <h3>

                            {item.question ||
                              `Question ${
                                index + 1
                              }`}

                          </h3>

                        </div>


                        <div className="result-score">

                          {normalized.score}

                          <span>
                            /10
                          </span>

                        </div>

                      </div>


                      {/* METRICS */}

                      <div className="result-metrics">

                        <div>

                          <span>
                            Technical Accuracy
                          </span>

                          <strong>

                            {
                              normalized
                                .technical_accuracy
                            }
                            /10

                          </strong>

                        </div>


                        <div>

                          <span>
                            Clarity
                          </span>

                          <strong>

                            {
                              normalized.clarity
                            }
                            /10

                          </strong>

                        </div>


                        <div>

                          <span>
                            Depth
                          </span>

                          <strong>

                            {
                              normalized.depth
                            }
                            /10

                          </strong>

                        </div>


                        <div>

                          <span>
                            Relevance
                          </span>

                          <strong>

                            {
                              normalized.relevance
                            }
                            /10

                          </strong>

                        </div>

                      </div>


                      {/* STRENGTHS */}

                      {normalized.strengths.length >
                        0 && (

                        <div className="feedback-box">

                          <h4>
                            Strengths
                          </h4>

                          <ul>

                            {normalized.strengths.map(
                              (
                                strength,
                                i
                              ) => (

                                <li key={i}>
                                  {strength}
                                </li>

                              )
                            )}

                          </ul>

                        </div>
                      )}


                      {/* WEAKNESSES */}

                      {normalized.weaknesses.length >
                        0 && (

                        <div className="feedback-box">

                          <h4>
                            Areas to Improve
                          </h4>

                          <ul>

                            {normalized.weaknesses.map(
                              (
                                weakness,
                                i
                              ) => (

                                <li key={i}>
                                  {weakness}
                                </li>

                              )
                            )}

                          </ul>

                        </div>
                      )}


                      {/* FEEDBACK */}

                      {normalized.feedback && (

                        <div className="feedback-box">

                          <h4>
                            AI Feedback
                          </h4>

                          <p>
                            {
                              normalized.feedback
                            }
                          </p>

                        </div>
                      )}


                      {/* IDEAL ANSWER */}

                      {normalized.ideal_answer && (

                        <div className="feedback-box">

                          <h4>
                            Ideal Answer
                          </h4>

                          <p className="ideal-answer-text">

                            {
                              normalized.ideal_answer
                            }

                          </p>

                        </div>
                      )}

                    </div>
                  );
                }
              )}

            </div>

          </section>


          <button
            className="restart-button"
            onClick={
              restartInterview
            }
          >
            Start New Interview
          </button>

        </main>

      </div>
    );
  }


  /* =====================================================
     MAIN PAGE
  ===================================================== */

  return (

    <div className="app">

      <main className="container">

        <header className="app-header">

          <h1>
            AI Interview Assistant
          </h1>

          <p>
            AI-powered resume based interview
            preparation and evaluation
          </p>

        </header>


        {/* ERROR */}

        {error && (

          <div className="alert error-alert">
            {error}
          </div>

        )}


        {/* SUCCESS */}

        {success && (

          <div className="alert success-alert">
            {success}
          </div>

        )}


        {/* =================================================
            RESUME UPLOAD
        ================================================= */}

        {!interviewStarted &&
          !interviewCompleted && (

            <section className="resume-card">

              <div className="card-icon">
                📄
              </div>

              <h2>
                Upload Your Resume
              </h2>

              <p>
                Upload your PDF resume to
                generate personalized AI/ML
                interview questions.
              </p>


              <label
                htmlFor="resume-upload"
                className="file-upload-area"
              >

                <div className="upload-icon">
                  ↑
                </div>

                <strong>

                  {resumeFile
                    ? resumeFile.name
                    : "Choose your PDF resume"}

                </strong>

                <span>

                  {resumeFile
                    ? "Selected successfully"
                    : "PDF files only"}

                </span>


                <input
                  id="resume-upload"
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={
                    handleFileChange
                  }
                />

              </label>


              {resumeFile && (

                <div className="selected-file">

                  <span>
                    ✓
                  </span>

                  {resumeFile.name}

                </div>

              )}


              <button
                className="primary-button"
                onClick={
                  uploadResume
                }
                disabled={
                  !resumeFile ||
                  uploading
                }
              >

                {uploading
                  ? "Analyzing Resume..."
                  : "Upload Resume"}

              </button>


              {resumeUploaded && (

                <button
                  className="start-button"
                  onClick={
                    startInterview
                  }
                  disabled={
                    starting
                  }
                >

                  {starting
                    ? "Preparing Interview..."
                    : "Start AI Interview →"}

                </button>

              )}

            </section>

          )}


        {/* =================================================
            INTERVIEW
        ================================================= */}

        {interviewStarted && (

          <div className="interview-container">

            <div className="interview-progress">

              <div>

                Question{" "}

                <strong>
                  {currentQuestion}
                </strong>

                {" "}of{" "}

                {totalQuestions}

              </div>


              <div className="progress-track">

                <div
                  className="progress-fill"
                  style={{
                    width:
                      `${
                        (
                          currentQuestion /
                          totalQuestions
                        ) * 100
                      }%`,
                  }}
                />

              </div>

            </div>


            {/* QUESTION */}

            <section className="question-card">

              <div className="question-label">
                Interview Question
              </div>

              <h2>
                {question}
              </h2>

            </section>


            {/* ANSWER */}

            <section className="answer-card">

              <div className="answer-header">

                <div>

                  <h3>
                    Your Answer
                  </h3>

                  <p>
                    Explain your approach
                    clearly. Include examples
                    and technical reasoning
                    wherever relevant.
                  </p>

                </div>


                <span className="answer-count">

                  {answer.length}
                  {" "}characters

                </span>

              </div>


              <textarea
                className="answer-textarea"
                value={answer}
                onChange={(e) =>
                  setAnswer(
                    e.target.value
                  )
                }
                placeholder={
                  "Type your answer here...\n\n" +
                  "Try to explain:\n" +
                  "• Your understanding\n" +
                  "• Your approach\n" +
                  "• Technical details\n" +
                  "• Examples\n" +
                  "• Challenges and solutions"
                }
                disabled={
                  submitting
                }
              />


              <button
                className="submit-button"
                onClick={
                  submitAnswer
                }
                disabled={
                  !answer.trim() ||
                  submitting
                }
              >

                {submitting
                  ? "AI is evaluating your answer..."
                  : currentQuestion ===
                    totalQuestions
                  ? "Submit & Finish Interview"
                  : "Submit Answer →"}

              </button>

            </section>


            {/* =================================================
                CURRENT EVALUATION
            ================================================= */}

            {evaluation && (

              <section className="evaluation-card">

                <div className="evaluation-title">

                  <div>

                    <span>
                      AI EVALUATION
                    </span>

                    <h2>
                      Current Question
                      Performance
                    </h2>

                  </div>


                  <div className="score-badge">

                    {evaluation.score}
                    /10

                  </div>

                </div>


                <div className="evaluation-grid">

                  <div className="evaluation-item">

                    <span>
                      Technical Accuracy
                    </span>

                    <strong>

                      {
                        evaluation
                          .technical_accuracy
                      }
                      /10

                    </strong>

                  </div>


                  <div className="evaluation-item">

                    <span>
                      Clarity
                    </span>

                    <strong>

                      {
                        evaluation.clarity
                      }
                      /10

                    </strong>

                  </div>


                  <div className="evaluation-item">

                    <span>
                      Depth
                    </span>

                    <strong>

                      {
                        evaluation.depth
                      }
                      /10

                    </strong>

                  </div>


                  <div className="evaluation-item">

                    <span>
                      Relevance
                    </span>

                    <strong>

                      {
                        evaluation.relevance
                      }
                      /10

                    </strong>

                  </div>

                </div>


                {/* STRENGTHS */}

                {evaluation.strengths?.length >
                  0 && (

                  <div className="current-feedback">

                    <h3>
                      Strengths
                    </h3>

                    <ul>

                      {evaluation.strengths.map(
                        (
                          strength,
                          index
                        ) => (

                          <li key={index}>
                            {strength}
                          </li>

                        )
                      )}

                    </ul>

                  </div>
                )}


                {/* WEAKNESSES */}

                {evaluation.weaknesses?.length >
                  0 && (

                  <div className="current-feedback">

                    <h3>
                      Areas to Improve
                    </h3>

                    <ul>

                      {evaluation.weaknesses.map(
                        (
                          weakness,
                          index
                        ) => (

                          <li key={index}>
                            {weakness}
                          </li>

                        )
                      )}

                    </ul>

                  </div>
                )}


                {/* FEEDBACK */}

                {evaluation.feedback && (

                  <div className="current-feedback">

                    <h3>
                      AI Feedback
                    </h3>

                    <p>
                      {
                        evaluation.feedback
                      }
                    </p>

                  </div>
                )}


                {/* IDEAL ANSWER */}

                {evaluation.ideal_answer && (

                  <div className="current-feedback">

                    <h3>
                      Ideal Answer
                    </h3>

                    <p className="ideal-answer-text">

                      {
                        evaluation.ideal_answer
                      }

                    </p>

                  </div>
                )}

              </section>

            )}

          </div>

        )}

      </main>

    </div>
  );
}

export default App;
