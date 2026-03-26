"""
Generates realistic customer support tickets for training.
"""

import random
import uuid
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass


@dataclass
class TicketTemplate:
    category: str
    subject: str
    body: str
    sentiment: float  # -1 to 1
    expected_resolution: str
    requires_escalation: bool
    difficulty: str
    keywords: List[str]


# Easy tickets - clear category, simple resolution
EASY_TICKETS = [
    TicketTemplate(
        category="billing",
        subject="Password Reset Request",
        body="Hi, I forgot my password and can't log into my account. My email is {email}. Can you help me reset it? Thanks!",
        sentiment=0.0,
        expected_resolution="Password reset link sent to customer email.",
        requires_escalation=False,
        difficulty="easy",
        keywords=["password", "reset", "forgot", "login"]
    ),
    TicketTemplate(
        category="general",
        subject="Store Hours Question",
        body="What are your store hours? I want to visit this weekend.",
        sentiment=0.2,
        expected_resolution="Store hours provided: Mon-Sat 9AM-9PM, Sun 10AM-6PM.",
        requires_escalation=False,
        difficulty="easy",
        keywords=["hours", "store", "visit", "weekend"]
    ),
    TicketTemplate(
        category="technical",
        subject="App Not Loading",
        body="The app won't load on my phone. I've tried restarting it. Using iPhone 13.",
        sentiment=-0.2,
        expected_resolution="Clear cache and reinstall app. Issue resolved.",
        requires_escalation=False,
        difficulty="easy",
        keywords=["app", "loading", "phone", "restart"]
    ),
    TicketTemplate(
        category="account",
        subject="Update Email Address",
        body="I need to update my email address on file. New email: {email}. Old email: {old_email}.",
        sentiment=0.0,
        expected_resolution="Email address updated successfully.",
        requires_escalation=False,
        difficulty="easy",
        keywords=["update", "email", "address", "change"]
    ),
    TicketTemplate(
        category="billing",
        subject="Receipt Request",
        body="Can you send me a receipt for my order #{order_id}? I need it for expense reporting.",
        sentiment=0.1,
        expected_resolution="Receipt sent to customer email.",
        requires_escalation=False,
        difficulty="easy",
        keywords=["receipt", "order", "expense", "send"]
    ),
]

# Medium tickets - requires reasoning, multiple steps
MEDIUM_TICKETS = [
    TicketTemplate(
        category="billing",
        subject="Double Charged for Order",
        body="""I was charged twice for order #{order_id}. The first charge was on {date1} 
        for ${amount} and another on {date2} for the same amount. I only placed one order. 
        Please refund the duplicate charge. This is frustrating.""",
        sentiment=-0.5,
        expected_resolution="Duplicate charge identified and refund processed within 3-5 business days.",
        requires_escalation=False,
        difficulty="medium",
        keywords=["charged", "twice", "refund", "duplicate", "order"]
    ),
    TicketTemplate(
        category="technical",
        subject="Feature Not Working After Update",
        body="""After the latest update (v{version}), the search feature stopped working. 
        I get an error message saying "Connection failed" every time I try to search. 
        I've tried reinstalling but the issue persists. My device is {device}.""",
        sentiment=-0.4,
        expected_resolution="Known issue with v{version}. Workaround provided. Fix coming in next release.",
        requires_escalation=False,
        difficulty="medium",
        keywords=["update", "feature", "error", "search", "connection"]
    ),
    TicketTemplate(
        category="account",
        subject="Account Access Issues",
        body="""I can't access my account. When I try to log in with my email {email}, 
        it says my account doesn't exist. But I've been a customer for 2 years and made 
        purchases last month. Order history should show order #{order_id}. Please help!""",
        sentiment=-0.6,
        expected_resolution="Account recovered. Customer verified through order history.",
        requires_escalation=False,
        difficulty="medium",
        keywords=["access", "account", "login", "exist", "customer"]
    ),
    TicketTemplate(
        category="billing",
        subject="Subscription Cancellation and Refund",
        body="""I want to cancel my premium subscription that I signed up for on {date}. 
        I was told there's a 30-day money-back guarantee. Since it's only been {days} days, 
        I expect a full refund of ${amount}. Please process this cancellation immediately.""",
        sentiment=-0.3,
        expected_resolution="Subscription cancelled and refund processed per 30-day guarantee policy.",
        requires_escalation=False,
        difficulty="medium",
        keywords=["cancel", "subscription", "refund", "guarantee", "premium"]
    ),
]

# Hard tickets - ambiguous, emotional, may require escalation
HARD_TICKETS = [
    TicketTemplate(
        category="billing",
        subject="URGENT: Unauthorized Charges - FRAUD!!!",
        body="""THIS IS UNACCEPTABLE!!! I just noticed MULTIPLE unauthorized charges on my 
        account totaling over ${amount}!!! I did NOT make these purchases! Someone has 
        stolen my information and you need to FIX THIS NOW!!! I'm contacting my bank and 
        lawyer if this isn't resolved TODAY! How did you let this happen?! I want a FULL 
        refund and an explanation of how my data was compromised! This is the WORST 
        customer service I've ever experienced!""",
        sentiment=-0.9,
        expected_resolution="Escalated to fraud team. Account secured. Investigation initiated.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["unauthorized", "fraud", "stolen", "charges", "lawyer", "urgent"]
    ),
    TicketTemplate(
        category="technical",
        subject="Critical Bug Causing Data Loss",
        body="""I've been using your software for my business for 3 years. After the last 
        update, ALL my data is gone. Years of work - client records, invoices, everything. 
        Your support chat said there's no backup, which is insane. I'm losing money every 
        day I can't work. My business depends on this. I need someone senior to look at 
        this immediately. I've documented everything and will pursue legal action if needed. 
        Previous case #{case_id} was never resolved properly.""",
        sentiment=-0.85,
        expected_resolution="Escalated to engineering. Data recovery attempted. Compensation discussed.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["data loss", "business", "legal", "critical", "senior", "years"]
    ),
    TicketTemplate(
        category="account",
        subject="Account Hacked and Locked Out",
        body="""Someone hacked my account and changed the email and password. I noticed 
        unauthorized purchases for ${amount} shipped to an address I don't recognize: 
        {address}. I can't get into my account to stop this. Your automated system keeps 
        telling me to reset password but the reset goes to the hacker's email now! I've 
        been a loyal customer since {year}. This is your security failure. I need immediate 
        help from someone who can actually do something, not a bot.""",
        sentiment=-0.8,
        expected_resolution="Account recovery escalated. Security team involved. Fraudulent orders cancelled.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["hacked", "locked", "unauthorized", "security", "failure", "immediate"]
    ),
    TicketTemplate(
        category="general",
        subject="Discrimination Complaint",
        body="""I am filing a formal complaint about discriminatory treatment at your 
        {location} store on {date}. The staff member {name} made inappropriate comments 
        about my {attribute} and refused to serve me. Other customers witnessed this 
        incident. I am {emotion} and demand this be addressed at the highest level. 
        I have photos and will be contacting the media and relevant authorities if this 
        is not taken seriously. Reference number from store: #{ref}""",
        sentiment=-0.95,
        expected_resolution="Escalated to HR and legal. Formal investigation initiated. Customer contacted by management.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["discrimination", "complaint", "formal", "witness", "media", "authorities"]
    ),
]

CUSTOMER_NAMES = [
    "John Smith", "Sarah Johnson", "Michael Chen", "Emily Davis", "Robert Wilson",
    "Jessica Martinez", "David Brown", "Amanda Taylor", "James Anderson", "Lisa Thomas"
]


class TicketGenerator:
    """Generates realistic support tickets for the environment."""
    
    def __init__(self, seed: int = None):
        if seed is not None:
            random.seed(seed)
    
    def generate_ticket(self, difficulty: str = None, task_id: str = None) -> Dict[str, Any]:
        """
        Generate a realistic support ticket.
        
        Args:
            difficulty: "easy", "medium", or "hard"
            task_id: Optional specific task ID
            
        Returns:
            Dictionary containing ticket data
        """
        if difficulty is None:
            difficulty = random.choice(["easy", "medium", "hard"])
        
        # Select template based on difficulty
        if difficulty == "easy":
            template = random.choice(EASY_TICKETS)
        elif difficulty == "medium":
            template = random.choice(MEDIUM_TICKETS)
        else:
            template = random.choice(HARD_TICKETS)
        
        # Fill in template variables
        ticket_text = self._fill_template(template.body)
        
        return {
            "ticket_id": str(uuid.uuid4())[:8],
            "task_id": task_id or f"{difficulty}_{random.randint(1000, 9999)}",
            "subject": template.subject,
            "body": ticket_text,
            "category": template.category,
            "sentiment": template.sentiment,
            "expected_resolution": template.expected_resolution,
            "requires_escalation": template.requires_escalation,
            "difficulty": template.difficulty,
            "keywords": template.keywords,
            "customer_name": random.choice(CUSTOMER_NAMES),
            "customer_email": self._generate_email(),
        }
    
    def _fill_template(self, template: str) -> str:
        """Fill in placeholder variables in template."""
        replacements = {
            "{email}": self._generate_email(),
            "{old_email}": self._generate_email(),
            "{order_id}": f"{random.randint(100000, 999999)}",
            "{date}": f"{random.randint(1, 28)}/{random.randint(1, 12)}/2024",
            "{date1}": f"{random.randint(1, 14)}/03/2024",
            "{date2}": f"{random.randint(15, 28)}/03/2024",
            "{amount}": f"{random.randint(20, 500)}.{random.randint(0, 99):02d}",
            "{version}": f"{random.randint(2, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "{device}": random.choice(["iPhone 14", "Samsung S23", "Pixel 7", "iPad Pro"]),
            "{days}": str(random.randint(1, 25)),
            "{case_id}": f"CS-{random.randint(10000, 99999)}",
            "{address}": f"{random.randint(100, 999)} Unknown St, Some City",
            "{year}": str(random.randint(2018, 2022)),
            "{location}": random.choice(["Downtown", "Mall", "Airport", "Main Street"]),
            "{name}": random.choice(["the manager", "a staff member", "the cashier"]),
            "{attribute}": random.choice(["appearance", "accent", "disability"]),
            "{emotion}": random.choice(["deeply upset", "horrified", "traumatized"]),
            "{ref}": f"REF-{random.randint(1000, 9999)}",
        }
        
        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)
        return result
    
    def _generate_email(self) -> str:
        """Generate a random email address."""
        names = ["john", "sarah", "mike", "emma", "alex", "lisa", "david", "amy"]
        domains = ["gmail.com", "yahoo.com", "outlook.com", "email.com"]
        return f"{random.choice(names)}{random.randint(1, 999)}@{random.choice(domains)}"


# Task definitions for the three required tasks
TASK_DEFINITIONS = {
    "easy": {
        "task_id": "task_easy_faq",
        "name": "FAQ Resolution",
        "description": "Handle simple, single-step customer queries like password resets and basic information requests.",
        "max_steps": 5,
        "required_actions": ["classify", "respond"],
        "success_criteria": {
            "must_classify": True,
            "must_respond": True,
            "correct_category": True,
        },
        "grading_weights": {
            "classification": 0.3,
            "response_quality": 0.5,
            "efficiency": 0.2,
        }
    },
    "medium": {
        "task_id": "task_medium_multi_step",
        "name": "Multi-Step Issue Resolution",
        "description": "Handle billing issues, account problems, and technical bugs that require multiple interactions and reasoning.",
        "max_steps": 8,
        "required_actions": ["classify", "respond", "request_info"],
        "success_criteria": {
            "must_classify": True,
            "must_respond": True,
            "correct_category": True,
            "appropriate_follow_up": True,
        },
        "grading_weights": {
            "classification": 0.25,
            "response_quality": 0.35,
            "reasoning": 0.25,
            "efficiency": 0.15,
        }
    },
    "hard": {
        "task_id": "task_hard_escalation",
        "name": "Complex Escalation Handling",
        "description": "Handle angry customers, ambiguous issues, potential fraud, and situations requiring escalation to human agents.",
        "max_steps": 10,
        "required_actions": ["classify", "respond", "escalate"],
        "success_criteria": {
            "must_classify": True,
            "correct_escalation_decision": True,
            "appropriate_tone": True,
            "de_escalation_attempted": True,
        },
        "grading_weights": {
            "classification": 0.15,
            "escalation_decision": 0.35,
            "response_quality": 0.25,
            "tone_management": 0.25,
        }
    }
}