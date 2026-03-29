import pytest
from baseline.policy import BaselinePolicy
from models import SupportAction, SupportObservation
from server.environment import SupportEnvironment

def test_baseline_policy():
    policy = BaselinePolicy()
    
    # Check simple reset semantics
    policy.reset()
    assert policy.classified is False
    assert policy.current_category is None
    
    # Create simple mock observation
    obs = SupportObservation(
        ticket_id="T1",
        ticket_text="How do I reset my password?",
        ticket_subject="Password reset",
        customer_name="Test User",
        interaction_history=[],
        customer_sentiment=0.5,
        current_classification=None,
        is_classified=False,
        is_escalated=False,
        task_difficulty="easy",
        steps_remaining=5,
        max_steps=5,
        message="",
        available_actions=["classify"]
    )
    
    # Baseline should typically classify first
    action = policy.act(obs)
    assert isinstance(action, SupportAction)
    assert action.action_type in ["classify", "respond", "request_info", "escalate", "resolve"]

def test_evaluate_baseline_integration():
    policy = BaselinePolicy()
    env = SupportEnvironment()
    
    for difficulty in ["easy"]:
        obs = env.reset(difficulty=difficulty, seed=42)
        policy.reset()
        
        while not obs.done:
            action = policy.act(obs)
            obs = env.step(action)
            
        assert obs.done is True
        result = env.grade_episode()
        assert result.score >= 0.0
