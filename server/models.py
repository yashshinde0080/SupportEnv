from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class TicketStatus(str, Enum):
    open = "open"
    pending = "pending"
    resolved = "resolved"
    escalated = "escalated"

class TicketObservation(BaseModel):
    id: int
    subject: str
    body: str
    status: TicketStatus

class KBResultObservation(BaseModel):
    articles: List[str] = Field(default_factory=list)

class SupportObservation(BaseModel):
    ticket: TicketObservation
    kb_results: Optional[KBResultObservation] = None
    done: bool = False
    reward: Optional[float] = None

class SupportAction(BaseModel):
    action_type: str = Field(..., description="One of: classify, respond, lookup_kb, escalate, resolve, request_info")
    content: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class Reward(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0)
    info: Optional[str] = None
