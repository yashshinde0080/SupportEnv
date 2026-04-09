import re
import random
from typing import List, Dict, Any, Optional

from models import SupportAction, SupportObservation


class BaselinePolicy:
    """
    Rule-based baseline agent for customer support with diversified behaviors.
    
    Strategy:
    1. Classify based on expanded keywords
    2. Respond with randomized templates
    3. Escalate based on sentiment and critical keywords
    4. Vary intermediate actions (KB lookup, info gathering)
    """
    
    CATEGORY_KEYWORDS = {
        "billing": ["payment", "charge", "refund", "invoice", "subscription",
                   "price", "cost", "money", "fee", "bill", "receipt", "charged",
                   "double", "twice", "cancel", "plan", "premium", "card", "bank",
                   "transaction", "overcharged", "statement", "autopay"],
        "technical": ["error", "bug", "crash", "not working", "broken",
                     "update", "app", "load", "slow", "freeze", "search",
                     "connection", "feature", "download", "sync", "export",
                     "login issue", "failed to", "invalid", "glitch", "performance"],
        "account": ["password", "login", "account", "access", "email",
                   "profile", "username", "reset", "locked", "delete",
                   "2fa", "merge", "duplicate", "address", "update", "security",
                   "verification", "permissions", "credentials", "sign in"],
        "general": ["question", "information", "hours", "location", "help",
                   "store", "visit", "weekend", "available", "product", "receipt",
                   "policy", "shipping", "return", "contact", "support"]
    }
    
    RESPONSE_TEMPLATES = {
        "billing": [
            "Thank you for contacting us about your billing concern regarding {action}. I understand this is frustrating, and I'm here to help. I'll process this within 3-5 business days. Is there anything else I can assist with?",
            "I've received your billing inquiry about {action}. I apologize for any frustration this has caused. I'm investigating the details right now to ensure everything is correct.",
            "I understand you have a question about {action}. I'm reviewing your billing history and will get this sorted out for you immediately."
        ],
        "technical": [
            "I'm sorry to hear you're experiencing technical difficulties with {action}. I know how disruptive that can be. Please try clearing your cache and restarting the application; that often resolves {action}.",
            "It sounds like you've encountered a technical issue related to {action}. I'm looking into our system logs now. In the meantime, could you try accessing the service from a different browser?",
            "I apologize for the technical trouble you're having with {action}. I've logged this with our engineering team for a closer look while I check for immediate workarounds."
        ],
        "account": [
            "I understand you need help with your account security for {action}. For your protection, I've confirmed your details and am now {action}. You should receive a confirmation shortly.",
            "Your account access regarding {action} is important to us. I'm currently {action} as requested. Please let me know if you need anything else to manage your profile.",
            "I've processed your request to {action}. Security is our top priority, so please check your registered email for a verification link to finalize the {action} process."
        ],
        "general": [
            "Thank you for reaching out! I'm happy to help with your inquiry. {answer}. Does that provide the information you were looking for?",
            "Great question! {answer}. We always aim to provide clear information, so please let me know if I can elaborate on any part of that.",
            "I appreciate you asking about that. {answer}. Is there anything else you'd like to know about our services or policies?"
        ]
    }
    
    ESCALATION_MESSAGES = [
        "Customer requires immediate human assistance due to the severity and sensitivity of the issue. Elevated emotional state detected.",
        "Case involves complex or sensitive matters that exceed automated handling capabilities. Escalating for specialist review.",
        "Detected critical keywords or high frustration levels. Transferring this session to a senior support representative for immediate resolution."
    ]
    
    KB_QUERIES = [
        "Standard policy and troubleshooting steps for {topic} issues",
        "How to resolve common {topic} complaints and technical errors",
        "Knowledge base article on {topic} procedures and customer guidelines",
        "Internal documentation for handling {topic} escalation and resolution"
    ]
    
    INFO_REQUESTS = [
        "To help you better, could you please provide your account details or the specific error message you are seeing?",
        "Could you clarify a few more details? Specifically, when did this issue first occur and what device are you using?",
        "I need a bit more information to proceed. Could you please share the order ID or the email address associated with your account?"
    ]

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed) if seed is not None else random.Random()
        self.reset()
    
    def reset(self, seed: Optional[int] = None):
        if seed is not None:
            self.rng = random.Random(seed)
        self.classified = False
        self.kb_searched = False
        self.info_requested = False
        self.current_category = None
        self.responded = False
        self.escalated = False
        self.step_count = 0
    
    def act(self, observation: SupportObservation) -> SupportAction:
        """
        Choose action based on observation with randomized variety.
        """
        self.step_count += 1
        ticket_text = f"{observation.ticket_subject} {observation.ticket_text}".lower()
        diff = observation.task_difficulty.lower() if observation.task_difficulty else "easy"
        
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
                content=self.rng.choice(self.ESCALATION_MESSAGES)
            )

        # Step 3: Vary between KB lookup and Request Info
        if not self.kb_searched and (self.rng.random() > 0.5 or diff == "easy"):
            self.kb_searched = True
            topic = self.current_category or "general support"
            query_template = self.rng.choice(self.KB_QUERIES)
            return SupportAction(
                action_type="lookup_kb", 
                content=query_template.format(topic=topic)
            )

        # Step 4: Request Info (prio for medium/hard, or random chance)
        if not self.info_requested and (diff in ["medium", "hard"] or self.rng.random() > 0.7):
            self.info_requested = True
            return SupportAction(
                action_type="request_info", 
                content=self.rng.choice(self.INFO_REQUESTS)
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
                content=response,
                confidence=0.85 + self.rng.random() * 0.1
            )
            
        # Step 6: Resolve
        res_message = self.rng.choice([
            "Issue resolved. Category: {cat}. Customer's concern has been addressed through appropriate response and action.",
            "I've successfully addressed the reported issue for the {cat} category. Marking this ticket as resolved.",
            "Thank you for your patience. I have finalized the resolution steps for this {cat} case."
        ]).format(cat=observation.current_classification or self.current_category)

        return SupportAction(
            action_type="resolve",
            content=res_message
        )

    def _classify(self, text: str) -> str:
        """Classify ticket based on keywords with a bit of multi-hit weighting."""
        scores = {category: 0 for category in self.CATEGORY_KEYWORDS}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                # Use word boundaries for better accuracy
                if re.search(rf'\b{re.escape(keyword)}\b', text):
                    scores[category] += 2  # Strong hit
                elif keyword in text:
                    scores[category] += 1  # Weak hit
        
        # Determine hits
        max_score = max(scores.values())
        if max_score == 0:
            return "general"
            
        candidates = [cat for cat, score in scores.items() if score == max_score]
        return self.rng.choice(candidates)
    
    def _should_escalate(self, text: str, sentiment: float) -> bool:
        """Determine if ticket should be escalated."""
        # Escalate for extremely negative sentiment
        if sentiment < -0.75:
            return True

        # Critical escalation keywords
        severe_keywords = ["lawyer", "legal", "fraud", "stolen", "sue",
                          "discrimination", "authorities", "media", "class action",
                          "hacked", "identity", "breach", "suicide", "bankruptcy", "fda",
                          "malfunction", "critical failure"]
        for keyword in severe_keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', text):
                return True

        return False
    
    def _generate_response(self, category: str, ticket_text: str) -> str:
        """Generate diversified response based on category."""
        templates = self.RESPONSE_TEMPLATES.get(
            category, 
            self.RESPONSE_TEMPLATES["general"]
        )
        template = self.rng.choice(templates)
        
        # Fill in template variables
        if category == "billing":
            if "refund" in ticket_text:
                action = "your refund request"
            elif "charge" in ticket_text or "overcharg" in ticket_text:
                action = "the transaction discrepancy"
            elif "invoice" in ticket_text:
                action = "the invoice details"
            else:
                action = "your account billing status"
            return template.format(action=action)
        
        elif category == "technical":
            if "app" in ticket_text:
                action = "the application error"
            elif "crash" in ticket_text or "freeze" in ticket_text:
                action = "the system instability"
            elif "slow" in ticket_text or "load" in ticket_text:
                action = "the performance delay"
            else:
                action = "the technical issue"
            return template.format(action=action)
        
        elif category == "account":
            if "password" in ticket_text:
                action = "updating your password"
            elif "email" in ticket_text:
                action = "syncing your email account"
            elif "delete" in ticket_text:
                action = "processing your account deletion request"
            else:
                action = "modifying your profile settings"
            return template.format(action=action)
        
        elif category == "general":
            if "hours" in ticket_text:
                answer = "our standard hours are 9 AM to 9 PM daily"
            elif "location" in ticket_text or "where" in ticket_text:
                answer = "we are located at several convenient spots in the city center"
            elif "shipping" in ticket_text or "return" in ticket_text:
                answer = "our return policy allows for exchanges within 30 days"
            else:
                answer = "I'm looking into the most accurate information for your specific query"
            return template.format(answer=answer)
        
        return template