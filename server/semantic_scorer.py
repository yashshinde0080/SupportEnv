"""
Semantic scoring functionality using sentence transformers.
Evaluates agent responses for empathy, solution-orientation, and resolution alignment.
"""

from typing import List, Dict, Any, Optional
import os
import sys

# Add parent directory to path for interface import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SemanticScorer:
    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Using a small, fast model suitable for CPU inference in HF Spaces
                from interface import Config
                hf_token = Config.get_hf_token()

                if hf_token:
                    self._model = SentenceTransformer(
                        'sentence-transformers/all-MiniLM-L6-v2',
                        token=hf_token
                    )
                else:
                    self._model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            except Exception:
                return None
        return self._model

    def evaluate_responses(self, responses: List[str], expected_resolution: str) -> Dict[str, float]:
        """
        Evaluate the overall semantic quality of a list of responses.
        Returns a dict with empathy, solution, and resolution alignment scores.
        """
        if not responses or not expected_resolution:
            return {"empathy": 0.01, "solution": 0.01, "resolution": 0.01, "overall": 0.01}

        # Use model-based evaluation if available
        if self.model is not None:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                
                combined_response = " ".join([r for r in responses if len(r) > 10])
                if not combined_response:
                    return self._fallback_evaluate(responses, expected_resolution)

                from interface import Config
                targets = Config.get_semantic_targets()
                empathy_target = targets["empathy"]
                solution_target = targets["solution"]

                embeddings = self.model.encode([combined_response, empathy_target, solution_target, expected_resolution])
                embedded_resp = embeddings[0].reshape(1, -1)
                
                emb_empathy = embeddings[1].reshape(1, -1)
                emb_solution = embeddings[2].reshape(1, -1)
                emb_resolution = embeddings[3].reshape(1, -1)

                sim_empathy = float(cosine_similarity(embedded_resp, emb_empathy)[0][0])
                sim_solution = float(cosine_similarity(embedded_resp, emb_solution)[0][0])
                sim_resolution = float(cosine_similarity(embedded_resp, emb_resolution)[0][0])
                
                # Non-linear scaling
                def scale(sim):
                    return min(0.99, max(0.01, (sim - 0.1) / 0.7))

                empathy_score = scale(sim_empathy)
                solution_score = scale(sim_solution)
                resolution_score = max(0.01, min(0.99, (sim_resolution - 0.2) / 0.7))

                overall = (empathy_score * 0.2) + (solution_score * 0.2) + (resolution_score * 0.6)
                
                return {
                    "empathy": round(empathy_score, 2),
                    "solution": round(solution_score, 2),
                    "resolution": round(resolution_score, 2),
                    "overall": round(overall, 2)
                }
            except Exception:
                pass
        
        # Fallback to keyword-based evaluation
        return self._fallback_evaluate(responses, expected_resolution)

    def _fallback_evaluate(self, responses: List[str], expected_resolution: str) -> Dict[str, float]:
        """Deterministic keyword-based fallback if model is unavailable."""
        combined_response = " ".join([r.lower() for r in responses])
        expected_lower = expected_resolution.lower()

        # Simple empathy keywords
        empathy_keywords = ["understand", "sorry", "apologize", "help", "thank", "frustrated", "regret"]
        empathy_p = sum(1 for kw in empathy_keywords if kw in combined_response)
        empathy_score = min(0.99, 0.2 + (empathy_p * 0.2))

        # Simple solution keywords
        solution_keywords = ["steps", "follow", "instruction", "fix", "resolution", "process", "done"]
        solution_p = sum(1 for kw in solution_keywords if kw in combined_response)
        solution_score = min(0.99, 0.2 + (solution_p * 0.2))

        # Basic overlap for resolution alignment
        resp_words = set(combined_response.split())
        target_words = set(expected_lower.split())
        target_words = {w for w in target_words if len(w) > 3} # Filter short words
        
        if not target_words:
            resolution_score = 0.5
        else:
            overlap = len(resp_words.intersection(target_words))
            resolution_score = min(0.99, 0.1 + (overlap / len(target_words)) * 0.9)

        overall = (empathy_score * 0.2) + (solution_score * 0.2) + (resolution_score * 0.6)

        return {
            "empathy": round(empathy_score, 2),
            "solution": round(solution_score, 2),
            "resolution": round(resolution_score, 2),
            "overall": round(overall, 2)
        }

semantic_scorer = SemanticScorer()
