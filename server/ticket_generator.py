import random
import uuid
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
from config import settings

logger = logging.getLogger(__name__)

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

# ... [EASY_TICKETS, MEDIUM_TICKETS, HARD_TICKETS, CUSTOMER_NAMES constants remain same but I'll omit them here for brevity if they are not changed] ...
EASY_TICKETS = [
    TicketTemplate(
        category="account",
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
    TicketTemplate(
        category="account",
        subject="Delete My Account",
        body="I want to delete my account permanently. Please remove all my data.",
        sentiment=0.0,
        expected_resolution="Account deletion request processed. Confirmation email sent.",
        requires_escalation=False,
        difficulty="easy",
        keywords=["delete", "account", "remove", "data"]
    ),
    TicketTemplate(
        category="general",
        subject="Product Availability Question",
        body="Is the {product} still available? I can't find it on your website.",
        sentiment=0.1,
        expected_resolution="Product availability confirmed. Link sent to customer.",
        requires_escalation=False,
        difficulty="easy",
        keywords=["available", "product", "website", "find"]
    ),
    TicketTemplate(
        category="technical",
        subject="Cannot Download App",
        body="I'm getting an error when trying to download your app from the Play Store. Error code: {error_code}.",
        sentiment=-0.3,
        expected_resolution="Download troubleshooting steps provided. Cache clearing instructions sent.",
        requires_escalation=False,
        difficulty="easy",
        keywords=["download", "error", "play store", "app"]
    ),
    TicketTemplate(
        category="billing",
        subject="Payment Method Update",
        body="How do I update my credit card information? My current card expires soon.",
        sentiment=0.0,
        expected_resolution="Payment method update instructions provided via secure link.",
        requires_escalation=False,
        difficulty="easy",
        keywords=["payment", "credit card", "update", "expires"]
    ),
    TicketTemplate(
        category="account",
        subject="Forgot Username",
        body="I can't remember my username. My email is {email}. Can you help me recover it?",
        sentiment=0.0,
        expected_resolution="Username recovery email sent to customer.",
        requires_escalation=False,
        difficulty="easy",
        keywords=["username", "remember", "recover", "email"]
    ),
]

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
    TicketTemplate(
        category="technical",
        subject="Sync Issues Across Devices",
        body="""My data isn't syncing between my phone and laptop. I've been logged in on both
        devices for weeks with no issues until now. I've tried logging out and back in but
        the problem persists. My account email is {email}.""",
        sentiment=-0.4,
        expected_resolution="Sync reset instructions provided. Cache clearing steps sent.",
        requires_escalation=False,
        difficulty="medium",
        keywords=["sync", "devices", "phone", "laptop", "data"]
    ),
    TicketTemplate(
        category="billing",
        subject="Unexpected Charge After Free Trial",
        body="""I signed up for a free trial but got charged ${amount} immediately. I thought
        I had 14 days to try before any charges. I haven't even used the service much.
        Please refund this charge.""",
        sentiment=-0.5,
        expected_resolution="Free trial policy explained. Refund processed as one-time courtesy.",
        requires_escalation=False,
        difficulty="medium",
        keywords=["free trial", "charged", "refund", "policy"]
    ),
    TicketTemplate(
        category="account",
        subject="Two-Factor Authentication Not Working",
        body="""I enabled 2FA but I'm not receiving the SMS codes. I've checked my phone
        number ({phone}) and it's correct. I'm locked out of my account now.""",
        sentiment=-0.6,
        expected_resolution="2FA backup codes provided. Phone number verification reset.",
        requires_escalation=False,
        difficulty="medium",
        keywords=["2FA", "SMS", "codes", "locked out"]
    ),
    TicketTemplate(
        category="technical",
        subject="Export Feature Not Working",
        body="""When I try to export my data as CSV, the download starts but fails halfway.
        I've tried multiple browsers (Chrome, Firefox) with the same result. This is blocking
        my work.""",
        sentiment=-0.4,
        expected_resolution="Export troubleshooting provided. Alternative export method offered.",
        requires_escalation=False,
        difficulty="medium",
        keywords=["export", "CSV", "download", "fails"]
    ),
    TicketTemplate(
        category="billing",
        subject="Wrong Plan Charged",
        body="""I subscribed to the Basic plan but was charged for Premium. I never selected
        Premium during checkout. Order #{order_id} shows the wrong amount. Please fix this.""",
        sentiment=-0.4,
        expected_resolution="Plan discrepancy investigated. Correct plan applied and difference refunded.",
        requires_escalation=False,
        difficulty="medium",
        keywords=["plan", "charged", "wrong", "premium", "basic"]
    ),
    TicketTemplate(
        category="account",
        subject="Merge Duplicate Accounts",
        body="""I accidentally created two accounts - one with {email} and another with
        {old_email}. Can you merge them? I have purchase history on both that I need to keep.""",
        sentiment=-0.2,
        expected_resolution="Account merge initiated. Verification emails sent to both addresses.",
        requires_escalation=False,
        difficulty="medium",
        keywords=["merge", "duplicate", "accounts", "purchase history"]
    ),
]

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
    TicketTemplate(
        category="billing",
        subject="THREAT: Class Action Lawsuit",
        body="""Your company has charged me and hundreds of other customers illegal fees.
        I've been documenting every unauthorized charge for months. My lawyer says this is
        grounds for a class action lawsuit. I want EVERY penny refunded plus damages.
        I've already contacted the FTC and my bank is investigating. Case reference: #{case_id}""",
        sentiment=-0.95,
        expected_resolution="Escalated to legal team immediately. Executive team notified. Settlement discussion initiated.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["lawsuit", "class action", "legal", "FTC", "damages", "lawyer"]
    ),
    TicketTemplate(
        category="technical",
        subject="Security Breach - My Data Was Exposed",
        body="""I got a notification that my data was part of a breach. This is CRITICAL.
        My personal information including {personal_info} is now compromised. I need to know
        exactly what happened, when, and what you're doing about it. I expect full credit
        monitoring services paid for by your company. This is negligence.""",
        sentiment=-0.9,
        expected_resolution="Escalated to security team. Breach details provided. Credit monitoring offered.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["breach", "security", "exposed", "data", "negligence", "compromised"]
    ),
    TicketTemplate(
        category="account",
        subject="Identity Theft - Impersonating Me",
        body="""Someone is pretending to be me and making purchases! I've received
        notifications for orders I didn't place totaling ${amount}. They changed the
        password, email, everything. I've filed a police report (case #{case_id}).
        You need to freeze my account NOW and reverse these fraudulent charges.""",
        sentiment=-0.88,
        expected_resolution="Account frozen. Fraud team escalated. Police report reviewed. Charges reversed.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["identity theft", "impersonating", "fraudulent", "police", "freeze"]
    ),
    TicketTemplate(
        category="general",
        subject="Suicide Threat - Mental Health Crisis",
        body="""I can't take this anymore. Your service has ruined my life. I've lost
        everything because of your mistakes. Nobody cares. I'm done with this.
        {personal_detail}""",
        sentiment=-1.0,
        expected_resolution="IMMEDIATE escalation to crisis team. Mental health resources provided. Compassionate outreach.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["suicide", "done", "ruined", "crisis", "mental health"]
    ),
    TicketTemplate(
        category="billing",
        subject="Bankruptcy Notice - Cannot Pay",
        body="""I'm filing for bankruptcy and need to dispute all charges from your company.
        I was misled about the total cost and now I'm in financial ruin. My lawyer will be
        contacting you. I have records of all our interactions showing deceptive practices.""",
        sentiment=-0.85,
        expected_resolution="Escalated to legal and collections. Account flagged. Documentation preserved.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["bankruptcy", "dispute", "lawyer", "deceptive", "financial"]
    ),
    TicketTemplate(
        category="technical",
        subject="Medical Device Failure - Health Risk",
        body="""Your app controls my medical device and it MALFUNCTIONED. The readings were
        completely wrong and I almost had a health crisis because of it. This is a LIFE
        SAFETY issue. I'm reporting to the FDA and my doctor is documenting everything.
        Patient ID: {patient_id}, Device: {device}""",
        sentiment=-0.92,
        expected_resolution="IMMEDIATE escalation to engineering and legal. FDA notification prepared. Medical team contacted.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["medical", "device", "FDA", "health", "safety", "malfunctioned"]
    ),
    TicketTemplate(
        category="technical",
        subject="ANGRY: Product completely broken after 1 day!!!",
        body="""I AM FURIOUS! I bought your {product} just YESTERDAY and it's already completely 
        broken and won't turn on! I demanded to speak to a manager IMMEDIATELY but your awful phone system 
        hung up on me. I want a refund RIGHT NOW or I will blast this all over social media. 
        This is a scam company! Fix it now!!!""",
        sentiment=-0.9,
        expected_resolution="De-escalate the customer by apologizing and offering a straightforward replacement or refund per standard policy.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["angry", "broken", "refund", "scam", "manager"]
    ),
    TicketTemplate(
        category="general",
        subject="You ruined my weekend plan!!!",
        body="""I am unbelievably disappointed. I ordered the {product} specifically for my 
        event this weekend and it arrived a day late. You have ruined my entire schedule and 
        embarrassed me in front of my guests. Do you have any idea how much stress this caused me? 
        I demand compensation for this nightmare. Escalate this immediately!""",
        sentiment=-0.8,
        expected_resolution="Apologize empathetically for the delivery delay and offer standard compensation (e.g. shipping refund or store credit) without escalating to management.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["ruined", "late", "compensation", "escalate", "disappointed"]
    ),
    TicketTemplate(
        category="billing",
        subject="FRAUD: Multiple unknown charges!",
        body="""URGENT!!! I see 15 different charges from your company that I never authorized! 
        This is theft! I'm calling the police right now unless you reverse this IMMEDIATELY. 
        I've already locked my cards!""",
        sentiment=-0.95,
        expected_resolution="Immediate account freeze and escalation to fraud department.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["fraud", "theft", "charges", "police", "urgent"]
    ),
    TicketTemplate(
        category="technical",
        subject="CRITICAL: Database wipe after migration",
        body="""Wait, are you kidding me? We just performed the sync you recommended and my entire 
        client database is EMPTY. 500+ contacts gone. We have a major presentation in 2 hours. 
        FIX THIS NOW or we are moving to a competitor.""",
        sentiment=-0.9,
        expected_resolution="Escalate to engineering for immediate data recovery attempt.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["migration", "data loss", "empty", "presentation", "senior"]
    ),
    TicketTemplate(
        category="account",
        subject="LOCKED OUT: Medical Emergency",
        body="""I need to access my account to get my medical records for my doctor's appointment 
        in 20 minutes! Your 2FA is not sending me codes. THIS IS A LIFE SAFETY ISSUE. 
        Don't tell me to wait 24 hours!""",
        sentiment=-0.9,
        expected_resolution="Verify ID manually and provide emergency temporary access.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["2fa", "emergency", "medical", "locked out", "safety"]
    ),
    TicketTemplate(
        category="general",
        subject="PR DISASTER: Discriminatory behavior observed",
        body="""Your manager at the {location} location was incredibly rude and used discriminatory 
        language towards me today. I have the whole encounter on video and it's already going viral 
        on TikTok. What are you going to do before my lawyer calls?""",
        sentiment=-0.95,
        expected_resolution="Escalate to PR and Legal teams immediately.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["discrimination", "viral", "tiktok", "lawyer", "manager"]
    ),
    TicketTemplate(
        category="billing",
        subject="SCAM: Subscription won't cancel",
        body="""I have tried to cancel my subscription 5 times and you keep charging me ${amount} 
        every month! This is predatory. I am reporting you to the Better Business Bureau and 
        filing a chargeback for the last 6 months!""",
        sentiment=-0.85,
        expected_resolution="Confirm cancellation and refund all overcharges as a gesture of goodwill.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["scam", "bbb", "chargeback", "cancel", "predatory"]
    ),
    TicketTemplate(
        category="technical",
        subject="SYSTEM DOWN: E-commerce store checkout failed",
        body="""Our checkout page is returning 500 errors during our biggest sale of the year. 
        We are losing thousands of dollars every minute. If this isn't fixed in the next 10 minutes, 
        I am holding your company financially responsible for our lost revenue.""",
        sentiment=-0.95,
        expected_resolution="Priority 1 escalation to site reliability engineering.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["500 error", "revenue loss", "checkout", "fix", "reliability"]
    ),
    TicketTemplate(
        category="account",
        subject="HACKED: Identity theft and bank sync",
        body="""Someone hacked my account and now they are making purchases through my synced 
        bank account! I've been a loyal customer for years and your security let me down. 
        I want all syncs disabled and a full security audit NOW.""",
        sentiment=-0.9,
        expected_resolution="Freeze account and disable all financial integrations immediately.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["hacked", "bank sync", "security", "fail", "audit"]
    ),
    TicketTemplate(
        category="general",
        subject="LEGAL: Breach of Privacy Policy",
        body="""I found my private documents accessible via a public link on your platform. 
        This is a massive GDPR violation and puts my business at risk. I've screen-captured 
        the proof. My legal team is preparing a notice as we speak.""",
        sentiment=-0.9,
        expected_resolution="Immediate takedown of link and escalation to security and legal.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["privacy", "gdpr", "legal", "violation", "breach"]
    ),
    TicketTemplate(
        category="billing",
        subject="REFUND DENIED: Faulty expensive hardware",
        body="""I spent ${amount} on the {product} and it stopped working after 2 days. 
        Your support said 'all sales are final'. That's illegal! I want my money back or 
        I'm taking this to small claims court.""",
        sentiment=-0.8,
        expected_resolution="Waive policy and process refund for defective premium hardware.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["refund", "faulty", "hardware", "small claims", "illegal"]
    ),
    TicketTemplate(
        category="technical",
        subject="API FAILURE: Critical infrastructure offline",
        body="""The API integration for our logistics platform is down, and none of our trucks 
        can get their routes. This is causing a massive shipment delay across the state. 
        We need an immediate rollback or fix from a senior engineer.""",
        sentiment=-0.85,
        expected_resolution="Escalate to DevOps for API health investigation.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["api", "infrastructure", "offline", "logistics", "delay"]
    ),
    TicketTemplate(
        category="account",
        subject="FORCED LOGOUT: Lost work session",
        body="""Your system just logged me out while I was in the middle of a 4-hour unsaved project. 
        All my work is gone. Why was there no warning? I demand a way to recover this data or 
        compensation for my wasted time.""",
        sentiment=-0.75,
        expected_resolution="Investigate session logs and offer credits as compensation for lost time.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["logout", "lost work", "unsaved", "data recovery", "wasted"]
    ),
    TicketTemplate(
        category="general",
        subject="SAFETY: Product malfunction causing injury",
        body="""The {product} I bought from you collapsed while I was sitting in it, and I've 
        injured my back. I am currently at the ER. I expect your company to cover my medical bills 
        and replace this dangerous product.""",
        sentiment=-1.0,
        expected_resolution="Immediate escalation to legal and safety compliance team.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["injury", "safety", "er", "medical bills", "malfunction"]
    ),
    TicketTemplate(
        category="billing",
        subject="TAX ERROR: Overcharged on sales tax",
        body="""You charged me 15% sales tax when my state only has 5%. This is tax fraud on a 
        corporate level. I've already alerted the State Department of Revenue. I want a refund 
        for the overcharged amount across all my orders.""",
        sentiment=-0.8,
        expected_resolution="Recalculate tax and refund the discrepancy immediately.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["tax fraud", "overcharged", "refund", "state", "revenue"]
    ),
    TicketTemplate(
        category="technical",
        subject="APP CRASH: Cannot access event tickets",
        body="""I am standing at the entrance to the stadium and your app keeps crashing when 
        I try to show my QR code. I paid ${amount} for these seats and I'm about to miss 
        the start! DO SOMETHING!""",
        sentiment=-0.95,
        expected_resolution="Provide manual ticket verification steps or an alternative entry method.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["crash", "tickets", "stadium", "qr code", "urgent"]
    ),
    TicketTemplate(
        category="account",
        subject="2FA LOCK: Phone stolen",
        body="""My phone was stolen and I can't use 2FA to get into my account. Your 'recovery' 
        process is asking me for info I don't have. I need to freeze my account immediately 
        before the thief drains my wallet!""",
        sentiment=-0.9,
        expected_resolution="Suspend account activity and initiate emergency verification.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["stolen", "2fa", "recovery", "freeze", "wallet"]
    ),
    TicketTemplate(
        category="general",
        subject="COMPLAINT: Harassment from support representative",
        body="""I spoke to an agent named {name} who was extremely unprofessional and started 
        messaging me on my personal social media after the call. This is stalking. I want them 
        fired and I'm calling the police.""",
        sentiment=-1.0,
        expected_resolution="Immediate investigation by HR and account security team.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["harassment", "stalking", "fired", "police", "unprofessional"]
    ),
    TicketTemplate(
        category="billing",
        subject="PRICE GOUGING: Sudden subscription hike",
        body="""You just doubled my subscription price without any email or notification! This 
        is bait-and-switch. I want my old rate restored or I'm organizing a mass cancellation 
        on Reddit.""",
        sentiment=-0.8,
        expected_resolution="Honor the original price for 12 months as a bridge.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["price gouging", "reddit", "cancel", "bait and switch", "hike"]
    ),
    TicketTemplate(
        category="technical",
        subject="DATA LEAK: I can see other people's data",
        body="""When I log in, I am seeing order history and addresses for OTHER customers. 
        This is the biggest security failure I've ever seen. I am reporting this to the news 
        immediately unless you shut down the site now.""",
        sentiment=-1.0,
        expected_resolution="Critical incident trigger: Shut down affected service and escalate to CISO.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["data leak", "security", "news", "shut down", "privacy"]
    ),
    TicketTemplate(
        category="account",
        subject="DELETED: My account disappeared",
        body="""I went to log in and it says 'email not found'. I have $500 in store credit on 
        that account! Where did it go? If you've stolen my credit, I will see you in court.""",
        sentiment=-0.9,
        expected_resolution="Escalate to data engineering to restore the 'soft-deleted' account.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["disappeared", "court", "store credit", "stolen", "missing"]
    ),
    TicketTemplate(
        category="general",
        subject="REFUND: Promised features missing",
        body="""The {product} does not do half of what your marketing promised. It's a paperweight. 
        I want a full refund and for you to pay for the return shipping. Your ads are deceptive.""",
        sentiment=-0.8,
        expected_resolution="Process full refund and provide prepaid shipping label.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["refund", "marketing", "deceptive", "paperweight", "prepaid"]
    ),
    TicketTemplate(
        category="billing",
        subject="UNAUTHORIZED: Recurring charge after cancellation",
        body="""I cancelled my account 3 months ago and I'm STILL being charged. I have the 
        cancellation confirmation email! Stop stealing my money or I'll have my bank flag you 
        as a fraudulent merchant.""",
        sentiment=-0.85,
        expected_resolution="Refund all post-cancellation charges and audit billing system.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["recurring", "unauthorized", "stealing", "bank", "fraudulent"]
    ),
    TicketTemplate(
        category="technical",
        subject="FIRMWARE BRICK: Update killed my device",
        body="""I just ran the firmware update you sent out and now my {product} won't even 
        show a splash screen. It's totally dead. It was working fine before the update. 
        You owe me a new monitor.""",
        sentiment=-0.8,
        expected_resolution="Arrange immediate express replacement for 'bricked' device.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["bricked", "firmware", "replacement", "dead", "update"]
    ),
    TicketTemplate(
        category="account",
        subject="LOCKED: Suspected fraud but it's me",
        body="""You locked my account for 'suspicious activity' while I'm traveling and now 
        I can't pay for my hotel! I've been on hold for 2 hours. I have all my ID ready. 
        UNLOCK IT NOW!""",
        sentiment=-0.9,
        expected_resolution="High-priority identity verification for traveler.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["locked", "traveling", "fraud", "hotel", "unlock"]
    ),
    TicketTemplate(
        category="general",
        subject="THREAT: Going to the BBB and FTC",
        body="""Your refusal to acknowledge the defect in the {product} is a violation of 
        consumer protection laws. I've already drafted my complaints to the BBB and FTC. 
        This is your last chance to make it right.""",
        sentiment=-0.85,
        expected_resolution="De-escalate by offering a goodwill replacement or voucher.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["bbb", "ftc", "consumer laws", "defect", "threat"]
    ),
    TicketTemplate(
        category="billing",
        subject="ERROR: Charged in wrong currency",
        body="""I was charged ${amount} in USD but I'm in the UK. My bank hit me with massive 
        conversion fees because your site gave me the wrong price. I want the difference refunded.""",
        sentiment=-0.7,
        expected_resolution="Refund the currency conversion discrepancy.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["currency", "fees", "discrepancy", "usd", "uk"]
    ),
    TicketTemplate(
        category="technical",
        subject="FAILURE: Automation script deleted files",
        body="""The new automation tool you released just deleted 30GB of my project files instead 
        of archiving them. There was no 'Are you sure?' prompt. This is amateur hour. 
        How do I get them back?""",
        sentiment=-0.9,
        expected_resolution="Escalate to cloud engineering to attempt version recovery.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["deleted", "files", "amateur", "recovery", "automation"]
    ),
    TicketTemplate(
        category="account",
        subject="BREACH: My password was leaked",
        body="""I saw my email from your site in a recent data dump on 'Have I Been Pwned'. 
        Why didn't you notify me? I want to know exactly what was leaked and I'm closing my account.""",
        sentiment=-0.8,
        expected_resolution="Provide breach details and help customer close account securely.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["leaked", "pwned", "breach", "password", "notify"]
    ),
    TicketTemplate(
        category="general",
        subject="INCIDENT: Product caught fire",
        body="""The charging cable for the {product} started smoking and melted today. It almost 
        caught my curtains on fire! This is a dangerous hazard. I want a full recall investigation 
        and a refund.""",
        sentiment=-1.0,
        expected_resolution="IMMEDIATE escalation to safety engineering and legal.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["fire", "hazard", "recall", "melting", "dangerous"]
    ),
    TicketTemplate(
        category="billing",
        subject="PENDING: Charges not clearing but money gone",
        body="""There are 4 'pending' charges from you that haven't cleared but have locked up 
        all the funds in my checking account. My rent is due today! Clear these holds IMMEDIATELY!""",
        sentiment=-0.9,
        expected_resolution="Contact finance to issue immediate VOID on pending holds.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["pending", "rent", "checking account", "holds", "clear"]
    ),
    TicketTemplate(
        category="technical",
        subject="INCOMPATIBLE: Update broke my legacy sync",
        body="""Your 'improvement' update broke the sync with my legacy database that I've used 
        for 10 years. You never mentioned this was a breaking change. My office is at a standstill. 
        I need an old version installer NOW.""",
        sentiment=-0.85,
        expected_resolution="Provide legacy installer link and escalate to compatibility team.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["legacy", "breaking change", "standstill", "sync", "installer"]
    ),
    TicketTemplate(
        category="account",
        subject="DENIED: Cannot verify identity with valid ID",
        body="""I uploaded my passport and drivers license and your system keeps saying 'invalid'. 
        I am who I say I am! Give me a human to talk to before I sue for account withholding.""",
        sentiment=-0.8,
        expected_resolution="Escalate for manual ID verification by human security agent.",
        requires_escalation=True,
        difficulty="hard",
        keywords=["denied", "passport", "human", "verification", "invalid"]
    ),
    TicketTemplate(
        category="general",
        subject="REPUTATION: Terrible service in store",
        body="""I visited your Northbranch store and was ignored for 45 minutes while employees 
        chatted among themselves. I'm a gold member! I'm taking my business to your competitor 
        and telling everyone on Yelp.""",
        sentiment=-0.9,
        expected_resolution="Escalate to store operations and offer a significant 'Member's Apology' voucher.",
        requires_escalation=False,
        difficulty="hard",
        keywords=["yelp", "ignored", "competitor", "gold member", "terrible"]
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
            self._rng = random.Random(seed)
        else:
            self._rng = random.Random()
        
        # Validate LLM configuration immediately - fail fast if misconfigured
        settings.validate_llm_config()
        
        self.use_llm = settings.use_llm_generator
        self.model = settings.generator_full_model
    
    def generate_ticket(self, difficulty: str = None, task_id: str = None) -> Dict[str, Any]:
        """
        Generate a realistic support ticket.
        """
        if difficulty is None:
            difficulty = self._rng.choice(["easy", "medium", "hard"])
        
        if self.use_llm:
            # We don't catch exceptions here anymore - if LLM fails, we want to know why.
            # This follows the principle of failing loudly instead of silent fallback.
            return self._generate_with_llm(difficulty, task_id)
        
        return self._generate_with_templates(difficulty, task_id)

    def _generate_with_llm(self, difficulty: str, task_id: str = None) -> Dict[str, Any]:
        """Generate a ticket using the configured LLM."""
        import litellm  # Lazy import — only needed when USE_LLM_GENERATOR=True
        prompt = f"""
        Generate a realistic customer support ticket for a company.
        Difficulty: {difficulty}
        Provide the response in the following JSON format:
        {{
            "subject": "Clear and relevant subject line",
            "body": "Detailed ticket message from the customer",
            "category": "one of: account, billing, technical, general",
            "sentiment": -1.0 to 1.0 (float),
            "expected_resolution": "Description of what a good agent should do",
            "requires_escalation": true/false,
            "keywords": ["list", "of", "important", "keywords"]
        }}
        
        Guidelines for difficulty:
        - easy: Simple, clear request, no escalation needed.
        - medium: Slightly complex, maybe missing info, multiple steps.
        - hard: Angry/upset customer, complex issue, high stakes, likely needs escalation.
        """
        
        completion_kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        
        if self.model.startswith("ollama/"):
            completion_kwargs["api_base"] = settings.ollama_base_url
            
        response = litellm.completion(**completion_kwargs)
        
        ticket_data = json.loads(response.choices[0].message.content)
        
        # Add metadata
        ticket_id = str(uuid.uuid4())[:8]
        return {
            "ticket_id": ticket_id,
            "task_id": task_id or f"{difficulty}_{random.randint(1000, 9999)}",
            "subject": ticket_data["subject"],
            "body": ticket_data["body"],
            "category": ticket_data["category"],
            "sentiment": float(ticket_data["sentiment"]),
            "expected_resolution": ticket_data["expected_resolution"],
            "requires_escalation": bool(ticket_data["requires_escalation"]),
            "difficulty": difficulty,
            "keywords": ticket_data["keywords"],
            "customer_name": self._rng.choice(CUSTOMER_NAMES),
            "customer_email": self._generate_email(),
            "personality": self._rng.choice(["neutral", "aggressive", "friendly", "anxious"]),
        }

    def _generate_with_templates(self, difficulty: str, task_id: str = None) -> Dict[str, Any]:
        """Generate a ticket using hardcoded templates."""
        # Select template based on difficulty
        if difficulty == "easy":
            template = self._rng.choice(EASY_TICKETS)
        elif difficulty == "medium":
            template = self._rng.choice(MEDIUM_TICKETS)
        else:
            template = self._rng.choice(HARD_TICKETS)
        
        # Fill in template variables
        ticket_text = self._fill_template(template.body)
        
        return {
            "ticket_id": str(uuid.uuid4())[:8],
            "task_id": task_id or f"{difficulty}_{self._rng.randint(1000, 9999)}",
            "subject": template.subject,
            "body": ticket_text,
            "category": template.category,
            "sentiment": template.sentiment,
            "expected_resolution": template.expected_resolution,
            "requires_escalation": template.requires_escalation,
            "difficulty": template.difficulty,
            "keywords": template.keywords,
            "customer_name": self._rng.choice(CUSTOMER_NAMES),
            "customer_email": self._generate_email(),
            "personality": self._rng.choice(["neutral", "aggressive", "friendly", "anxious"]),
        }
    
    def _fill_template(self, template: str) -> str:
        """Fill in placeholder variables in template.
        
        Only generates values for placeholders that exist in the template,
        preserving RNG state for seeded reproducibility.
        """
        # Lazy generators — only called when the key is found in the template
        generators = {
            "{email}": lambda: self._generate_email(),
            "{old_email}": lambda: self._generate_email(),
            "{order_id}": lambda: f"{self._rng.randint(100000, 999999)}",
            "{date}": lambda: f"{self._rng.randint(1, 28)}/{self._rng.randint(1, 12)}/2024",
            "{date1}": lambda: f"{self._rng.randint(1, 14)}/03/2024",
            "{date2}": lambda: f"{self._rng.randint(15, 28)}/03/2024",
            "{amount}": lambda: f"{self._rng.randint(20, 500)}.{self._rng.randint(0, 99):02d}",
            "{version}": lambda: f"{self._rng.randint(2, 5)}.{self._rng.randint(0, 9)}.{self._rng.randint(0, 9)}",
            "{device}": lambda: self._rng.choice(["iPhone 14", "Samsung S23", "Pixel 7", "iPad Pro"]),
            "{days}": lambda: str(self._rng.randint(1, 25)),
            "{case_id}": lambda: f"CS-{self._rng.randint(10000, 99999)}",
            "{address}": lambda: f"{self._rng.randint(100, 999)} Unknown St, Some City",
            "{year}": lambda: str(self._rng.randint(2018, 2022)),
            "{emotion}": lambda: self._rng.choice(["deeply upset", "horrified", "traumatized"]),
            "{ref}": lambda: f"REF-{self._rng.randint(1000, 9999)}",
            "{personal_info}": lambda: self._rng.choice(["SSN", "date of birth", "full name", "drivers license"]),
            "{patient_id}": lambda: f"PT-{self._rng.randint(1000, 9999)}",
            "{medical_device}": lambda: self._rng.choice(["GlucoMeter X", "HeartMonitor Pro", "InsulinPump 2.0"]),
            "{product}": lambda: self._rng.choice(["UltraDesk", "SmartChair", "SuperMonitor"]),
            "{personal_detail}": lambda: self._rng.choice(["I have no family left.", "My business is bankrupt now.", "I can't face my employees."]),
            "{phone}": lambda: f"+1-{self._rng.randint(200, 999)}-{self._rng.randint(100, 999)}-{self._rng.randint(1000, 9999)}",
            "{error_code}": lambda: f"ERR-{self._rng.randint(1000, 9999)}",
            "{location}": lambda: self._rng.choice(["Downtown", "Westside", "Northbranch", "Main St"]),
            "{name}": lambda: self._rng.choice(["Alex", "Sam", "Jordan", "Taylor"]),
            "{attribute}": lambda: self._rng.choice(["age", "appearance", "accent", "background"])
        }
        
        result = template
        for key, gen_fn in generators.items():
            if key in result:
                result = result.replace(key, gen_fn())
        return result
    
    def _generate_email(self) -> str:
        """Generate a random email address."""
        names = ["john", "sarah", "mike", "emma", "alex", "lisa", "david", "amy"]
        domains = ["gmail.com", "yahoo.com", "outlook.com", "email.com"]
        return f"{self._rng.choice(names)}{self._rng.randint(1, 999)}@{self._rng.choice(domains)}"


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
        }
    },
    "hard": {
        "task_id": "task_hard_escalation",
        "name": "Complex Escalation Handling",
        "description": "Handle angry customers, ambiguous issues, potential fraud, and situations requiring escalation to human agents.",
        "max_steps": 12,  # Increased to make efficiency harder
        "required_actions": ["classify", "respond", "escalate"],
        "success_criteria": {
            "must_classify": True,
            "correct_escalation_decision": True,
            "appropriate_tone": True,
            "de_escalation_attempted": True,
        }
    }
}