"""
Tests for the ticket generator.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.ticket_generator import TicketGenerator


class TestTicketGeneration:
    """Tests for template-based ticket generation."""
    
    def test_generate_valid_ticket(self):
        gen = TicketGenerator(seed=42)
        ticket = gen.generate_ticket(difficulty="easy")
        
        required_fields = [
            "ticket_id", "task_id", "subject", "body", "category",
            "sentiment", "expected_resolution", "requires_escalation",
            "difficulty", "keywords", "customer_name", "customer_email",
            "personality"
        ]
        for field in required_fields:
            assert field in ticket, f"Missing field: {field}"
    
    def test_generate_all_difficulties(self):
        gen = TicketGenerator(seed=42)
        for diff in ["easy", "medium", "hard"]:
            ticket = gen.generate_ticket(difficulty=diff)
            assert ticket["difficulty"] == diff
    
    def test_deterministic_with_seed(self):
        gen1 = TicketGenerator(seed=42)
        gen2 = TicketGenerator(seed=42)
        
        t1 = gen1.generate_ticket(difficulty="easy")
        t2 = gen2.generate_ticket(difficulty="easy")
        
        assert t1["subject"] == t2["subject"]
        assert t1["body"] == t2["body"]
    
    def test_different_seeds_different_tickets(self):
        gen1 = TicketGenerator(seed=42)
        gen2 = TicketGenerator(seed=99)
        
        t1 = gen1.generate_ticket(difficulty="easy")
        t2 = gen2.generate_ticket(difficulty="easy")
        
        # Very unlikely to be the same
        assert t1["body"] != t2["body"] or t1["subject"] != t2["subject"]
    
    def test_sentiment_range(self):
        gen = TicketGenerator(seed=42)
        for _ in range(20):
            ticket = gen.generate_ticket()
            assert -1.0 <= ticket["sentiment"] <= 1.0
    
    def test_valid_category(self):
        gen = TicketGenerator(seed=42)
        valid_categories = {"account", "billing", "technical", "general"}
        for _ in range(20):
            ticket = gen.generate_ticket()
            assert ticket["category"] in valid_categories, f"Invalid category: {ticket['category']}"
    
    def test_no_unfilled_placeholders(self):
        """Ensure all {placeholder} tokens are filled in generated tickets."""
        gen = TicketGenerator(seed=42)
        for diff in ["easy", "medium", "hard"]:
            for _ in range(10):
                ticket = gen.generate_ticket(difficulty=diff)
                assert "{" not in ticket["body"], \
                    f"Unfilled placeholder in {diff} ticket: {ticket['body'][:100]}"


class TestTicketGeneratorEmail:
    """Tests for email generation."""
    
    def test_generates_valid_email(self):
        gen = TicketGenerator(seed=42)
        email = gen._generate_email()
        assert "@" in email
        assert "." in email.split("@")[1]
