"""
Tests for the reward engine.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.reward import RewardEngine


# Common kwargs to reduce test boilerplate
def _base_kwargs(**overrides):
    defaults = {
        "action_type": "classify",
        "action_content": "billing",
        "target_category": "billing",
        "requires_escalation": False,
        "customer_sentiment": 0.0,
        "step_count": 1,
        "max_steps": 5,
        "is_resolved": False,
        "task_difficulty": "easy",
        "target_resolution": "",
        "confidence": None,
    }
    defaults.update(overrides)
    return defaults


class TestRewardConfidence:
    """Tests for confidence adjustment."""
    
    def setup_method(self):
        self.engine = RewardEngine()
    
    def test_confidence_bonus_applied(self):
        """High confidence on a positive-reward action should add a bonus."""
        self.engine.reset()
        breakdown_high = self.engine.compute_reward(**_base_kwargs(confidence=0.95))
        
        self.engine.reset()
        breakdown_low = self.engine.compute_reward(**_base_kwargs(confidence=0.5))
        
        # High confidence on correct classification should yield >= low confidence
        assert breakdown_high.total >= breakdown_low.total
    
    def test_confidence_not_discarded(self):
        """Verify that confidence actually affects the total (bug L1 regression test)."""
        self.engine.reset()
        breakdown_with = self.engine.compute_reward(**_base_kwargs(confidence=0.99))
        
        self.engine.reset()
        breakdown_without = self.engine.compute_reward(**_base_kwargs(confidence=None))
        
        # With high confidence on correct action, total should differ
        assert breakdown_with.total != breakdown_without.total


class TestRewardRepeatedAction:
    """Tests for repeated action penalty."""
    
    def setup_method(self):
        self.engine = RewardEngine()
    
    def test_repeated_action_penalized(self):
        self.engine.reset()
        # Simulate previous respond actions
        self.engine.action_history = ["respond", "respond"]
        
        breakdown = self.engine.compute_reward(**_base_kwargs(
            action_type="respond",
            action_content="I can help you.",
            step_count=3,
        ))
        # The repeated-action penalty shows up in response_reward for 'respond' type, as -0.1
        assert breakdown.response_reward < 0 or breakdown.penalty < 0


class TestRewardInfoRequest:
    """Tests for request_info reward threshold."""
    
    def setup_method(self):
        self.engine = RewardEngine()
    
    def test_early_info_request_rewarded_for_hard(self):
        self.engine.reset()
        breakdown = self.engine.compute_reward(**_base_kwargs(
            action_type="request_info",
            action_content="Can you provide more details?",
            step_count=2,
            max_steps=12,
            task_difficulty="hard",
        ))
        assert breakdown.response_reward > 0
    
    def test_late_info_request_penalized(self):
        self.engine.reset()
        breakdown = self.engine.compute_reward(**_base_kwargs(
            action_type="request_info",
            action_content="Can you provide more details?",
            step_count=10,
            max_steps=12,
            task_difficulty="hard",
        ))
        assert breakdown.penalty < 0
    
    def test_mid_episode_info_request_allowed_for_hard(self):
        """Step 3 out of 12 should still be rewarded for hard tasks (40% threshold = step 4)."""
        self.engine.reset()
        breakdown = self.engine.compute_reward(**_base_kwargs(
            action_type="request_info",
            action_content="Can you provide more details?",
            step_count=3,
            max_steps=12,
            task_difficulty="hard",
        ))
        assert breakdown.response_reward > 0


class TestRewardBounds:
    """Tests for reward clamping."""
    
    def setup_method(self):
        self.engine = RewardEngine()
    
    def test_total_clamped(self):
        self.engine.reset()
        breakdown = self.engine.compute_reward(**_base_kwargs())
        assert -1.0 <= breakdown.total <= 1.0
