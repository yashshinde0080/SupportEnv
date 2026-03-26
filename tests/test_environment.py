"""
Unit tests for SupportEnv environment.
"""

import pytest
from server.environment import SupportEnvironment
from models import SupportAction, SupportObservation, SupportState


class TestEnvironmentBasics:
    """Test basic environment functionality."""
    
    def test_reset_returns_observation(self):
        """reset() should return valid observation."""
        env = SupportEnvironment()
        obs = env.reset(seed=42, difficulty="easy")
        
        assert isinstance(obs, SupportObservation)
        assert obs.done is False
        assert obs.reward is None
        assert len(obs.ticket_text) > 0
        assert obs.steps_remaining > 0
    
    def test_reset_with_seed_is_reproducible(self):
        """Same seed should produce same ticket."""
        env1 = SupportEnvironment()
        obs1 = env1.reset(seed=42, difficulty="easy")
        
        env2 = SupportEnvironment()
        obs2 = env2.reset(seed=42, difficulty="easy")
        
        assert obs1.ticket_text == obs2.ticket_text
        assert obs1.ticket_subject == obs2.ticket_subject
    
    def test_step_updates_state(self):
        """step() should update internal state."""
        env = SupportEnvironment()
        env.reset(seed=42, difficulty="easy")
        
        action = SupportAction(action_type="classify", content="billing")
        obs = env.step(action)
        
        assert env.state.step_count == 1
        assert obs.is_classified is True
    
    def test_step_returns_reward(self):
        """step() should return numeric reward."""
        env = SupportEnvironment()
        env.reset(seed=42, difficulty="easy")
        
        action = SupportAction(action_type="classify", content="billing")
        obs = env.step(action)
        
        assert obs.reward is not None
        assert isinstance(obs.reward, float)
    
    def test_episode_terminates(self):
        """Episode should terminate after resolve/escalate."""
        env = SupportEnvironment()
        env.reset(seed=42, difficulty="easy")
        
        # Classify
        env.step(SupportAction(action_type="classify", content="billing"))
        
        # Respond
        env.step(SupportAction(action_type="respond", content="I'll help you."))
        
        # Resolve
        obs = env.step(SupportAction(action_type="resolve", content="Issue resolved."))
        
        assert obs.done is True
    
    def test_max_steps_terminates(self):
        """Episode should terminate at max steps."""
        env = SupportEnvironment()
        obs = env.reset(seed=42, difficulty="easy")
        max_steps = obs.max_steps
        
        for i in range(max_steps + 1):
            if obs.done:
                break
            obs = env.step(SupportAction(
                action_type="request_info",
                content=f"Request {i}"
            ))
        
        assert obs.done is True


class TestDifficultyLevels:
    """Test different difficulty levels."""
    
    @pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
    def test_difficulty_returns_observation(self, difficulty):
        """All difficulties should work."""
        env = SupportEnvironment()
        obs = env.reset(seed=42, difficulty=difficulty)
        
        assert obs.task_difficulty == difficulty
        assert len(obs.ticket_text) > 0
    
    def test_hard_tasks_require_escalation(self):
        """Hard tasks often require escalation."""
        escalation_count = 0
        
        for seed in range(10):
            env = SupportEnvironment()
            env.reset(seed=seed, difficulty="hard")
            if env.state.requires_escalation:
                escalation_count += 1
        
        # At least some hard tasks should require escalation
        assert escalation_count > 0


class TestStateManagement:
    """Test state management."""
    
    def test_state_property(self):
        """state property should return SupportState."""
        env = SupportEnvironment()
        env.reset(seed=42)
        
        state = env.state
        
        assert isinstance(state, SupportState)
        assert state.episode_id is not None
        assert state.step_count == 0
    
    def test_state_tracks_classification(self):
        """State should track classification correctness."""
        env = SupportEnvironment()
        env.reset(seed=42, difficulty="easy")
        
        # Get target category
        target = env.state.target_category
        
        # Classify correctly
        env.step(SupportAction(action_type="classify", content=target))
        
        assert env.state.classification_correct is True
    
    def test_episode_data(self):
        """get_episode_data should return complete data."""
        env = SupportEnvironment()
        env.reset(seed=42)
        
        env.step(SupportAction(action_type="classify", content="billing"))
        
        data = env.get_episode_data()
        
        assert "action_history" in data
        assert "target_category" in data
        assert len(data["action_history"]) == 1


class TestActions:
    """Test different action types."""
    
    def test_classify_action(self):
        """Classify action should update classification."""
        env = SupportEnvironment()
        env.reset(seed=42)
        
        obs = env.step(SupportAction(action_type="classify", content="billing"))
        
        assert obs.is_classified is True
        assert obs.current_classification == "billing"
    
    def test_respond_action(self):
        """Respond action should add to history."""
        env = SupportEnvironment()
        env.reset(seed=42)
        
        env.step(SupportAction(action_type="classify", content="billing"))
        obs = env.step(SupportAction(
            action_type="respond",
            content="Thank you for contacting us."
        ))
        
        assert len(obs.interaction_history) >= 1
    
    def test_escalate_action(self):
        """Escalate action should terminate episode."""
        env = SupportEnvironment()
        env.reset(seed=42)
        
        obs = env.step(SupportAction(
            action_type="escalate",
            content="Customer requires immediate attention."
        ))
        
        assert obs.done is True
        assert obs.is_escalated is True
    
    def test_resolve_action(self):
        """Resolve action should terminate episode."""
        env = SupportEnvironment()
        env.reset(seed=42)
        
        env.step(SupportAction(action_type="classify", content="billing"))
        env.step(SupportAction(action_type="respond", content="Here's help."))
        obs = env.step(SupportAction(action_type="resolve", content="Resolved."))
        
        assert obs.done is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])