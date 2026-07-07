# AI Resume Screening Agent

A production-ready **AI Resume Screening Agent** designed to rank multiple candidate resumes against a given Job Description (JD) using semantic NLP similarity. Developed as part of the **Junior AI Research Associate – 24-Hour AI Agent Challenge**.

This application parses resumes of multiple formats (PDF, DOCX, TXT), segments their contents into structured categories (Skills, Experience, Education), computes aspect-based semantic scores using Sentence Transformers, ranks the candidates, and outputs detailed summaries. It supports both a command-line interface (CLI) and an interactive web dashboard (Streamlit).

---

## 🚀 Features

- **Double Interface**: 
  - **CLI (Command Line)**: Runs entirely in your terminal and asks for user inputs dynamically.
  - **Streamlit Web UI**: Polished, dashboard-style interface with interactive analytics and a candidate explorer.
- **Multi-Format Parser**: Supports `.pdf`, `.docx`, and `.txt` resumes. Handles empty, corrupted, and invalid files gracefully without interrupting execution.
- **Aspect-Based NLP Scoring**: Utilizes the `all-MiniLM-L6-v2` Sentence Transformers model to calculate cosine similarity across multiple dimensions (Overall, Skills, and Experience) rather than relying on simple keyword matching.
- **Explainable AI Reasoning**: Generates automated, deterministic matching explanations by mapping the best-aligned candidate sentences to key job description requirements.
- **Interactive Streamlit Dashboard**:
  - Upload custom Job Descriptions & resumes or test with a pre-generated sample dataset.
  - Interactive ranking tables, visualizations, and metrics.
  - **Candidate Explorer**: Perform deep dives on individual candidates to inspect their parsed skills, experience, and similarity breakdowns.
- **Export Formats**: Exports screening results automatically to both CSV and JSON formats in the `output/` directory.

---

## 📂 Folder Structure

```
ai-resume-screening-agent/
│
├── app.py                     # Streamlit web application & UI dashboard
├── main.py                    # Interactive Command Line Interface (CLI)
├── generate_sample_data.py    # Sample data generator (creates JD and 10 resumes)
├── requirements.txt           # Project dependencies
├── README.md                  # Detailed project documentation
├── .gitignore                 # Files and folders ignored by git
│
├── jd/                        # Job description storage
│   └── job_description.txt    # Generated sample Job Description
│
├── resumes/                   # Candidate resumes storage (created dynamically)
│   ├── resume_01_alice_smith.pdf
│   ├── ...
│   └── resume_10_julia_roberts.pdf
│
├── output/                    # Folder for exported ranking outputs
│   ├── results.csv
│   └── results.json
│
└── utils/                     # Modular service layer
    ├── __init__.py
    ├── logger.py              # Application logger setup
    ├── parser.py              # File reader for PDF, DOCX, and TXT
    ├── extractor.py           # Candidate profile regex & keyword extractor
    └── scorer.py              # Sentence Transformers semantic similarity scorer
```

---

## 🛠️ Installation

Ensure you have Python 3.10+ installed. Follow the commands below to set up your environment:

1. Clone or download this repository to your local workspace.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 How to Run

### 1. Generate Sample Data
To test the application immediately with 10 pre-constructed realistic candidates (representing various qualification match levels: Strong, Moderate, and Weak):
```bash
python generate_sample_data.py
```
This command generates:
- A detailed job description for a **Junior AI Research Associate**.
- **10 resumes** in the `resumes/` folder (comprising 4 PDF, 3 DOCX, and 3 TXT documents).

### 2. Run the CLI Application (User Input Prompts)
Run the command-line application. It will prompt you to input the Job Description path and the Resumes folder path:
```bash
python main.py
```
*Example Console Interaction:*
```
Enter the path to the Job Description text file (default: jd/job_description.txt): jd/job_description.txt
Enter the path to the folder containing resumes (default: resumes/): resumes
```
The terminal will display the live parsing logs and output a formatted ASCII table ranking all candidates. Results will be saved to `output/results.csv` and `output/results.json`.

### 3. Launch the Streamlit Web UI
To run the Streamlit dashboard:
```bash
streamlit run app.py
```
This opens the dashboard in your default browser (usually at `http://localhost:8501`).

---

## 📊 Scoring Method

Rather than performing simple global text-to-text cosine similarity, which is highly prone to noise (e.g., contact details or irrelevant headers inflating scores), the screening agent implements a **Multi-Aspect Semantic Matching Strategy**:

1. **Overall Match (Weight: 50%)**: Cosine similarity between the entire Job Description text and the full Resume text.
2. **Skills Match (Weight: 30%)**: Cosine similarity between the Job Description and the extracted/scanned **Skills** section.
3. **Experience Match (Weight: 20%)**: Cosine similarity between the Job Description and the extracted **Work Experience** section.

$$\text{Final Score} = (0.50 \times S_{\text{overall}}) + (0.30 \times S_{\text{skills}}) + (0.20 \times S_{\text{experience}})$$

The scores are output as percentages (0–100%). Candidates are classified into:
- **Strong Match** (Score $\ge 75\%$)
- **Moderate Match** ($55\% \le$ Score $< 75\%$)
- **Weak Match** (Score $< 55\%$)

### Explainable Reasoning Engine
To provide a clear audit trail for the score, the agent:
- Identifies the key requirements in the Job Description.
- Computes sentence-level similarities against the resume text.
- Extracts the candidate's exact sentences showing the highest similarity as "strengths".
- Lists matching tech-stack keywords identified in a structured summary.

---

## ⚖️ Trade-offs & Limitations

### Trade-offs
1. **Local Embeddings vs. LLM API**: Using `all-MiniLM-L6-v2` locally is 100% free, runs completely offline, guarantees private data handling, and does not require managing API keys. However, it lack generative capabilities, which is why we built a sentence-matching heuristics engine to produce explainable reasoning.
2. **Rule-Based Parsing vs. Visual Parsing**: We segment documents using regular expressions and text structure. While this executes instantly and works for 95% of standard resume designs, it can lose spatial context on multi-column or highly graphical designs.

### Limitations
- **Scanned Resumes**: Resumes that are saved as flat images inside a PDF (scanned) cannot be parsed. They will be identified as empty/scanned and scored as 0.0 with an explanation in the dashboard.
- **Context Length**: The embedding model `all-MiniLM-L6-v2` has a context window of 256 tokens. While our scorer splits sentences to evaluate key requirements, extremely long resumes are truncated at the chunk boundary during global embedding generation.
