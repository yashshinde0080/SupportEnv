"""
Core environment logic for SupportEnv.

Implements the OpenEnv interface:
- reset() -> Observation
- step(action) -> Observation
- state -> State
"""

import uuid
import random
from typing import Optional, Dict, Any, List

from openenv.core.env_server import Environment

from models import SupportAction, SupportObservation, SupportState
from server.ticket_generator import TicketGenerator, TASK_DEFINITIONS
from server.reward import RewardEngine, RewardBreakdown
from server.graders import SupportGrader, GradeResult


class SupportEnvironment(Environment):
    """
    Customer Support RL Environment.
    
    Simulates a customer support workflow where agents:
    1. Receive support tickets
    2. Classify issues
    3. Respond to customers
    4. Decide whether to escalate
    5. Resolve issues
    
    Supports concurrent sessions via SUPPORTS_CONCURRENT_SESSIONS = True
    """
    
    SUPPORTS_CONCURRENT_SESSIONS = True
    
    def __init__(self):
        """Initialize environment."""
        self._state = SupportState()
        self._ticket_generator = TicketGenerator()
        self._reward_engine = RewardEngine()
        self._grader = SupportGrader()
        self._rng = random.Random()
        
        # Current episode data
        self._current_ticket: Dict[str, Any] = {}
        self._action_history: List[Dict[str, Any]] = []
        self._interaction_history: List[Dict[str, str]] = []
        
        # Episode flags
        self._is_classified = False
        self._is_escalated = False
        self._is_resolved = False
        self._current_classification: Optional[str] = None
    
    def reset(
        self, 
        seed: int = None, 
        episode_id: str = None,
        task_id: str = None,
        difficulty: str = None,
        **kwargs
    ) -> SupportObservation:
        """
        Reset environment for new episode.
        
        Args:
            seed: Random seed for reproducibility
            episode_id: Optional episode identifier
            task_id: Optional specific task to use
            difficulty: Optional difficulty level (easy/medium/hard)
            
        Returns:
            Initial observation
        """
        # Set seed for reproducibility
        if seed is not None:
            self._rng = random.Random(seed)
            self._ticket_generator = TicketGenerator(seed=seed)
        
        # Reset reward engine
        self._reward_engine.reset()
        
        # Determine difficulty
        if difficulty is None:
            difficulty = self._rng.choice(["easy", "medium", "hard"])
        
        # Generate ticket
        self._current_ticket = self._ticket_generator.generate_ticket(
            difficulty=difficulty,
            task_id=task_id
        )
        
        # Get task config
        task_config = TASK_DEFINITIONS.get(difficulty, TASK_DEFINITIONS["easy"])
        max_steps = task_config["max_steps"]
        
        # Initialize state
        self._state = SupportState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            target_category=self._current_ticket["category"],
            target_resolution=self._current_ticket["expected_resolution"],
            requires_escalation=self._current_ticket["requires_escalation"],
            task_id=self._current_ticket["task_id"],
            task_difficulty=difficulty,
            max_steps=max_steps,
            classification_correct=False,
            response_quality_score=0.0,
            escalation_correct=False,
            resolved=False,
            total_reward=0.0
        )
        
        # Reset episode flags
        self._action_history = []
        self._interaction_history = []
        self._is_classified = False
        self._is_escalated = False
        self._is_resolved = False
        self._current_classification = None
        
        # Return initial observation
        return SupportObservation(
            done=False,
            reward=None,
            ticket_id=self._current_ticket["ticket_id"],
            ticket_text=self._current_ticket["body"],
            ticket_subject=self._current_ticket["subject"],
            customer_name=self._current_ticket["customer_name"],
            interaction_history=[],
            customer_sentiment=self._current_ticket["sentiment"],
            current_classification=None,
            is_classified=False,
            is_escalated=False,
            task_difficulty=difficulty,
            steps_remaining=max_steps,
            max_steps=max_steps,
            message=f"New support ticket received. Customer: {self._current_ticket['customer_name']}. Subject: {self._current_ticket['subject']}",
            available_actions=["classify", "respond", "escalate", "request_info", "resolve"]
        )
    
    def step(
        self, 
        action: SupportAction,
        timeout_s: float = None,
        **kwargs
    ) -> SupportObservation:
        """
        Execute action and return new observation.
        
        Args:
            action: SupportAction to execute
            timeout_s: Optional timeout (unused)
            
        Returns:
            New observation with reward and done flag
        """
        # Increment step count
        self._state.step_count += 1
        
        # Record action
        action_record = {
            "type": action.action_type,
            "content": action.content,
            "step": self._state.step_count
        }
        self._action_history.append(action_record)
        
        # Process action
        message = self._process_action(action)
        
        # Compute reward
        reward_breakdown = self._reward_engine.compute_reward(
            action_type=action.action_type,
            action_content=action.content,
            target_category=self._state.target_category,
            requires_escalation=self._state.requires_escalation,
            customer_sentiment=self._current_ticket["sentiment"],
            step_count=self._state.step_count,
            max_steps=self._state.max_steps,
            is_resolved=self._is_resolved,
            task_difficulty=self._state.task_difficulty
        )
        
        reward = reward_breakdown.total
        self._state.total_reward += reward
        
        # Check termination
        done = self._check_done()
        
        # Add final reward if done
        if done:
            final_reward = self._reward_engine.compute_episode_final_reward(
                is_resolved=self._is_resolved,
                classification_correct=self._state.classification_correct,
                escalation_correct=self._state.escalation_correct,
                total_steps=self._state.step_count,
                max_steps=self._state.max_steps
            )
            reward += final_reward
            self._state.total_reward += final_reward
            message += f" Episode complete. Total reward: {self._state.total_reward:.2f}"
        
        # Calculate steps remaining
        steps_remaining = max(0, self._state.max_steps - self._state.step_count)
        
        return SupportObservation(
            done=done,
            reward=reward,
            ticket_id=self._current_ticket["ticket_id"],
            ticket_text=self._current_ticket["body"],
            ticket_subject=self._current_ticket["subject"],
            customer_name=self._current_ticket["customer_name"],
            interaction_history=self._interaction_history.copy(),
            customer_sentiment=self._current_ticket["sentiment"],
            current_classification=self._current_classification,
            is_classified=self._is_classified,
            is_escalated=self._is_escalated,
            task_difficulty=self._state.task_difficulty,
            steps_remaining=steps_remaining,
            max_steps=self._state.max_steps,
            message=message,
            available_actions=self._get_available_actions()
        )
    
    @property
    def state(self) -> SupportState:
        """Return current state."""
        return self._state
    
    def _process_action(self, action: SupportAction) -> str:
        """
        Process action and update internal state.
        
        Returns:
            Message describing action result
        """
        action_type = action.action_type
        content = action.content
        
        if action_type == "classify":
            return self._handle_classify(content)
        elif action_type == "respond":
            return self._handle_respond(content)
        elif action_type == "escalate":
            return self._handle_escalate(content)
        elif action_type == "request_info":
            return self._handle_request_info(content)
        elif action_type == "resolve":
            return self._handle_resolve(content)
        else:
            return f"Unknown action type: {action_type}"
    
    def _handle_classify(self, category: str) -> str:
        """Handle classification action."""
        self._is_classified = True
        self._current_classification = category.lower().strip()
        
        # Check if correct
        if self._current_classification == self._state.target_category:
            self._state.classification_correct = True
            return f"Ticket classified as '{category}'. Classification correct."
        else:
            return f"Ticket classified as '{category}'."
    
    def _handle_respond(self, response: str) -> str:
        """Handle response action."""
        # Add to interaction history
        self._interaction_history.append({
            "role": "agent",
            "content": response
        })
        
        customer_reply = self._generate_customer_reply(response)
        
        self._interaction_history.append({
            "role": "customer",
            "content": customer_reply
        })
        
        return f"Response sent to customer. Customer replied: '{customer_reply}'"
        
    def _generate_customer_reply(self, response: str) -> str:
        """Dynamic customer reply based on ticket sentiment, personality, and agent response."""
        sentiment = self._current_ticket["sentiment"]
        personality = self._current_ticket.get("personality", "neutral")
        
        response_lower = response.lower()
        has_empathy = any(kw in response_lower for kw in ["understand", "sorry", "apologize", "help", "thank"])
        has_solution = any(kw in response_lower for kw in ["here's", "you can", "resolved", "fixed", "processed", "please try"])
        
        if has_empathy and has_solution:
            sentiment += 0.3
        elif has_empathy:
            sentiment += 0.1
        elif not has_solution:
            sentiment -= 0.2
            
        self._current_ticket["sentiment"] = max(-1.0, min(1.0, sentiment))
        
        if sentiment < -0.5:
            if personality == "aggressive":
                return "This is unacceptable. I need a real solution IMMEDIATELY or I'm escalating this."
            elif personality == "anxious":
                return "I'm panicking! I really need this fixed, what's taking so long?"
            return "I am still very unhappy with this. Please fix it now."
        elif sentiment < 0:
            if personality == "anxious":
                return "Oh no, I'm really worried this won't get fixed. Are you sure?"
            return "Okay, I'm waiting for the resolution. Please hurry."
        elif sentiment < 0.5:
            return "Okay, I understand. Let's see if this works."
        else:
            if personality == "friendly":
                return "Oh perfect! Thank you so much for your wonderful help!"
            return "Thank you for your help. That resolves my issue."
    
    def _handle_escalate(self, reason: str) -> str:
        """Handle escalation action."""
        self._is_escalated = True
        
        # Check if escalation was correct
        if self._state.requires_escalation:
            self._state.escalation_correct = True
            self._is_resolved = True  # Escalation counts as resolution
            return f"Ticket escalated to human agent. Reason: {reason}. Escalation was appropriate."
        else:
            return f"Ticket escalated to human agent. Reason: {reason}. Note: This ticket may not have required escalation."
    
    def _handle_request_info(self, info_needed: str) -> str:
        """Handle request for information."""
        self._interaction_history.append({
            "role": "agent",
            "content": f"Could you please provide: {info_needed}"
        })
        
        # Simulate customer providing info
        self._interaction_history.append({
            "role": "customer",
            "content": f"Here is the information you requested about {info_needed}."
        })
        
        return f"Requested additional information: {info_needed}. Customer provided response."
    
    def _handle_resolve(self, summary: str) -> str:
        """Handle resolution action."""
        self._is_resolved = True
        self._state.resolved = True
        
        self._interaction_history.append({
            "role": "agent",
            "content": f"Resolution: {summary}"
        })
        
        return f"Ticket marked as resolved. Summary: {summary}"
    
    def _check_done(self) -> bool:
        """Check if episode should end."""
        # Done if resolved
        if self._is_resolved:
            return True
        
        # Done if escalated
        if self._is_escalated:
            return True
        
        # Done if max steps reached
        if self._state.step_count >= self._state.max_steps:
            return True
        
        return False
    
    def _get_available_actions(self) -> List[str]:
        """Get currently available actions."""
        actions = ["respond", "request_info"]
        
        if not self._is_classified:
            actions.insert(0, "classify")
        
        if not self._is_escalated:
            actions.append("escalate")
        
        if self._is_classified and len(self._interaction_history) >= 2:
            actions.append("resolve")
        
        return actions
    
    def get_episode_data(self) -> Dict[str, Any]:
        """Get complete episode data for grading."""
        return {
            "action_history": self._action_history,
            "target_category": self._state.target_category,
            "requires_escalation": self._state.requires_escalation,
            "expected_resolution": self._state.target_resolution,
            "task_difficulty": self._state.task_difficulty,
            "is_resolved": self._is_resolved,
            "total_steps": self._state.step_count,
            "max_steps": self._state.max_steps
        }
    
    def grade_episode(self) -> GradeResult:
        """Grade the current episode."""
        episode_data = self.get_episode_data()
        return self._grader.grade_episode(**episode_data)