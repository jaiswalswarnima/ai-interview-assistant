# 🤖 AI Interview Assistant

An AI-powered technical interview platform that analyzes a candidate's resume, generates personalized interview questions, evaluates answers, and provides detailed performance analytics.

## 🚀 Live Demo

- **Frontend:** https://ai-interview-assistant-swart-eta.vercel.app/
- **Backend API:** https://ai-interview-assistant-api.onrender.com

---

## 📌 Overview

AI Interview Assistant is an AI-powered interview preparation platform designed to simulate a real technical interview experience.

The application allows candidates to upload their resume, receive personalized interview questions based on their skills and projects, answer questions, and receive AI-generated evaluation and performance feedback.

The system is primarily focused on **AI/ML and technical placement preparation**.

---

## ✨ Features

### 📄 Resume Upload & Analysis

- Upload resume in PDF format
- Extract resume text automatically
- Analyze candidate profile using AI
- Identify technical skills
- Extract projects
- Extract work experience
- Extract education
- Identify strengths
- Identify areas for improvement

### 🧠 Personalized Interview Questions

Interview questions are generated according to the candidate's resume.

Questions can cover:

- Artificial Intelligence
- Machine Learning
- Deep Learning
- NLP
- Generative AI
- RAG
- LLMs
- Python
- Programming
- DSA
- OOP
- DBMS
- Technical Projects
- Core CS concepts

### 🎯 Adaptive Interview

The interview dynamically generates the next question based on:

- Candidate's previous answer
- Previous question
- AI evaluation
- Candidate's resume
- Interview type
- Previously asked questions

This helps create a personalized and realistic interview experience.

### 📊 AI Answer Evaluation

Each answer is evaluated on four parameters:

| Parameter | Score |
|-----------|-------|
| Technical Accuracy | /10 |
| Clarity | /10 |
| Depth | /10 |
| Relevance | /10 |

### 💡 Detailed Feedback

For every answer, the system provides:

- Overall score
- Strengths
- Areas to improve
- Overall feedback
- Question-wise evaluation

### 📈 Final Performance Report

After completing the interview, candidates can view:

- Total questions
- Total answered questions
- Total score
- Average score
- Average technical accuracy
- Average clarity
- Average depth
- Average relevance
- Question-wise results

---

# 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │      Candidate      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   React Frontend    │
                    │       + Vite        │
                    └──────────┬──────────┘
                               │
                               │ REST API
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Backend   │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌─────────────┐ ┌────────────┐ ┌─────────────┐
        │   PyMuPDF   │ │  Session   │ │ LLM Service │
        │ Resume PDF  │ │  Storage   │ │    Groq     │
        └─────────────┘ └────────────┘ └──────┬──────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │ GPT-OSS-20B     │
                                      └─────────────────┘
