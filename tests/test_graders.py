"""
Unit tests for graders.
"""

import pytest
from server.graders import SupportGrader, GradeResult, grade_task


class TestGraderBasics:
    """Test basic grader functionality."""
    
    def test_grade_returns_result(self):
        """Grader should return GradeResult."""
        grader = SupportGrader()
        
        result = grader.grade_episode(
            action_history=[
                {"type": "classify", "content": "billing", "step": 1},
                {"type": "respond", "content": "Thank you for your help.", "step": 2},
            ],
            target_category="billing",
            requires_escalation=False,
            expected_resolution="Issue resolved",
            task_difficulty="easy",
            is_resolved=True,
            total_steps=2,
            max_steps=5
        )
        
        assert isinstance(result, GradeResult)
        assert 0.0 <= result.score <= 1.0
    
    def test_score_in_range(self):
        """Score should always be 0.0 to 1.0."""
        grader = SupportGrader()
        
        # Test various scenarios
        scenarios = [
            # Perfect case
            {
                "action_history": [
                    {"type": "classify", "content": "billing", "step": 1},
                    {"type": "respond", "content": "I understand and I'm sorry. Here's how to fix it.", "step": 2},
                    {"type": "resolve", "content": "Issue resolved", "step": 3}
                ],
                "target_category": "billing",
                "requires_escalation": False,
                "expected_resolution": "Issue resolved",
                "task_difficulty": "easy",
                "is_resolved": True,
                "total_steps": 3,
                "max_steps": 5
            },
            # Worst case
            {
                "action_history": [],
                "target_category": "billing",
                "requires_escalation": True,
                "expected_resolution": "Escalate",
                "task_difficulty": "hard",
                "is_resolved": False,
                "total_steps": 10,
                "max_steps": 10
            }
        ]
        
        for scenario in scenarios:
            result = grader.grade_episode(**scenario)
            assert 0.0 <= result.score <= 1.0, f"Score {result.score} out of range"
    
    def test_deterministic_scoring(self):
        """Same input should produce same output."""
        grader = SupportGrader()
        
        kwargs = {
            "action_history": [
                {"type": "classify", "content": "billing", "step": 1}
            ],
            "target_category": "billing",
            "requires_escalation": False,
            "expected_resolution": "Done",
            "task_difficulty": "easy",
            "is_resolved": True,
            "total_steps": 1,
            "max_steps": 5
        }
        
        result1 = grader.grade_episode(**kwargs)
        result2 = grader.grade_episode(**kwargs)
        
        assert result1.score == result2.score
        assert result1.breakdown == result2.breakdown


class TestClassificationGrading:
    """Test classification grading."""
    
    def test_correct_classification_scores_high(self):
        """Correct classification should score 1.0."""
        grader = SupportGrader()
        
        result = grader.grade_episode(
            action_history=[
                {"type": "classify", "content": "billing", "step": 1}
            ],
            target_category="billing",
            requires_escalation=False,
            expected_resolution="Done",
            task_difficulty="easy",
            is_resolved=True,
            total_steps=1,
            max_steps=5
        )
        
        assert result.breakdown["classification"] == 1.0
    
    def test_wrong_classification_scores_low(self):
        """Wrong classification should score low."""
        grader = SupportGrader()
        
        result = grader.grade_episode(
            action_history=[
                {"type": "classify", "content": "technical", "step": 1}
            ],
            target_category="billing",
            requires_escalation=False,
            expected_resolution="Done",
            task_difficulty="easy",
            is_resolved=True,
            total_steps=1,
            max_steps=5
        )
        
        assert result.breakdown["classification"] < 1.0


class TestEscalationGrading:
    """Test escalation decision grading."""
    
    def test_correct_escalation(self):
        """Escalating when needed (with empathy first on hard) should score high."""
        grader = SupportGrader()
        
        result = grader.grade_episode(
            action_history=[
                {"type": "respond", "content": "I'm so sorry to hear about this. I understand how upsetting this must be.", "step": 1},
                {"type": "escalate", "content": "Customer is threatening legal action due to severity and sensitivity of the issue", "step": 2}
            ],
            target_category="billing",
            requires_escalation=True,
            expected_resolution="Escalate",
            task_difficulty="hard",
            is_resolved=True,
            total_steps=2,
            max_steps=10
        )
        
        assert result.breakdown["escalation_decision"] >= 0.8
    
    def test_unnecessary_escalation(self):
        """Escalating when not needed should score low."""
        grader = SupportGrader()
        
        result = grader.grade_episode(
            action_history=[
                {"type": "escalate", "content": "Not sure what to do", "step": 1}
            ],
            target_category="billing",
            requires_escalation=False,
            expected_resolution="Simple resolution",
            task_difficulty="easy",
            is_resolved=True,
            total_steps=1,
            max_steps=5
        )
        
        assert result.breakdown["escalation_decision"] < 0.5


class TestEfficiencyGrading:
    """Test efficiency grading."""
    
    def test_fast_resolution_scores_high(self):
        """Quick resolution should score high efficiency."""
        grader = SupportGrader()
        
        result = grader.grade_episode(
            action_history=[
                {"type": "classify", "content": "billing", "step": 1},
                {"type": "resolve", "content": "Done", "step": 2}
            ],
            target_category="billing",
            requires_escalation=False,
            expected_resolution="Done",
            task_difficulty="easy",
            is_resolved=True,
            total_steps=2,
            max_steps=10
        )
        
        assert result.breakdown["efficiency"] >= 0.8
    
    def test_slow_resolution_scores_low(self):
        """Slow resolution should score low efficiency."""
        grader = SupportGrader()
        
        # Many steps
        actions = [{"type": "request_info", "content": f"Info {i}", "step": i} 
                   for i in range(1, 10)]
        
        result = grader.grade_episode(
            action_history=actions,
            target_category="billing",
            requires_escalation=False,
            expected_resolution="Done",
            task_difficulty="easy",
            is_resolved=True,
            total_steps=9,
            max_steps=10
        )
        
        assert result.breakdown["efficiency"] < 0.5

    def test_fast_resolution_on_hard_mode_penalized(self):
        """Quick resolution on hard mode should score low efficiency due to required deliberation."""
        grader = SupportGrader()
        
        result = grader.grade_episode(
            action_history=[
                {"type": "classify", "content": "billing", "step": 1},
                {"type": "resolve", "content": "Done", "step": 2}
            ],
            target_category="billing",
            requires_escalation=False,
            expected_resolution="Done",
            task_difficulty="hard",
            is_resolved=True,
            total_steps=2,
            max_steps=10
        )
        
        # In hard mode, quick resolution signifies guessing or poor deliberation
        assert result.breakdown["efficiency"] <= 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])