"""
Tests for the grading system.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.graders import SupportGrader


class TestGraderEfficiency:
    """Tests for efficiency grading edge cases."""
    
    def setup_method(self):
        self.grader = SupportGrader()
    
    def test_efficiency_no_division_by_zero_hard(self):
        """max_steps=9 should not crash for hard difficulty."""
        score = self.grader._grade_efficiency(steps=10, max_steps=9, difficulty="hard")
        assert 0.01 <= score <= 0.99
    
    def test_efficiency_no_division_by_zero_easy(self):
        """max_steps=1 should not crash for easy difficulty."""
        score = self.grader._grade_efficiency(steps=2, max_steps=1, difficulty="easy")
        assert 0.01 <= score <= 0.99
    
    def test_efficiency_zero_max_steps(self):
        """max_steps=0 should return safe default."""
        score = self.grader._grade_efficiency(steps=1, max_steps=0, difficulty="easy")
        assert score == 0.5
    
    def test_efficiency_one_step_easy(self):
        score = self.grader._grade_efficiency(steps=1, max_steps=5, difficulty="easy")
        assert score == 0.99
    
    def test_efficiency_one_step_hard(self):
        score = self.grader._grade_efficiency(steps=1, max_steps=12, difficulty="hard")
        assert score == 0.5  # Discourage one-step solutions for hard
    
    def test_efficiency_optimal_hard(self):
        """5-9 steps should get max score for hard."""
        for steps in range(5, 10):
            score = self.grader._grade_efficiency(steps=steps, max_steps=12, difficulty="hard")
            assert score == 0.99, f"Step {steps} should get 0.99"


class TestGraderActionOrdering:
    """Tests for action ordering penalty."""
    
    def setup_method(self):
        self.grader = SupportGrader()
    
    def test_correct_ordering_no_penalty(self):
        history = [
            {"type": "classify", "content": "billing"},
            {"type": "respond", "content": "I can help"},
            {"type": "resolve", "content": "Done"}
        ]
        penalty = self.grader._grade_action_ordering(history)
        assert penalty == 0.0
    
    def test_resolve_before_classify_penalized(self):
        history = [
            {"type": "resolve", "content": "Done"},
            {"type": "classify", "content": "billing"}
        ]
        penalty = self.grader._grade_action_ordering(history)
        assert penalty == -0.15
    
    def test_no_classify_with_resolve_penalized(self):
        history = [
            {"type": "respond", "content": "Helping"},
            {"type": "resolve", "content": "Done"}
        ]
        penalty = self.grader._grade_action_ordering(history)
        assert penalty == -0.15


class TestGraderEscalation:
    """Tests for escalation grading."""
    
    def setup_method(self):
        self.grader = SupportGrader()
    
    def test_correct_escalation_with_empathy(self):
        history = [
            {"type": "classify", "content": "billing"},
            {"type": "respond", "content": "I understand your frustration and I want to help."},
            {"type": "escalate", "content": "Customer requires immediate human assistance due to the severity of the issue."}
        ]
        score = self.grader._grade_escalation(history, should_escalate=True, task_difficulty="hard")
        assert score >= 0.7
    
    def test_correct_no_escalation(self):
        history = [
            {"type": "classify", "content": "billing"},
            {"type": "respond", "content": "I can help with that."},
            {"type": "resolve", "content": "Done."}
        ]
        score = self.grader._grade_escalation(history, should_escalate=False, task_difficulty="easy")
        assert score == 0.99
    
    def test_missing_required_escalation(self):
        history = [
            {"type": "classify", "content": "billing"},
            {"type": "respond", "content": "I can help."},
            {"type": "resolve", "content": "Done."}
        ]
        score = self.grader._grade_escalation(history, should_escalate=True, task_difficulty="hard")
        assert score == 0.01
    
    def test_unnecessary_escalation(self):
        history = [
            {"type": "classify", "content": "general"},
            {"type": "escalate", "content": "Escalating."}
        ]
        score = self.grader._grade_escalation(history, should_escalate=False, task_difficulty="easy")
        assert score == 0.1


class TestGraderClassification:
    """Tests for classification grading."""
    
    def setup_method(self):
        self.grader = SupportGrader()
    
    def test_exact_match(self):
        history = [{"type": "classify", "content": "billing"}]
        score = self.grader._grade_classification(history, target="billing")
        assert score == 0.99
    
    def test_no_classification(self):
        history = [{"type": "respond", "content": "Hi"}]
        score = self.grader._grade_classification(history, target="billing")
        assert score == 0.01
    
    def test_wrong_classification(self):
        history = [{"type": "classify", "content": "technical"}]
        score = self.grader._grade_classification(history, target="billing")
        assert 0.01 <= score < 0.6  # Wrong but not zero


class TestGraderFullEpisode:
    """Integration tests for full episode grading."""
    
    def setup_method(self):
        self.grader = SupportGrader()
    
    def test_full_grade_easy(self):
        result = self.grader.grade_episode(
            action_history=[
                {"type": "classify", "content": "billing"},
                {"type": "respond", "content": "I understand your concern. Here is how to fix this."},
                {"type": "resolve", "content": "Issue resolved."}
            ],
            target_category="billing",
            requires_escalation=False,
            expected_resolution="refund processed",
            is_resolved=True,
            total_steps=3,
            max_steps=5,
            task_difficulty="easy"
        )
        
        assert 0.01 <= result.score <= 0.99
        assert all(0.01 <= v <= 0.99 for v in result.breakdown.values())
