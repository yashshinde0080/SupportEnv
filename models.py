"""
Typed models for SupportEnv - Customer Support RL Environment.
These Pydantic models define the strict contract between client and server.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import Field
from openenv.core.env_server import Action, Observation, State


class SupportAction(Action):
    """
    Action that an agent can take in the support environment.
    
    action_type: The type of action to perform
        - "classify": Categorize the ticket (billing, technical, general, account)
        - "respond": Send a response to the customer
        - "escalate": Escalate to human agent
        - "request_info": Ask customer for more information
        - "resolve": Mark ticket as resolved
    
    content: The actual content of the action
        - For classify: the category label
        - For respond: the response text
        - For escalate: reason for escalation
        - For request_info: what information is needed
        - For resolve: resolution summary
    
    confidence: Optional confidence score (0.0-1.0) for the action
    """
    action_type: Literal["classify", "respond", "escalate", "request_info", "resolve"]
    content: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SupportObservation(Observation):
    """
    Observation returned by the environment after each step.
    
    Inherits from Observation base class which provides:
        - done: bool - whether episode is complete
        - reward: Optional[float] - reward for this step
    """
    # Ticket information
    ticket_id: str
    ticket_text: str
    ticket_subject: str
    customer_name: str
    
    # Context
    interaction_history: List[Dict[str, str]] = Field(default_factory=list)
    customer_sentiment: float = Field(ge=-1.0, le=1.0)  # -1 = angry, 0 = neutral, 1 = happy
    
    # Current state
    current_classification: Optional[str] = None
    is_classified: bool = False
    is_escalated: bool = False
    
    # Metadata
    task_difficulty: Literal["easy", "medium", "hard"]
    steps_remaining: int
    max_steps: int
    
    # Feedback
    message: str = ""
    available_actions: List[str] = Field(default_factory=lambda: [
        "classify", "respond", "escalate", "request_info", "resolve"
    ])


class SupportState(State):
    """
    Internal state of the environment (for debugging/monitoring).

    Inherits from State base class which provides:
        - episode_id: Optional[str]
        - step_count: int
    """
    # Target information (hidden from agent in normal operation)
    target_category: str = ""
    target_resolution: str = ""
    requires_escalation: bool = False

    # Episode tracking
    task_id: str = ""
    task_difficulty: str = ""
    max_steps: int = 10

    # Performance tracking
    classification_correct: bool = False
    response_quality_score: float = 0.0
    escalation_correct: bool = False
    resolved: bool = False

    # Cumulative metrics
    total_reward: float = 0.0