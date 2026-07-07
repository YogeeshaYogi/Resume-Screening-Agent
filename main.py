import os
import pandas as pd
import json
from utils.logger import logger
from utils.parser import parse_file
from utils.extractor import extract_resume_info
from utils.scorer import ResumeScorer

def main():
    print("====================================================")
    print(" AI RESUME SCREENING AGENT - COMMAND LINE INTERFACE")
    print("====================================================")
    
    # 1. Ask for Job Description path
    while True:
        jd_path = input("\nEnter the path to the Job Description text file: ").strip().strip('"').strip("'")
        if not jd_path:
            print("[ERROR] Path cannot be empty. Please enter a valid path.")
            continue
        if not os.path.exists(jd_path):
            print(f"[ERROR] Job Description file not found at '{jd_path}'. Please check the path and try again.")
            continue
        break
        
    # 2. Ask for Resumes directory path
    while True:
        resumes_dir = input("Enter the path to the folder containing resumes: ").strip().strip('"').strip("'")
        if not resumes_dir:
            print("[ERROR] Path cannot be empty. Please enter a valid folder path.")
            continue
        if not os.path.exists(resumes_dir) or not os.path.isdir(resumes_dir):
            print(f"[ERROR] Resumes folder not found or is not a directory at '{resumes_dir}'. Please try again.")
            continue
        break
        
    # 3. Read Job Description
    print(f"\n[READ] Reading Job Description from '{jd_path}'...")
    try:
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_text = f.read().strip()
        if not jd_text:
            print("[ERROR] The Job Description file is empty.")
            return
    except Exception as e:
        print(f"[ERROR] Error reading Job Description file: {e}")
        return

    # 4. Scan folder for resumes
    print(f"[DIR] Scanning '{resumes_dir}' for resumes (.pdf, .docx, .txt)...")
    valid_extensions = ('.pdf', '.docx', '.txt')
    resume_files = [
        os.path.join(resumes_dir, f) 
        for f in os.listdir(resumes_dir) 
        if f.lower().endswith(valid_extensions)
    ]
    
    if not resume_files:
        print(f"[ERROR] No valid resumes found in folder '{resumes_dir}'. Supported formats: .pdf, .docx, .txt")
        return
        
    print(f"Found {len(resume_files)} resumes to process.")
    
    # 5. Initialize NLP Scorer
    print("\n[MODEL] Initializing Sentence Transformer Model (all-MiniLM-L6-v2)...")
    try:
        scorer = ResumeScorer()
    except Exception as e:
        print(f"[ERROR] Error loading Sentence Transformers: {e}")
        return
        
    # 6. Screen Resumes
    print("\n[PROCESS] Processing and scoring candidates...")
    flat_results = []
    parsed_count = 0
    failed_count = 0
    
    for i, file_path in enumerate(resume_files, 1):
        file_name = os.path.basename(file_path)
        print(f" [{i}/{len(resume_files)}] Processing: {file_name}...")
        try:
            raw_text = parse_file(file_path)
            info = extract_resume_info(file_path, raw_text)
            score_info = scorer.score_candidate(jd_text, info)
            
            flat_results.append({
                "Rank": 0,  # Will assign after sorting
                "Candidate Name": info["candidate_name"],
                "Score": score_info["overall_score"],
                "Skills": ", ".join(info["skills_list"]) if info["skills_list"] else "Not Specified",
                "Experience": info["experience_text"][:150] + ("..." if len(info["experience_text"]) > 150 else ""),
                "Education": info["education_text"][:150] + ("..." if len(info["education_text"]) > 150 else ""),
                "Reason for ranking": score_info["reasoning"]
            })
            parsed_count += 1
        except Exception as e:
            logger.error(f"Failed to process file {file_name}: {e}")
            failed_count += 1
            flat_results.append({
                "Rank": 999,
                "Candidate Name": f"Corrupted Candidate ({file_name})",
                "Score": 0.0,
                "Skills": "N/A",
                "Experience": "N/A",
                "Education": "N/A",
                "Reason for ranking": f"PARSE/SCORE ERROR: {str(e)}"
            })
            
    # 7. Rank and Sort Results
    df = pd.DataFrame(flat_results)
    # Separate successful ones and failed ones for sorting
    success_df = df[df["Score"] > 0].sort_values(by="Score", ascending=False).reset_index(drop=True)
    failed_df = df[df["Score"] == 0].reset_index(drop=True)
    
    # Assign ranks
    success_df["Rank"] = success_df.index + 1
    if not failed_df.empty:
        failed_df["Rank"] = len(success_df) + failed_df.index + 1
        
    final_df = pd.concat([success_df, failed_df], ignore_index=True)
    
    # 8. Display Results Table
    print("\n" + "="*80)
    print(" CANDIDATE RANKINGS")
    print("="*80)
    # Set display options for cleaner printing
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(final_df[["Rank", "Candidate Name", "Score", "Reason for ranking"]].to_string(index=False))
    print("="*80)
    print(f"Summary: Screened {len(resume_files)} candidate(s). Successful: {parsed_count}. Failed: {failed_count}.")
    
    # 9. Export Reports
    os.makedirs("output", exist_ok=True)
    csv_path = "output/results.csv"
    json_path = "output/results.json"
    
    try:
        final_df.to_csv(csv_path, index=False)
        
        json_data = {
            "summary": {
                "total_candidates": len(resume_files),
                "parsed_successfully": parsed_count,
                "failed_count": failed_count,
                "average_score": round(success_df["Score"].mean(), 2) if not success_df.empty else 0.0
            },
            "candidates": final_df.to_dict(orient="records")
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, default=str)
            
        print(f"\n[EXPORT] Reports successfully exported to:")
        print(f" - CSV Report:  {csv_path}")
        print(f" - JSON Report: {json_path}")
        print("\nScreening Agent run complete!\n")
    except Exception as e:
        print(f"[ERROR] Error saving report files: {e}")

if __name__ == "__main__":
    main()
