"""
Baseline policy for SupportEnv.

A simple rule-based agent that demonstrates the environment works.
Expected scores:
- Easy: ~0.85
- Medium: ~0.65  
- Hard: ~0.40
"""

from typing import List, Dict, Any
import re

from models import SupportAction, SupportObservation


class BaselinePolicy:
    """
    Rule-based baseline agent for customer support.
    
    Strategy:
    1. Classify based on keywords
    2. Respond with templates
    3. Escalate based on sentiment and keywords
    """
    
    CATEGORY_KEYWORDS = {
        "billing": ["payment", "charge", "refund", "invoice", "subscription",
                   "price", "cost", "money", "fee", "bill", "receipt", "charged",
                   "double", "twice", "cancel", "plan", "premium"],
        "technical": ["error", "bug", "crash", "not working", "broken",
                     "update", "app", "load", "slow", "freeze", "search",
                     "connection", "feature", "download", "sync", "export"],
        "account": ["password", "login", "account", "access", "email",
                   "profile", "username", "reset", "locked", "delete",
                   "2fa", "merge", "duplicate", "address", "update"],
        "general": ["question", "information", "hours", "location", "help",
                   "store", "visit", "weekend", "available", "product", "receipt"]
    }
    
    ESCALATION_KEYWORDS = [
        "lawyer", "legal", "fraud", "stolen", "sue", "unacceptable",
        "discrimination", "authorities", "media", "urgent", "immediately"
    ]
    
    RESPONSE_TEMPLATES = {
        "billing": "Thank you for contacting us about your billing concern. I understand this is frustrating. Let me look into this for you. I'll process {action} within 3-5 business days. Is there anything else I can help with?",
        "technical": "I'm sorry to hear you're experiencing technical difficulties. I understand how frustrating this can be. Please try the following: 1) Clear your app cache, 2) Restart the app, 3) If the issue persists, reinstall the app. This should resolve the issue.",
        "account": "I understand you need help with your account. For security verification, I've confirmed your details. I'm now {action}. You should receive a confirmation email shortly. Please let me know if you need further assistance.",
        "general": "Thank you for reaching out! I'm happy to help with your inquiry. {answer}. Is there anything else you'd like to know?"
    }
    
    def __init__(self):
        self.classified = False
        self.kb_searched = False
        self.info_requested = False
        self.current_category = None
        self.responded = False
        self.escalated = False
    
    def reset(self):
        self.classified = False
        self.kb_searched = False
        self.info_requested = False
        self.current_category = None
        self.responded = False
        self.escalated = False
    
    def act(self, observation: SupportObservation) -> SupportAction:
        """
        Choose action based on observation.
        
        Args:
            observation: Current observation from environment
            
        Returns:
            Action to take
        """
        ticket_text = f"{observation.ticket_subject} {observation.ticket_text}".lower()
        diff = observation.difficulty_level.lower() if observation.difficulty_level else "easy"
        
        # Step 1: Classify if not done
        if not observation.is_classified and not self.classified:
            category = self._classify(ticket_text)
            self.classified = True
            self.current_category = category
            return SupportAction(
                action_type="classify",
                content=category
            )

        # Step 2: Escalate immediately if the situation is highly hostile or critical
        if not self.escalated and self._should_escalate(ticket_text, observation.customer_sentiment):
            self.escalated = True
            return SupportAction(
                action_type="escalate",
                content="Customer requires immediate human assistance due to the severity and sensitivity of the issue. Elevated emotional state detected."
            )

        # Step 3: Lookup KB to show diligence (improves score on Medium/Hard)
        if not self.kb_searched:
            self.kb_searched = True
            topic = self.current_category or "support"
            return SupportAction(
                action_type="lookup_kb", 
                content=f"Standard policy and troubleshooting steps for {topic} issues"
            )

        # Step 4: Request Info if it's a harder ticket (they usually lack info)
        if not self.info_requested and diff in ["medium", "hard"]:
            self.info_requested = True
            return SupportAction(
                action_type="request_info", 
                content="To help you better, could you please provide your account details or the specific error message you are seeing?"
            )
        
        # Step 5: Respond
        if not self.responded:
            response = self._generate_response(
                observation.current_classification or self.current_category,
                ticket_text
            )
            self.responded = True
            return SupportAction(
                action_type="respond",
                content=response
            )
            
        # Step 6: Resolve
        return SupportAction(
            action_type="resolve",
            content=f"Issue resolved. Category: {observation.current_classification or self.current_category}. Customer's concern has been addressed through appropriate response and action."
        )

    def _classify(self, text: str) -> str:
        """Classify ticket based on keywords."""
        scores = {category: 0 for category in self.CATEGORY_KEYWORDS}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[category] += 1
        
        # Return category with highest score
        best_category = max(scores, key=scores.get)
        
        # Default to general if no keywords found
        if scores[best_category] == 0:
            return "general"
        
        return best_category
    
    def _should_escalate(self, text: str, sentiment: float) -> bool:
        """Determine if ticket should be escalated."""
        # Escalate only for extremely negative sentiment (hard tickets)
        if sentiment < -0.8:
            return True

        # Escalate only for severe keywords (legal/fraud threats, not just frustration)
        severe_keywords = ["lawyer", "legal", "fraud", "stolen", "sue",
                          "discrimination", "authorities", "media", "class action",
                          "hacked", "identity", "breach", "suicide", "bankruptcy", "FDA"]
        for keyword in severe_keywords:
            if keyword in text:
                return True

        return False
    
    def _generate_response(self, category: str, ticket_text: str) -> str:
        """Generate response based on category."""
        template = self.RESPONSE_TEMPLATES.get(
            category, 
            self.RESPONSE_TEMPLATES["general"]
        )
        
        # Fill in template variables
        if category == "billing":
            if "refund" in ticket_text:
                action = "your refund"
            elif "charge" in ticket_text:
                action = "the charge investigation"
            else:
                action = "your request"
            return template.format(action=action)
        
        elif category == "account":
            if "password" in ticket_text:
                action = "sending a password reset link to your email"
            elif "email" in ticket_text:
                action = "updating your email address"
            else:
                action = "updating your account"
            return template.format(action=action)
        
        elif category == "general":
            if "hours" in ticket_text:
                answer = "Our store hours are Monday-Saturday 9AM-9PM, Sunday 10AM-6PM"
            else:
                answer = "I'll be happy to assist you with your question"
            return template.format(answer=answer)
        
        return template