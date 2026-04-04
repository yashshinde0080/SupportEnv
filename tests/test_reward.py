import pytest
from server.reward import RewardEngine

class TestRewardEngine:
    def test_basic_rewards(self):
        engine = RewardEngine()
        
        # Test classification
        breakdown = engine.compute_reward(
            action_type="classify",
            action_content="billing",
            target_category="billing",
            requires_escalation=False,
            customer_sentiment=0.0,
            step_count=1,
            max_steps=5,
            is_resolved=False,
            task_difficulty="easy"
        )
        assert breakdown.classification_reward > 0
        assert breakdown.total > 0
        
    def test_confidence_calibration(self):
        engine = RewardEngine()
        
        # Confident and right
        breakdown_good = engine.compute_reward(
            action_type="classify",
            action_content="billing",
            target_category="billing",
            requires_escalation=False,
            customer_sentiment=0.0,
            step_count=1,
            max_steps=5,
            is_resolved=False,
            task_difficulty="easy",
            confidence=0.9
        )
        
        # Less confident and right
        breakdown_less = engine.compute_reward(
            action_type="classify",
            action_content="billing",
            target_category="billing",
            requires_escalation=False,
            customer_sentiment=0.0,
            step_count=2,
            max_steps=5,
            is_resolved=False,
            task_difficulty="easy",
            confidence=0.5
        )
        
        # High confidence gets a bonus
        assert breakdown_good.total > breakdown_less.total
        
        # Confident and wrong
        breakdown_wrong = engine.compute_reward(
            action_type="classify",
            action_content="technical",
            target_category="billing",
            requires_escalation=False,
            customer_sentiment=0.0,
            step_count=3,
            max_steps=5,
            is_resolved=False,
            task_difficulty="easy",
            confidence=0.9
        )
        # Should be penalized more for being confident when wrong
        assert breakdown_wrong.total < 0
        assert "Overconfidence penalty" in breakdown_wrong.reason

    def test_kb_lookup(self):
        engine = RewardEngine()
        
        # KB lookup on hard
        breakdown_hard = engine.compute_reward(
            action_type="lookup_kb",
            action_content="test",
            target_category="billing",
            requires_escalation=False,
            customer_sentiment=0.0,
            step_count=1,
            max_steps=5,
            is_resolved=False,
            task_difficulty="hard"
        )
        assert breakdown_hard.total > 0
        
        # KB lookup on easy (unnecessary)
        breakdown_easy = engine.compute_reward(
            action_type="lookup_kb",
            action_content="test",
            target_category="billing",
            requires_escalation=False,
            customer_sentiment=0.0,
            step_count=2,
            max_steps=5,
            is_resolved=False,
            task_difficulty="easy"
        )
        assert breakdown_easy.total < 0
        assert "Unnecessary KB lookup" in breakdown_easy.reason

    def test_sla_breach(self):
        engine = RewardEngine()
        
        # Fast action
        breakdown_fast = engine.compute_reward(
            action_type="request_info",
            action_content="test",
            target_category="billing",
            requires_escalation=False,
            customer_sentiment=0.0,
            step_count=1,
            max_steps=5,
            is_resolved=False,
            task_difficulty="hard"
        )
        assert breakdown_fast.penalty == 0
        
        # SLA breach action
        breakdown_slow = engine.compute_reward(
            action_type="request_info",
            action_content="test",
            target_category="billing",
            requires_escalation=False,
            customer_sentiment=0.0,
            step_count=5, # == max_steps
            max_steps=5,
            is_resolved=False,
            task_difficulty="hard"
        )
        assert "SLA breached" in breakdown_slow.reason
        assert breakdown_slow.penalty <= engine.SLA_BREACH
        # Total should reflect the large penalty
        assert breakdown_slow.total < 0
