"""
Semantic scoring functionality using sentence transformers.
Evaluates agent responses for empathy, solution-orientation, and resolution alignment.
"""

from typing import List, Dict, Any, Optional

class SemanticScorer:
    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Using a small, fast model suitable for CPU inference in HF Spaces
                self._model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                return None
        return self._model

    def evaluate_responses(self, responses: List[str], expected_resolution: str) -> Optional[Dict[str, float]]:
        """
        Evaluate the overall semantic quality of a list of responses
        Returns a dict with empathy, solution, and resolution alignment scores.
        """
        if not responses or not expected_resolution:
            return {"empathy": 0.0, "solution": 0.0, "resolution": 0.0, "overall": 0.0}

        if self.model is None:
            return None

        combined_response = " ".join([r for r in responses if len(r) > 10])
        if not combined_response:
            return {"empathy": 0.0, "solution": 0.0, "resolution": 0.0, "overall": 0.0}

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            empathy_target = "I understand your frustration, I am here to help you."
            solution_target = "I have a solution for you, please try to follow these steps:"

            embeddings = self.model.encode([combined_response, empathy_target, solution_target, expected_resolution])
            embedded_resp = embeddings[0].reshape(1, -1)
            
            emb_empathy = embeddings[1].reshape(1, -1)
            emb_solution = embeddings[2].reshape(1, -1)
            emb_resolution = embeddings[3].reshape(1, -1)

            sim_empathy = float(cosine_similarity(embedded_resp, emb_empathy)[0][0])
            sim_solution = float(cosine_similarity(embedded_resp, emb_solution)[0][0])
            sim_resolution = float(cosine_similarity(embedded_resp, emb_resolution)[0][0])
            
            # Non-linear scaling: 0.2 similarity is baseline, 0.9 similarity is perfect.
            def scale(sim):
                return min(1.0, max(0.0, (sim - 0.1) / 0.7))

            empathy_score = scale(sim_empathy)
            solution_score = scale(sim_solution)
            resolution_score = max(0.0, min(1.0, (sim_resolution - 0.2) / 0.7))

            overall = (empathy_score * 0.2) + (solution_score * 0.2) + (resolution_score * 0.6)
            
            return {
                "empathy": empathy_score,
                "solution": solution_score,
                "resolution": resolution_score,
                "overall": overall
            }
        except Exception:
            # Fallback if something goes wrong
            return None

semantic_scorer = SemanticScorer()
