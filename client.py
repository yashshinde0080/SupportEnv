"""
Client for SupportEnv - used to connect to deployed environment.
"""

from typing import Dict, Any, Optional
from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult

from models import SupportAction, SupportObservation, SupportState


class SupportEnv(EnvClient[SupportAction, SupportObservation, SupportState]):
    """
    Client for connecting to SupportEnv server.
    
    Usage:
        env = SupportEnv(base_url="https://username-support-env.hf.space")
        with env.sync() as client:
            result = client.reset(difficulty="medium")
            result = client.step(SupportAction(
                action_type="classify",
                content="billing"
            ))
    """
    
    def _step_payload(self, action: SupportAction) -> Dict[str, Any]:
        """Convert action to payload for WebSocket."""
        return {
            "action_type": action.action_type,
            "content": action.content,
            "confidence": action.confidence
        }
    
    def _parse_result(self, payload: Dict[str, Any]) -> StepResult:
        """Parse WebSocket response into StepResult."""
        obs_data = payload.get("observation", {})
        
        observation = SupportObservation(
            done=payload.get("done", False),
            reward=payload.get("reward"),
            ticket_id=obs_data.get("ticket_id", ""),
            ticket_text=obs_data.get("ticket_text", ""),
            ticket_subject=obs_data.get("ticket_subject", ""),
            customer_name=obs_data.get("customer_name", ""),
            interaction_history=obs_data.get("interaction_history", []),
            customer_sentiment=obs_data.get("customer_sentiment", 0.0),
            current_classification=obs_data.get("current_classification"),
            is_classified=obs_data.get("is_classified", False),
            is_escalated=obs_data.get("is_escalated", False),
            task_difficulty=obs_data.get("task_difficulty", "easy"),
            steps_remaining=obs_data.get("steps_remaining", 0),
            max_steps=obs_data.get("max_steps", 10),
            message=obs_data.get("message", ""),
            available_actions=obs_data.get("available_actions", [])
        )
        
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False)
        )
    
    def _parse_state(self, payload: Dict[str, Any]) -> SupportState:
        """Parse state response."""
        return SupportState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            target_category=payload.get("target_category", ""),
            target_resolution=payload.get("target_resolution", ""),
            requires_escalation=payload.get("requires_escalation", False),
            task_id=payload.get("task_id", ""),
            task_difficulty=payload.get("task_difficulty", "easy"),
            max_steps=payload.get("max_steps", 10),
            classification_correct=payload.get("classification_correct", False),
            response_quality_score=payload.get("response_quality_score", 0.0),
            escalation_correct=payload.get("escalation_correct", False),
            resolved=payload.get("resolved", False),
            total_reward=payload.get("total_reward", 0.0)
        )