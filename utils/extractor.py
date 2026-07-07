import re
import os
from typing import Dict, List, Any
from utils.logger import logger

# A list of common skills for keyword scanning (as a fallback and structured output)
COMMON_SKILLS = [
    # Programming Languages
    "Python", "SQL", "Java", "C\\+\\+", "C#", "R", "Go", "Rust", "JavaScript", "TypeScript", "HTML", "CSS", "Bash", "Scala",
    # AI/ML/Data Science
    "Machine Learning", "Deep Learning", "Artificial Intelligence", "AI", "NLP", "Natural Language Processing", 
    "Computer Vision", "Reinforcement Learning", "Neural Networks", "Data Science", "Data Analysis", "Predictive Modeling",
    # Frameworks & Libraries
    "PyTorch", "TensorFlow", "Keras", "Scikit-Learn", "NLTK", "Spacy", "Hugging Face", "Transformers", 
    "Pandas", "NumPy", "SciPy", "Matplotlib", "Seaborn", "Opencv", "LangChain", "LlamaIndex",
    # Streamlit/Web Development
    "Streamlit", "Flask", "FastAPI", "Django", "Node.js", "React", "Angular",
    # Cloud & DevOps
    "AWS", "GCP", "Google Cloud", "Azure", "Docker", "Kubernetes", "Git", "GitHub", "CI/CD", "MLOps", "Airflow", "Terraform",
    # Database
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLAlchemy", "Neo4j", "Pinecone",
    # Soft Skills & Domains
    "Agile", "Scrum", "Project Management", "Technical Writing", "Research", "Teamwork", "Communication"
]

def clean_text(text: str) -> str:
    """Removes double spaces and weird line endings."""
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_name(text: str) -> str:
    """
    Attempts to extract the candidate's name from the top section of the resume.
    Uses regex, line parsing, and exclusion rules for emails, links, etc.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return "Unknown Candidate"

    # Candidates names are usually at the top of the page.
    # We inspect the first 5 lines to find a valid name.
    email_regex = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    phone_regex = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
    url_regex = re.compile(r'https?://[^\s]+|www\.[^\s]+')
    
    for line in lines[:5]:
        # Skip if line contains typical contact info
        if email_regex.search(line) or phone_regex.search(line) or url_regex.search(line):
            continue
            
        # Skip if the line contains common labels
        line_lower = line.lower()
        exclude_keywords = [
            "phone", "email", "address", "linkedin", "github", "resume", "cv", 
            "curriculum", "vitae", "summary", "profile", "portfolio", "page"
        ]
        if any(keyword in line_lower for keyword in exclude_keywords):
            continue
            
        # Check if the line has 1 to 4 words and starts with capital letters
        words = line.split()
        if 1 <= len(words) <= 4:
            # Check if words look like proper nouns
            is_valid_name = True
            for w in words:
                # Allow abbreviations like 'J.' or names with hyphens
                cleaned_word = re.sub(r'[^a-zA-Z]', '', w)
                if cleaned_word and not cleaned_word[0].isupper():
                    is_valid_name = False
                    break
            
            if is_valid_name:
                cleaned_name = re.sub(r'[^a-zA-Z\s\.-]', '', line).strip()
                if cleaned_name and len(cleaned_name) > 2:
                    return cleaned_name
                    
    # Fallback to the first line if nothing matches, cleaned up
    first_line = lines[0]
    fallback_name = re.sub(r'[^a-zA-Z\s\.-]', '', first_line).strip()
    if fallback_name and len(fallback_name) > 2 and len(fallback_name.split()) <= 4:
        return fallback_name
        
    return "Unknown Candidate"

def extract_sections(text: str) -> Dict[str, str]:
    """
    Splits the resume text into standard sections: Skills, Experience, and Education.
    """
    sections = {
        "skills": "",
        "experience": "",
        "education": "",
        "other": ""
    }
    
    # Split text into lines
    lines = text.split('\n')
    
    # Define regexes for headers (checking clean, lower-case, punctuation-free string)
    skills_header_re = re.compile(
        r'^(technical\s+)?skills?(\s+&\s+technologies)?$|^expertise$|^core\s+competencies$|^technologies$|^technical\s+expertise$', 
        re.IGNORECASE
    )
    experience_header_re = re.compile(
        r'^(work\s+|professional\s+|employment\s+)?experience[s]?$|^(employment|work|career)\s+history$|^professional\s+background$', 
        re.IGNORECASE
    )
    education_header_re = re.compile(
        r'^education$|^academic\s+background$|^academic\s+qualifications?$', 
        re.IGNORECASE
    )
    
    current_section = "other"
    section_lines = {
        "skills": [],
        "experience": [],
        "education": [],
        "other": []
    }
    
    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
            
        # Detect if it's a section header.
        # Section headers are usually short: <= 35 chars and <= 5 words.
        is_header = False
        if len(cleaned_line) <= 35 and len(cleaned_line.split()) <= 5:
            # Strip punctuation and numbers for header check
            header_candidate = re.sub(r'[^\w\s]', '', cleaned_line).strip()
            
            if skills_header_re.match(header_candidate):
                current_section = "skills"
                is_header = True
            elif experience_header_re.match(header_candidate):
                current_section = "experience"
                is_header = True
            elif education_header_re.match(header_candidate):
                current_section = "education"
                is_header = True
                
        # If it is a header, we do not append the header word to the section content
        if not is_header:
            section_lines[current_section].append(line)
            
    for key in sections:
        sections[key] = "\n".join(section_lines[key]).strip()
        
    return sections

def scan_skills(text: str) -> List[str]:
    """
    Scans the text for a predefined list of skills (COMMON_SKILLS).
    Uses regex word boundaries for precise matching.
    """
    found_skills = []
    # Make text case-insensitive but preserve capital forms for exact match checks where needed
    for skill in COMMON_SKILLS:
        # Match word boundary
        # If skill contains special chars like C++ or .NET, escape them
        pattern = r'\b' + skill + r'\b'
        # Adjust pattern for C++ or C#
        if "++" in skill:
            pattern = r'\bC\+\+'
        elif "#" in skill:
            pattern = r'\bC#'
            
        if re.search(pattern, text, re.IGNORECASE):
            # Clean up the skill name for presentation
            clean_skill = skill.replace("\\", "")
            found_skills.append(clean_skill)
            
    return sorted(list(set(found_skills)))

def extract_resume_info(file_path: str, raw_text: str) -> Dict[str, Any]:
    """
    Wrapper function to extract all structured information from a resume.
    """
    logger.info(f"Extracting structured information from resume text: {file_path}")
    name = extract_name(raw_text)
    sections = extract_sections(raw_text)
    skills_list = scan_skills(raw_text)
    
    # Format Skills representation
    # If the skills section is non-empty, clean it up. If empty, use scanned skills.
    skills_text = sections["skills"]
    if not skills_text:
        skills_text = ", ".join(skills_list) if skills_list else "Not explicitly specified."
        
    experience_text = sections["experience"]
    if not experience_text:
        # If experience section is empty, look at the first 300 words of the text
        experience_text = "Experience section not explicitly identified. Refer to full text."
        
    education_text = sections["education"]
    if not education_text:
        education_text = "Education section not explicitly identified. Refer to full text."
        
    return {
        "file_name": os.path.basename(file_path),
        "file_path": file_path,
        "candidate_name": name,
        "skills_text": skills_text,
        "skills_list": skills_list,
        "experience_text": experience_text,
        "education_text": education_text,
        "full_text": raw_text
    }
