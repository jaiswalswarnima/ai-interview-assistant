import re

def extract_email(text):
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    match = re.search(pattern, text)
    if match:
        return match.group()
    return None

def extract_phone(text):
    pattern = r"(?:\+91[-\s]?)?[6-9]\d{9}"
    match = re.search(pattern, text)
    if match:
        return match.group()
    return None

def extract_skills(text):
    skills_list = [
        "Python",
        "Java",
        "C++",
        "SQL",
        "Machine Learning",
        "Deep Learning",
        "Artificial Intelligence",
        "NLP",
        "Natural Language Processing",
        "RAG",
        "LLM",
        "LangChain",
        "TensorFlow",
        "PyTorch",
        "FastAPI",
        "React",
        "JavaScript",
        "HTML",
        "CSS",
        "Git",
        "GitHub"
    ]
    found_skills = []
    text_lower = text.lower()
    for skill in skills_list:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    if "NLP" in found_skills and "Natural Language Processing" in found_skills:
        found_skills.remove("Natural Language Processing")        
    return found_skills

def extract_section(text, section_names):
    """
    Extracts text belonging to a resume section.
    """
    lines = text.splitlines()
    start_index = None
    for i, line in enumerate(lines):
        clean_line = line.strip().lower()
        for section_name in section_names:
            if clean_line == section_name.lower():
                start_index = i + 1
                break
        if start_index is not None:
            break
    if start_index is None:
        return []
    section_lines = []
    known_sections = [
        "education",
        "experience",
        "work experience",
        "internship experience",
        "projects",
        "project",
        "skills",
        "technical skills",
        "certifications",
        "achievements",
        "summary",
        "objective",
        "contact"
   ]
    for line in lines[start_index:]:
        clean_line = line.strip().lower()
        if clean_line in known_sections:
            break
        if line.strip():
            section_lines.append(line.strip())
    return section_lines

def extract_education(text):
    return extract_section(
        text,
        ["Education", "Academic Background"]
    )

def extract_experience(text):
    return extract_section(
        text,
        ["Experience", "Work Experience", "Internship Experience"]
    )

def extract_projects(text):
    return extract_section(
        text,
        ["Projects", "Project"]
    )

def parse_resume(text):
    resume_data = {
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "education": extract_education(text),
        "experience": extract_experience(text),
        "projects": extract_projects(text)
    }
    return resume_data