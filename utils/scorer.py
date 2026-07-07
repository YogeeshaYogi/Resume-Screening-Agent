import re
from typing import Dict, List, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer, util
from utils.logger import logger

class ResumeScorer:
    """
    Core NLP Scoring and Reasoning Engine using Sentence Transformers.
    Computes semantic similarity and extracts match explanations.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        
    @property
    def model(self) -> SentenceTransformer:
        """Lazy loader for SentenceTransformer model to optimize memory usage."""
        if self._model is None:
            logger.info(f"Loading SentenceTransformer model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def compute_cosine_similarity(self, text1: str, text2: str) -> float:
        """Computes raw cosine similarity between two texts."""
        if not text1.strip() or not text2.strip():
            return 0.0
            
        emb1 = self.model.encode(text1, convert_to_tensor=True)
        emb2 = self.model.encode(text2, convert_to_tensor=True)
        
        similarity = util.cos_sim(emb1, emb2).item()
        return max(0.0, min(1.0, similarity))

    def score_candidate(self, jd_text: str, candidate_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scores a candidate using a Multi-Aspect Semantic Matching Strategy.
        Combines overall similarity, skills matching, and experience matching.
        """
        logger.info(f"Scoring candidate: {candidate_info['candidate_name']}")
        
        # 1. Compute aspect-level cosine similarities
        overall_sim = self.compute_cosine_similarity(jd_text, candidate_info["full_text"])
        
        # Skills aspect (compare full JD to extracted skills section)
        skills_sim = self.compute_cosine_similarity(jd_text, candidate_info["skills_text"])
        
        # Experience aspect (compare full JD to extracted experience section)
        experience_sim = self.compute_cosine_similarity(jd_text, candidate_info["experience_text"])
        
        # 2. Calculate weighted final score
        # Weights: 50% Overall, 30% Skills, 20% Experience
        final_similarity = (0.50 * overall_sim) + (0.30 * skills_sim) + (0.20 * experience_sim)
        
        # Convert to percentage (0 - 100)
        score_percentage = round(final_similarity * 100, 2)
        
        # 3. Generate explainable reasoning
        reasoning = self._generate_reasoning(jd_text, candidate_info, score_percentage, overall_sim, skills_sim, experience_sim)
        
        return {
            "candidate_name": candidate_info["candidate_name"],
            "file_name": candidate_info["file_name"],
            "overall_score": score_percentage,
            "overall_similarity": round(overall_sim, 4),
            "skills_similarity": round(skills_sim, 4),
            "experience_similarity": round(experience_sim, 4),
            "reasoning": reasoning
        }

    def _split_into_sentences(self, text: str) -> List[str]:
        """Splits text into meaningful sentences/bullet points."""
        # Split by periods, newlines, semicolons, and list markers
        raw_sentences = re.split(r'\. |\n|; ', text)
        sentences = []
        for s in raw_sentences:
            s_clean = re.sub(r'^[\s\-\*•\d\.\)]+', '', s).strip()  # Clean list bullet markers
            if len(s_clean) > 15:  # Keep only informative sentences
                sentences.append(s_clean)
        return sentences

    def _generate_reasoning(
        self, 
        jd_text: str, 
        candidate_info: Dict[str, Any], 
        score: float,
        overall_sim: float, 
        skills_sim: float, 
        experience_sim: float
    ) -> str:
        """
        Generates deterministic, explainable reasoning based on semantic similarity of sentences.
        Matches key JD sentences with the resume's sentences to find the best-supporting evidence.
        """
        jd_sentences = self._split_into_sentences(jd_text)
        resume_sentences = self._split_into_sentences(candidate_info["full_text"])
        
        if not jd_sentences or not resume_sentences:
            return f"Candidate ranks with a score of {score}%. Detailed semantic matching was limited due to short text length."
            
        # Select key requirements from the Job Description
        # e.g., sentences containing 'must', 'experience', 'required', 'skills', 'develop', 'design', or long sentences
        requirement_keywords = ["must", "experience", "required", "skills", "ability", "proficient", "knowledge", "develop", "build", "lead"]
        key_jd_sentences = [
            s for s in jd_sentences 
            if any(kw in s.lower() for kw in requirement_keywords) or len(s) > 80
        ]
        
        # Fallback to top 5 longest sentences if none matched keywords
        if not key_jd_sentences:
            key_jd_sentences = sorted(jd_sentences, key=len, reverse=True)[:5]
        else:
            key_jd_sentences = key_jd_sentences[:8]  # Limit to top 8 key sentences
            
        # Find best matches in resume for each key JD requirement
        matches: List[Tuple[str, str, float]] = []
        
        # Batch encode to speed up
        jd_embs = self.model.encode(key_jd_sentences, convert_to_tensor=True)
        res_embs = self.model.encode(resume_sentences, convert_to_tensor=True)
        
        # Calculate similarity matrix
        sim_matrix = util.cos_sim(jd_embs, res_embs)
        
        for jd_idx, jd_sent in enumerate(key_jd_sentences):
            best_res_idx = sim_matrix[jd_idx].argmax().item()
            best_score = sim_matrix[jd_idx][best_res_idx].item()
            best_res_sent = resume_sentences[best_res_idx]
            matches.append((jd_sent, best_res_sent, best_score))
            
        # Sort matches by how strongly they align
        matches = sorted(matches, key=lambda x: x[2], reverse=True)
        
        # Extract top matching points for the summary
        strengths = []
        for _, res_sent, match_score in matches[:2]:
            if match_score > 0.45:
                # Truncate very long sentences
                truncated = res_sent if len(res_sent) < 90 else res_sent[:87] + "..."
                strengths.append(truncated)
                
        # Determine qualification category
        if score >= 75:
            fit_category = "Strong Match"
            fit_desc = "excellent alignment across technical requirements, experience, and domain skills"
        elif score >= 55:
            fit_category = "Moderate Match"
            fit_desc = "solid foundation in core areas, though some supplementary skills or experiences may be missing"
        else:
            fit_category = "Weak Match"
            fit_desc = "significant gaps between the candidate's profile and the critical requirements of the role"
            
        # Build explanation
        scanned_skills = candidate_info["skills_list"]
        skills_summary = ", ".join(scanned_skills[:5]) if scanned_skills else "None explicitly detected"
        
        explanation = f"**{fit_category}** ({score}%): Demonstrates {fit_desc}. "
        
        if strengths:
            explanation += f"Key strength includes direct experience matching the JD: *\"{strengths[0]}\"*."
            if len(strengths) > 1:
                explanation += f" Also aligns well on: *\"{strengths[1]}\"*."
        else:
            explanation += "The overall experience profile aligns moderately with the core duties."
            
        if scanned_skills:
            explanation += f" Notable keywords matched: {skills_summary}."
            
        return explanation
