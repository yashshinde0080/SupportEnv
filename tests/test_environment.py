"""
Tests for the SupportEnvironment core module.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.environment import SupportEnvironment
from models import SupportAction


class TestEnvironmentReset:
    """Tests for environment reset functionality."""
    
    def test_reset_returns_valid_observation(self):
        env = SupportEnvironment()
        obs = env.reset(seed=42, difficulty="easy")
        assert obs is not None
        assert obs.ticket_id != ""
        assert obs.ticket_text != ""
        assert obs.done is False
    
    def test_reset_with_each_difficulty(self):
        for diff in ["easy", "medium", "hard"]:
            env = SupportEnvironment()
            obs = env.reset(seed=42, difficulty=diff)
            assert obs.task_difficulty == diff
            assert obs.max_steps > 0
    
    def test_reset_deterministic_with_same_seed(self):
        env1 = SupportEnvironment()
        obs1 = env1.reset(seed=42, difficulty="easy")
        
        env2 = SupportEnvironment()
        obs2 = env2.reset(seed=42, difficulty="easy")
        
        assert obs1.ticket_text == obs2.ticket_text
        assert obs1.ticket_subject == obs2.ticket_subject


class TestEnvironmentStep:
    """Tests for environment step transitions."""
    
    def test_step_classify(self):
        env = SupportEnvironment()
        env.reset(seed=42, difficulty="easy")
        
        action = SupportAction(action_type="classify", content="billing")
        obs = env.step(action)
        assert obs is not None
        assert obs.is_classified is True
    
    def test_step_respond(self):
        env = SupportEnvironment()
        env.reset(seed=42, difficulty="easy")
        
        # Classify first
        env.step(SupportAction(action_type="classify", content="billing"))
        
        # Then respond
        obs = env.step(SupportAction(
            action_type="respond",
            content="I understand your concern. Let me help you resolve this billing issue."
        ))
        assert obs is not None
    
    def test_step_escalate_ends_episode(self):
        env = SupportEnvironment()
        env.reset(seed=42, difficulty="hard")
        
        env.step(SupportAction(action_type="classify", content="billing"))
        env.step(SupportAction(
            action_type="respond",
            content="I understand your frustration."
        ))
        obs = env.step(SupportAction(
            action_type="escalate",
            content="Customer requires immediate human assistance."
        ))
        assert obs.done is True
    
    def test_step_resolve_ends_episode(self):
        env = SupportEnvironment()
        env.reset(seed=42, difficulty="easy")
        
        env.step(SupportAction(action_type="classify", content="billing"))
        env.step(SupportAction(
            action_type="respond",
            content="I'll help you fix this billing issue right away."
        ))
        obs = env.step(SupportAction(
            action_type="resolve",
            content="Issue resolved. Billing corrected."
        ))
        assert obs.done is True
    
    def test_max_steps_terminates_episode(self):
        env = SupportEnvironment()
        env.reset(seed=42, difficulty="easy")
        max_steps = 5  # easy task max_steps
        
        for i in range(max_steps + 2):
            obs = env.step(SupportAction(
                action_type="respond",
                content=f"Response {i}"
            ))
            if obs.done:
                break
        
        assert obs.done is True


class TestEnvironmentGrading:
    """Tests for episode grading."""
    
    def test_grade_episode_returns_result(self):
        env = SupportEnvironment()
        env.reset(seed=42, difficulty="easy")
        
        env.step(SupportAction(action_type="classify", content="billing"))
        env.step(SupportAction(
            action_type="respond",
            content="I understand your concern. Here's how to fix this."
        ))
        env.step(SupportAction(
            action_type="resolve",
            content="Issue resolved successfully."
        ))
        
        result = env.grade_episode()
        assert result is not None
        assert 0.0 < result.score < 1.0
        assert isinstance(result.passed, bool)
        assert isinstance(result.breakdown, dict)
    
    def test_grade_score_in_strict_range(self):
        """Ensure scores are strictly within (0, 1) as required by hackathon validation."""
        for diff in ["easy", "medium", "hard"]:
            env = SupportEnvironment()
            env.reset(seed=42, difficulty=diff)
            
            env.step(SupportAction(action_type="classify", content="billing"))
            env.step(SupportAction(
                action_type="respond",
                content="I understand. Let me help you."
            ))
            env.step(SupportAction(
                action_type="resolve",
                content="Resolved."
            ))
            
            result = env.grade_episode()
            assert result.score > 0.0, f"Score must be > 0, got {result.score}"
            assert result.score < 1.0, f"Score must be < 1, got {result.score}"
            
            for key, val in result.breakdown.items():
                assert val > 0.0, f"Breakdown[{key}] must be > 0, got {val}"
                assert val < 1.0, f"Breakdown[{key}] must be < 1, got {val}"
    
    def test_grade_determinism(self):
        """Same episode should produce identical scores."""
        scores = []
        for _ in range(5):
            env = SupportEnvironment()
            env.reset(seed=42, difficulty="medium")
            
            env.step(SupportAction(action_type="classify", content="technical"))
            env.step(SupportAction(
                action_type="respond",
                content="I understand the issue. Please try clearing your cache."
            ))
            env.step(SupportAction(
                action_type="resolve",
                content="Issue resolved after cache clear."
            ))
            
            scores.append(env.grade_episode().score)
        
        assert all(s == scores[0] for s in scores), f"Scores not deterministic: {scores}"
