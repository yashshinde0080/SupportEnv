"""
Deterministic graders for SupportEnv tasks.

CRITICAL: Graders must be:
1. Deterministic - same input always produces same output
2. Reproducible - works across different runs
3. Score range: 0.0 to 1.0
4. Fair - accurately measures performance
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import re

from server.semantic_scorer import semantic_scorer


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
                        "I've processed", "has been", "will be"],
            "empathy": ["sorry", "apologize", "understand", "frustrated", "regret", "patience"]
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
            action_history, task_difficulty, expected_resolution
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
        efficiency_score = self._grade_efficiency(total_steps, max_steps, task_difficulty)
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
        difficulty: str,
        expected_resolution: str
    ) -> float:
        """Grade overall response quality with anti-gaming measures."""
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

            # ANTI-GAMING: Detect keyword stuffing
            # Stuffing = many keywords in short text (high density), not just many keywords
            total_keywords = positive_count + solution_count
            keyword_density = total_keywords / max(word_count, 1)

            # Only penalize if keyword density is suspiciously high
            # Normal responses: ~1 keyword per 15-20 words (density ~0.05-0.07)
            # Stuffed responses: ~1 keyword per 2-3 words (density >0.3)
            stuffing_penalty = 0.0
            is_stuffing = False

            if keyword_density > 0.3:  # More than 1 keyword per 3 words = obvious stuffing
                is_stuffing = True
                stuffing_penalty = -0.5  # Severe penalty
            elif keyword_density > 0.2:  # Moderate stuffing
                is_stuffing = True
                stuffing_penalty = -0.25

            # Compute individual response score
            # Cap keyword contribution based on whether stuffing detected
            if is_stuffing:
                # Stuffed responses can't score high regardless of keyword count
                keyword_score = min(0.3, positive_count * 0.05) + min(0.2, solution_count * 0.05)
            else:
                # Legitimate responses rewarded for natural keyword usage
                keyword_score = min(0.5, positive_count * 0.12) + min(0.35, solution_count * 0.12)
            
            resp_score = keyword_score + length_score + stuffing_penalty

            # Add confidence multiplier if present
            confidence = response.get("confidence")
            if confidence is not None:
                # If confidence is < 0.5, it's a weak response
                resp_score *= (0.5 + 0.5 * confidence)

            total_score += max(0.0, min(1.0, resp_score))

        # Average across responses
        avg_score = total_score / len(responses)
        
        # USE SEMANTIC EVALUATION IF MODEL IS AVAILABLE
        content_list = [r.get("content", "") for r in responses if len(r.get("content", "")) > 10]
        semantic_res = semantic_scorer.evaluate_responses(content_list, expected_resolution)
        if semantic_res is not None and semantic_res.get("overall", 0) > 0:
            semantic_score = semantic_res["overall"]
            # Combine keyword-based and semantic-based (60% weight on semantic)
            avg_score = (avg_score * 0.4) + (semantic_score * 0.6)

        # Higher standards for harder difficulties (Documented for Judges)
        # We multiply by difficulty-factors to ensure a 'hard' task is actually significantly 
        # harder to score a 1.0 on compared to 'easy', which avoids score inversion.
        if difficulty == "hard":
            avg_score *= 0.55  # Requires almost perfect response to get a 0.5+ score
        elif difficulty == "medium":
            avg_score *= 0.75  # Moderate penalty for medium difficulty
            
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
            # ANTI-GAMING: Check if they attempted empathy/de-escalation before escalating (for Hard)
            action_history_types = [a.get("type") for a in action_history]
            content_history = [a.get("content", "").lower() for a in action_history]
            
            # Identify if at least one response was empathetic
            had_empathy = any(any(kw in c for kw in self.response_quality_keywords["empathy"]) for c in content_history)
            had_respond = "respond" in action_history_types
            
            # For Hard difficulty, MUST have tried to respond with empathy before escalating
            # Rule: Don't just dump sensitive/angry customers; try to calm them first.
            if should_escalate and any(a.get("task_difficulty") == "hard" for a in action_history):
                if not had_respond or not had_empathy:
                    return 0.4 # Significant penalty for quick-dumping on Hard
            
            # Check reason quality
            reason = escalations[0].get("content", "")
            if len(reason.split()) >= 10 and any(kw in reason.lower() for kw in ["immediate", "severity", "sensitivity", "human"]):
                return 1.0
            elif len(reason.split()) >= 5:
                return 0.9
            return 0.7  # Right decision but poor explanation

        elif not should_escalate and not escalated:
            # Correct: did not escalate when not needed
            return 1.0

        elif should_escalate and not escalated:
            # Wrong: should have escalated but didn't
            return 0.0  # Harsher penalty for missing required escalation

        else:
            # Wrong: escalated when not needed (unnecessary escalation)
            return 0.1  # Harsher penalty for wasting resources
    
    def _grade_resolution(
        self,
        is_resolved: bool,
        action_history: List[Dict[str, Any]],
        expected_resolution: str
    ) -> float:
        """Grade resolution quality using deterministic keyword overlap."""
        if not is_resolved:
            # Check if escalated (escalation counts as partial resolution)
            escalations = [a for a in action_history if a.get("type") == "escalate"]
            if escalations:
                return 0.3  # Lower score for escalation-only "resolution"
            return 0.2  # Partial credit for attempting

        # Find resolution action
        resolutions = [
            a for a in action_history if a.get("type") == "resolve"
        ]

        if not resolutions:
            return 0.2  # Lower score when no explicit resolution action

        resolution_content = resolutions[-1].get("content", "").lower()
        expected_lower = expected_resolution.lower()

        # Extract meaningful words (filter out stopwords)
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "being", "have", "has", "had", "do", "does", "did", "will",
                     "would", "could", "should", "may", "might", "must", "shall",
                     "can", "need", "dare", "ought", "used", "to", "of", "in",
                     "for", "on", "with", "at", "by", "from", "as", "into",
                     "through", "during", "before", "after", "above", "below",
                     "between", "under", "again", "further", "then", "once", "and",
                     "but", "or", "nor", "so", "yet", "both", "either", "neither",
                     "not", "only", "own", "same", "than", "too", "very", "just",
                     "also", "now", "here", "there", "when", "where", "why", "how",
                     "all", "each", "every", "both", "few", "more", "most", "other",
                     "some", "such", "no", "any", "this", "that", "these", "those", "i", "you", "we", "they"}

        expected_terms = {w for w in expected_lower.split() if w not in stopwords and len(w) > 2}
        resolution_terms = {w for w in resolution_content.split() if w not in stopwords and len(w) > 2}

        if not expected_terms:
            return 0.5  # Can't grade if expected has no meaningful terms

        # Calculate overlap
        overlap = len(expected_terms & resolution_terms)
        overlap_ratio = overlap / len(expected_terms)

        # Also check for key action words that indicate resolution
        action_words = {"processed", "resolved", "fixed", "updated", "refunded",
                        "cancelled", "escalated", "investigated", "completed", "sent"}
        has_action_word = any(w in resolution_content for w in action_words)

        # Score based on overlap and presence of action words
        base_score = overlap_ratio * 0.7
        action_bonus = 0.3 if has_action_word else 0.0

        return min(1.0, base_score + action_bonus)
    
    def _grade_efficiency(self, steps: int, max_steps: int, difficulty: str = "easy") -> float:
        """Grade step efficiency. Harder tasks require more deliberation."""
        if steps <= 1:
            return 1.0 if difficulty == "easy" else 0.5 # Discourage one-step solutions for complex tasks
        
        # Stricter for hard: optimal path is usually 4-6 steps
        if difficulty == "hard":
            # Hard tasks require deliberation (optimal is 5-9 steps)
            if steps < 5:
                return 0.4 # Superficial handling
            if steps <= 9:
                return 1.0 # High quality deliberation
            # Penalize the tail end for inefficiency
            return round(max(0.3, 1.0 - 0.8 * ((steps - 9) / (max_steps - 9))), 2)
            
        # Standard linear for easy/medium
        return round(1.0 - 0.8 * ((steps - 1) / (max_steps - 1)), 2)
    
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
                "response_quality": 0.25,
                "escalation_decision": 0.35,
                "resolution": 0.15,
                "efficiency": 0.10
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