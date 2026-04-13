"""
Reward computation for SupportEnv.

Key Design Principles:
1. Dense rewards (not sparse) - provide signal at every step
2. Partial progress rewarded - encourage learning
3. Bad actions penalized - discourage harmful behavior
4. No loopholes - can't game the system
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re
from server.semantic_scorer import semantic_scorer


@dataclass
class RewardBreakdown:
    """Detailed breakdown of reward computation."""
    total: float
    classification_reward: float = 0.0
    response_reward: float = 0.0
    escalation_reward: float = 0.0
    efficiency_reward: float = 0.0
    tone_reward: float = 0.0
    kb_reward: float = 0.0
    penalty: float = 0.0
    reason: str = ""


class RewardEngine:
    """
    Computes rewards for agent actions.
    
    Reward Range: -1.0 to +1.0 per step
    Cumulative rewards can exceed this range over an episode.
    """
    
    # Reward values
    CORRECT_CLASSIFICATION = 0.25
    WRONG_CLASSIFICATION = -0.15
    
    GOOD_RESPONSE = 0.30
    ADEQUATE_RESPONSE = 0.15
    POOR_RESPONSE = -0.10
    HARMFUL_RESPONSE = -0.40
    
    CORRECT_ESCALATION = 0.35
    UNNECESSARY_ESCALATION = -0.20
    MISSED_ESCALATION = -0.35
    
    RESOLUTION_BONUS = 0.40
    EFFICIENCY_BONUS = 0.10
    
    # Penalties
    REPEATED_ACTION = -0.15
    HALLUCINATION = -0.30
    INVALID_ACTION = -0.10
    TOO_MANY_STEPS = -0.05  # Per step over optimal
    SLA_BREACH = -0.50
    
    # Response quality keywords (positive)
    EMPATHY_KEYWORDS = ["understand", "sorry", "apologize", "appreciate", "thank you", "help"]
    SOLUTION_KEYWORDS = ["here's", "you can", "please try", "resolved", "fixed", "processed"]
    
    # Response quality keywords (negative)
    HARMFUL_KEYWORDS = ["stupid", "fault", "impossible", "can't help", "not my problem"]
    
    def __init__(self):
        self.action_history: List[str] = []
        self.classification_made = False
        self.classification_correct = False
    
    def reset(self):
        """Reset for new episode."""
        self.action_history = []
        self.classification_made = False
        self.classification_correct = False
    
    def compute_reward(
        self,
        action_type: str,
        action_content: str,
        target_category: str,
        requires_escalation: bool,
        customer_sentiment: float,
        step_count: int,
        max_steps: int,
        is_resolved: bool,
        task_difficulty: str,
        target_resolution: str = "",
        confidence: Optional[float] = None
    ) -> RewardBreakdown:
        """
        Compute reward for a single action.
        
        Args:
            action_type: Type of action taken
            action_content: Content of the action
            target_category: Correct category for classification
            requires_escalation: Whether ticket should be escalated
            customer_sentiment: Current customer sentiment (-1 to 1)
            step_count: Current step number
            max_steps: Maximum allowed steps
            is_resolved: Whether issue is resolved
            task_difficulty: easy/medium/hard
            confidence: Optional confidence string or float
            
        Returns:
            RewardBreakdown with detailed reward computation
        """
        breakdown = RewardBreakdown(total=0.0)
        
        # Check for repeated action
        action_key = f"{action_type}:{action_content[:50]}"
        if action_key in self.action_history:
            breakdown.penalty += self.REPEATED_ACTION
            breakdown.reason += "Repeated action penalty. "
        self.action_history.append(action_key)
        
        # Compute action-specific reward
        if action_type == "classify":
            breakdown.classification_reward = self._compute_classification_reward(
                action_content, target_category
            )
            breakdown.reason += f"Classification: {action_content}. "
            
        elif action_type == "respond":
            breakdown.response_reward = self._compute_response_reward(
                action_content, customer_sentiment, task_difficulty, target_resolution
            )
            breakdown.tone_reward = self._compute_tone_reward(
                action_content, customer_sentiment
            )
            breakdown.reason += "Response evaluated. "
            
        elif action_type == "escalate":
            breakdown.escalation_reward = self._compute_escalation_reward(
                requires_escalation, action_content
            )
            breakdown.reason += f"Escalation decision: {'correct' if requires_escalation else 'unnecessary'}. "
            
        elif action_type == "resolve":
            if is_resolved or self._check_resolution_valid(action_content):
                breakdown.total += self.RESOLUTION_BONUS
                breakdown.reason += "Valid resolution. "
            else:
                breakdown.penalty += self.POOR_RESPONSE
                breakdown.reason += "Premature resolution. "
                
        elif action_type == "request_info":
            # Small reward for appropriate information gathering
            # Threshold is proportional to task complexity (40% of max steps)
            info_threshold = max(3, int(max_steps * 0.4))
            if step_count < info_threshold and task_difficulty in ["medium", "hard"]:
                breakdown.response_reward = 0.10
                breakdown.reason += "Information gathering. "
            else:
                breakdown.penalty += -0.05
                breakdown.reason += "Unnecessary info request. "
                
        elif action_type == "lookup_kb":
            if task_difficulty in ["medium", "hard"]:
                breakdown.kb_reward = 0.15
                breakdown.reason += "Appropriate KB usage. "
            else:
                breakdown.penalty += -0.10
                breakdown.reason += "Unnecessary KB lookup on easy task. "
        
        # Step penalty for taking too long / SLA Breach
        if step_count >= max_steps:
            breakdown.penalty += self.SLA_BREACH
            breakdown.reason += "SLA breached (max steps reached). "
        elif step_count > max_steps * 0.7:
            breakdown.penalty += self.TOO_MANY_STEPS
            
        # Compute total from all components
        breakdown.total = (
            breakdown.classification_reward +
            breakdown.response_reward +
            breakdown.escalation_reward +
            breakdown.efficiency_reward +
            breakdown.tone_reward +
            breakdown.kb_reward +
            breakdown.penalty
        )
        
        # Calibrated Confidence adjustment (applied AFTER base total)
        if confidence is not None:
            # Reward being confident when right, penalize when confident and wrong
            if breakdown.total > 0:
                breakdown.total += (confidence - 0.5) * 0.1
                breakdown.reason += f"Confidence bonus ({confidence}). "
            elif breakdown.total < 0:
                breakdown.total -= confidence * 0.1
                breakdown.reason += f"Overconfidence penalty ({confidence}). "
        
        # Clamp total to reasonable range
        breakdown.total = max(-1.0, min(1.0, breakdown.total))
        
        return breakdown

    
    def _compute_classification_reward(self, predicted: str, target: str) -> float:
        """Compute reward for classification action."""
        predicted_clean = predicted.lower().strip()
        target_clean = target.lower().strip()
        
        if predicted_clean == target_clean:
            self.classification_made = True
            self.classification_correct = True
            return self.CORRECT_CLASSIFICATION
        
        # Partial credit for related categories
        related_categories = {
            "billing": ["payment", "charge", "refund", "invoice"],
            "technical": ["bug", "error", "crash", "issue"],
            "account": ["login", "password", "access", "profile"],
            "general": ["question", "info", "inquiry", "other"]
        }
        
        for category, related in related_categories.items():
            if target_clean == category and predicted_clean in related:
                self.classification_made = True
                return self.CORRECT_CLASSIFICATION * 0.5
        
        self.classification_made = True
        return self.WRONG_CLASSIFICATION
    
    def _compute_response_reward(
        self, 
        response: str, 
        sentiment: float,
        difficulty: str,
        target_resolution: str = ""
    ) -> float:
        """Compute reward for response quality, aligned with SupportGrader logic."""
        response_lower = response.lower()
        
        # 1. Check for harmful content (Critical Failure)
        for keyword in self.HARMFUL_KEYWORDS:
            if keyword in response_lower:
                return self.HARMFUL_RESPONSE
        
        # 2. Check response length
        word_count = len(response.split())
        if word_count < 5:
            return self.POOR_RESPONSE
        
        # 3. Keyword-based heuristic (Empathy & Solution)
        solution_count = sum(1 for kw in self.SOLUTION_KEYWORDS if kw in response_lower)
        empathy_count = sum(1 for kw in self.EMPATHY_KEYWORDS if kw in response_lower)
        
        # Map keywords to a 0.0-1.0 base score (max 0.4 for keywords)
        keyword_base = (min(2, empathy_count) * 0.15) + (min(2, solution_count) * 0.05)
        
        # 4. Semantic evaluation (if available and target known)
        semantic_score = 0.0
        if target_resolution and len(response) > 10:
            res = semantic_scorer.evaluate_responses([response], target_resolution)
            if res:
                semantic_score = res.get("overall", 0.0)
        
        # 5. Blend scores (same 40/60 blend as SupportGrader)
        if semantic_score > 0:
            avg_score = (keyword_base * 0.4) + (semantic_score * 0.6)
        else:
            avg_score = keyword_base
            
        # 6. Apply difficulty-based graduated scaling (aligned with SupportGrader)
        #    hard   → scores below 0.7 compressed ×0.75
        #    medium → scores below 0.6 compressed ×0.85
        #    easy   → no adjustment
        if difficulty == "hard":
            if avg_score < 0.7:
                avg_score *= 0.75
        elif difficulty == "medium":
            if avg_score < 0.6:
                avg_score *= 0.85

        normalized_score = max(0.0, min(1.0, avg_score))

        return self.GOOD_RESPONSE * normalized_score if normalized_score > 0 else self.POOR_RESPONSE * (1.0 - avg_score)
    
    def _compute_tone_reward(self, response: str, sentiment: float) -> float:
        """Compute reward for appropriate tone given customer sentiment."""
        response_lower = response.lower()
        
        # For angry customers (negative sentiment), empathy is crucial
        if sentiment < -0.5:
            empathy_count = sum(1 for kw in self.EMPATHY_KEYWORDS if kw in response_lower)
            if empathy_count >= 2:
                return 0.15  # Good de-escalation
            elif empathy_count >= 1:
                return 0.05
            else:
                return -0.10  # Failed to address emotions
        
        return 0.0
    
    def _compute_escalation_reward(self, should_escalate: bool, reason: str) -> float:
        """Compute reward for escalation decision."""
        has_valid_reason = len(reason.split()) > 3  # Requires some explanation
        
        if should_escalate:
            if has_valid_reason:
                return self.CORRECT_ESCALATION
            else:
                return self.CORRECT_ESCALATION * 0.7  # Right decision, poor execution
        else:
            return self.UNNECESSARY_ESCALATION
    
    def _check_resolution_valid(self, resolution_summary: str) -> bool:
        """Check if resolution summary is valid."""
        return len(resolution_summary.split()) >= 5
    
    def compute_episode_final_reward(
        self,
        is_resolved: bool,
        classification_correct: bool,
        escalation_correct: bool,
        total_steps: int,
        max_steps: int
    ) -> float:
        """
        Compute final bonus/penalty at episode end.
        This is in addition to step-by-step rewards.
        """
        final_reward = 0.0
        
        if is_resolved:
            final_reward += 0.30
            
            # Efficiency bonus
            efficiency_ratio = 1 - (total_steps / max_steps)
            final_reward += efficiency_ratio * 0.20
        else:
            final_reward -= 0.40  # Failed to resolve
        
        if classification_correct:
            final_reward += 0.15
        
        if escalation_correct:
            final_reward += 0.15
        
        return final_reward