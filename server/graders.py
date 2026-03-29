"""
Deterministic graders for SupportEnv tasks.

CRITICAL: Graders must be:
1. Deterministic - same input always produces same output
2. Reproducible - works across different runs
3. Score range: 0.0 to 1.0
4. Fair - accurately measures performance
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import re


@dataclass
class GradeResult:
    """Result of grading an episode."""
    score: float  # 0.0 to 1.0
    breakdown: Dict[str, float]
    feedback: str
    passed: bool


class SupportGrader:
    """
    Grader for customer support environment episodes.
    
    Evaluates:
    - Classification accuracy
    - Response quality
    - Escalation decisions
    - Resolution efficiency
    - Tone appropriateness
    """
    
    def __init__(self):
        self.response_quality_keywords = {
            "positive": ["help", "assist", "resolve", "understand", "sorry", 
                        "apologize", "thank", "appreciate", "fixed", "processed"],
            "negative": ["can't", "won't", "impossible", "stupid", "fault"],
            "solution": ["here's what", "you can", "please try", "steps to",
                        "I've processed", "has been", "will be"]
        }
    
    def grade_episode(
        self,
        action_history: List[Dict[str, Any]],
        target_category: str,
        requires_escalation: bool,
        expected_resolution: str,
        task_difficulty: str,
        is_resolved: bool,
        total_steps: int,
        max_steps: int
    ) -> GradeResult:
        """
        Grade a complete episode.
        
        Args:
            action_history: List of actions taken [{type, content, step}]
            target_category: Correct category
            requires_escalation: Whether escalation was needed
            expected_resolution: Expected resolution text
            task_difficulty: easy/medium/hard
            is_resolved: Whether episode ended in resolution
            total_steps: Number of steps taken
            max_steps: Maximum allowed steps
            
        Returns:
            GradeResult with score 0.0-1.0 and breakdown
        """
        breakdown = {}
        
        # 1. Classification score (0.0 - 1.0)
        classification_score = self._grade_classification(
            action_history, target_category
        )
        breakdown["classification"] = classification_score
        
        # 2. Response quality score (0.0 - 1.0)
        response_score = self._grade_responses(
            action_history, task_difficulty
        )
        breakdown["response_quality"] = response_score
        
        # 3. Escalation decision score (0.0 - 1.0)
        escalation_score = self._grade_escalation(
            action_history, requires_escalation
        )
        breakdown["escalation_decision"] = escalation_score
        
        # 4. Resolution score (0.0 - 1.0)
        resolution_score = self._grade_resolution(
            is_resolved, action_history, expected_resolution
        )
        breakdown["resolution"] = resolution_score
        
        # 5. Efficiency score (0.0 - 1.0)
        efficiency_score = self._grade_efficiency(total_steps, max_steps)
        breakdown["efficiency"] = efficiency_score
        
        # Compute weighted total based on difficulty
        weights = self._get_weights(task_difficulty)
        
        total_score = sum(
            breakdown[key] * weights.get(key, 0.0)
            for key in breakdown
        )
        
        # Apply action ordering penalty
        ordering_penalty = self._grade_action_ordering(action_history)
        total_score += ordering_penalty
        
        # Ensure score is in valid range
        total_score = max(0.0, min(1.0, total_score))
        
        # Generate feedback
        feedback = self._generate_feedback(breakdown, task_difficulty)
        
        # Determine pass/fail
        passed = total_score >= 0.6
        
        return GradeResult(
            score=round(total_score, 4),
            breakdown={k: round(v, 4) for k, v in breakdown.items()},
            feedback=feedback,
            passed=passed
        )
        
    def _grade_action_ordering(self, action_history: List[Dict[str, Any]]) -> float:
        """Penalize if resolution or escalation happens before classification."""
        idx_classify = -1
        idx_resolve_or_escalate = -1
        for i, a in enumerate(action_history):
            t = a.get("type")
            if t == "classify" and idx_classify == -1:
                idx_classify = i
            elif t in ["escalate", "resolve"] and idx_resolve_or_escalate == -1:
                idx_resolve_or_escalate = i
                
        if idx_resolve_or_escalate != -1:
            if idx_classify == -1 or idx_resolve_or_escalate < idx_classify:
                return -0.25 # Penalty
        return 0.0
        
    def _get_model(self):
        if not hasattr(self, '_model') or self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                self._model = None
        return self._model
    
    def _grade_classification(
        self, 
        action_history: List[Dict[str, Any]], 
        target: str
    ) -> float:
        """Grade classification accuracy."""
        classifications = [
            a for a in action_history if a.get("type") == "classify"
        ]
        
        if not classifications:
            return 0.0  # No classification attempted
        
        # Check first classification (most important)
        first_class = classifications[0].get("content", "").lower().strip()
        target_clean = target.lower().strip()
        
        if first_class == target_clean:
            return 1.0
        
        # Partial credit for related categories
        category_relations = {
            "billing": ["payment", "charge", "refund", "invoice"],
            "technical": ["bug", "error", "crash", "issue"],
            "account": ["login", "password", "access", "profile"],
            "general": ["question", "info", "inquiry", "other"]
        }
        
        for category, related in category_relations.items():
            if target_clean == category:
                if first_class in related:
                    return 0.6  # Related but not exact
        
        # Check if correct classification was made later
        for cls in classifications[1:]:
            if cls.get("content", "").lower().strip() == target_clean:
                return 0.5  # Corrected but not first try
        
        return 0.2  # Wrong classification
    
    def _grade_responses(
        self, 
        action_history: List[Dict[str, Any]],
        difficulty: str
    ) -> float:
        """Grade overall response quality."""
        responses = [
            a for a in action_history if a.get("type") == "respond"
        ]
        
        if not responses:
            return 0.0
        
        total_score = 0.0
        
        for response in responses:
            content = response.get("content", "").lower()
            
            # Check for positive keywords
            positive_count = sum(
                1 for kw in self.response_quality_keywords["positive"]
                if kw in content
            )
            
            # Check for negative keywords (penalty)
            negative_count = sum(
                1 for kw in self.response_quality_keywords["negative"]
                if kw in content
            )
            
            # Check for solution-oriented language
            solution_count = sum(
                1 for kw in self.response_quality_keywords["solution"]
                if kw in content
            )
            
            # Response length check
            word_count = len(content.split())
            length_score = min(1.0, word_count / 20)  # At least 20 words ideal
            
            # Compute individual response score
            resp_score = (
                min(1.0, positive_count * 0.15) +
                min(0.4, solution_count * 0.2) +
                length_score * 0.3 -
                negative_count * 0.3
            )
            
            total_score += max(0.0, min(1.0, resp_score))
        
        # Average across responses
        avg_score = total_score / len(responses)
        
        # Higher standards for harder difficulties
        if difficulty == "hard":
            avg_score *= 0.85  # Harder to get high score
        elif difficulty == "medium":
            avg_score *= 0.92
        
        return min(1.0, avg_score)
    
    def _grade_escalation(
        self, 
        action_history: List[Dict[str, Any]],
        should_escalate: bool
    ) -> float:
        """Grade escalation decision."""
        escalations = [
            a for a in action_history if a.get("type") == "escalate"
        ]
        
        escalated = len(escalations) > 0
        
        if should_escalate and escalated:
            # Correct: escalated when needed
            # Check if escalation had valid reason
            reason = escalations[0].get("content", "")
            if len(reason.split()) >= 5:
                return 1.0
            return 0.8  # Right decision but poor explanation
            
        elif not should_escalate and not escalated:
            # Correct: did not escalate when not needed
            return 1.0
            
        elif should_escalate and not escalated:
            # Wrong: should have escalated but didn't
            return 0.1
            
        else:
            # Wrong: escalated when not needed
            return 0.3
    
    def _grade_resolution(
        self,
        is_resolved: bool,
        action_history: List[Dict[str, Any]],
        expected_resolution: str
    ) -> float:
        """Grade resolution quality."""
        if not is_resolved:
            return 0.2  # Partial credit for attempting
        
        # Find resolution action
        resolutions = [
            a for a in action_history if a.get("type") == "resolve"
        ]
        
        if not resolutions:
            return 0.5  # Resolved but no explicit resolution action
        
        resolution_content = resolutions[-1].get("content", "").lower()
        expected_lower = expected_resolution.lower()
        
        model = self._get_model()
        if model is not None:
            try:
                from sentence_transformers import util
                emb1 = model.encode(resolution_content)
                emb2 = model.encode(expected_lower)
                sim = float(util.cos_sim(emb1, emb2)[0][0])
                return min(1.0, max(0.0, sim))
            except Exception:
                pass
                
        # Fallback to key terms overlap
        expected_terms = set(expected_lower.split())
        resolution_terms = set(resolution_content.split())
        
        overlap = len(expected_terms & resolution_terms)
        overlap_ratio = overlap / max(len(expected_terms), 1)
        
        return min(1.0, 0.5 + overlap_ratio * 0.5)
    
    def _grade_efficiency(self, steps: int, max_steps: int) -> float:
        """Grade step efficiency."""
        if steps <= max_steps // 3:
            return 1.0  # Very efficient
        elif steps <= max_steps // 2:
            return 0.8
        elif steps <= max_steps * 0.7:
            return 0.6
        elif steps < max_steps:
            return 0.4
        else:
            return 0.2  # Used all steps
    
    def _get_weights(self, difficulty: str) -> Dict[str, float]:
        """Get grading weights based on difficulty."""
        if difficulty == "easy":
            return {
                "classification": 0.30,
                "response_quality": 0.40,
                "escalation_decision": 0.05,
                "resolution": 0.15,
                "efficiency": 0.10
            }
        elif difficulty == "medium":
            return {
                "classification": 0.25,
                "response_quality": 0.30,
                "escalation_decision": 0.10,
                "resolution": 0.20,
                "efficiency": 0.15
            }
        else:  # hard
            return {
                "classification": 0.15,
                "response_quality": 0.20,
                "escalation_decision": 0.30,
                "resolution": 0.20,
                "efficiency": 0.15
            }
    
    def _generate_feedback(
        self, 
        breakdown: Dict[str, float],
        difficulty: str
    ) -> str:
        """Generate human-readable feedback."""
        feedback_parts = []
        
        for key, score in breakdown.items():
            if score >= 0.8:
                feedback_parts.append(f"{key}: Excellent ({score:.2f})")
            elif score >= 0.6:
                feedback_parts.append(f"{key}: Good ({score:.2f})")
            elif score >= 0.4:
                feedback_parts.append(f"{key}: Needs improvement ({score:.2f})")
            else:
                feedback_parts.append(f"{key}: Poor ({score:.2f})")
        
        return f"[{difficulty.upper()}] " + " | ".join(feedback_parts)


def grade_task(
    task_id: str,
    episode_data: Dict[str, Any]
) -> GradeResult:
    """
    Convenience function to grade a task.
    
    Args:
        task_id: The task identifier
        episode_data: Dictionary containing episode information
        
    Returns:
        GradeResult
    """
    grader = SupportGrader()
    
    return grader.grade_episode(
        action_history=episode_data.get("action_history", []),
        target_category=episode_data.get("target_category", ""),
        requires_escalation=episode_data.get("requires_escalation", False),
        expected_resolution=episode_data.get("expected_resolution", ""),
        task_difficulty=episode_data.get("task_difficulty", "easy"),
        is_resolved=episode_data.get("is_resolved", False),
        total_steps=episode_data.get("total_steps", 0),
        max_steps=episode_data.get("max_steps", 10)
    )