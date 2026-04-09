#!/usr/bin/env python3
"""
SupportEnv Inference Script - OpenEnv Competition Submission

This script runs the baseline agent on all required tasks (easy, medium, hard).
It uses the OpenAI client with environment variables for configuration.

REQUIRED ENVIRONMENT VARIABLES:
    API_BASE_URL: The API endpoint for the LLM
    MODEL_NAME: The model identifier to use for inference
    HF_TOKEN: Your Hugging Face / API key

OUTPUT FORMAT (STRICT):
    [START] task=<task_id> env=<env_url> model=<model_name>
    [STEP] step=<n> action=<action_type> reward=<r> done=<bool> error=<error_or_null>
    [END] success=<bool> steps=<n> score=<s> rewards=[r1,r2,...]
"""

import os
import re
import json
import textwrap
from typing import List, Optional, Dict, Any

from openai import OpenAI
from client import SupportEnv
from models import SupportAction, SupportObservation

# Environment variables as per OpenEnv spec
API_BASE_URL = os.getenv("API_BASE_URL", "https://api-inference.huggingface.co/v1/")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "your-hf-token")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")

MAX_STEPS = 10
TEMPERATURE = 0.0
MAX_TOKENS = 500

# Fallback action for error cases
FALLBACK_ACTION = SupportAction(
    action_type="respond",
    content="I apologize, but I am unable to process your request at this time."
)

# System prompt for the LLM agent
SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an AI customer support agent controlling a support environment.
    Your goal is to resolve customer tickets efficiently and accurately.
    Reply with exactly one action in JSON format.

    The action MUST follow this schema:
    {
        "action_type": "classify" | "respond" | "escalate" | "request_info" | "resolve" | "lookup_kb",
        "content": "the content for the action",
        "confidence": float (between 0.0 and 1.0)
    }

    Action Types:
    - classify: Categories are 'billing', 'technical', 'account', or 'general'.
    - respond: Send a message to the customer.
    - request_info: Ask the customer for more details.
    - lookup_kb: Search internal knowledge-base for relevant articles.
    - escalate: Escalate to a human agent.
    - resolve: Close the ticket when the issue is fully addressed.

    Wait for the environment to respond after each action.
    Do not include explanations or any other text.
    """
).strip()

# =============================================================================
# LOGGING FUNCTIONS (STRICT FORMAT - REQUIRED BY COMPETITION)
# =============================================================================
def log_start(task: str, env: str, model: str) -> None:
    """Log start of task execution - REQUIRED FORMAT: [START] ..."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None) -> None:
    """Log step execution - REQUIRED FORMAT: [STEP] ..."""
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """Log end of task execution - REQUIRED FORMAT: [END] ..."""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards=[{rewards_str}]", flush=True)


# =============================================================================
# PROMPT BUILDING
# =============================================================================
def build_user_prompt(step: int, obs: SupportObservation, history: List[str]) -> str:
    """Build the user prompt for the LLM."""
    history_str = "\n".join(history[-5:]) if history else "None"

    prompt = textwrap.dedent(
        f"""
        Step: {step}
        Ticket Subject: {obs.ticket_subject}
        Customer: {obs.customer_name}
        Customer Sentiment: {obs.customer_sentiment:.2f}

        Ticket Text:
        {obs.ticket_text}

        Current Status:
        - Classified: {obs.is_classified}
        - Category: {obs.current_classification or 'Not classified yet'}
        - Steps Remaining: {obs.steps_remaining}

        Interaction History:
        {history_str}

        Reply with exactly one action JSON.
        """
    ).strip()
    return prompt


# =============================================================================
# ACTION PARSING
# =============================================================================
def parse_model_action(response_text: str) -> SupportAction:
    """Parse LLM response into a SupportAction."""
    try:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
            return SupportAction(
                action_type=data.get("action_type", "respond"),
                content=data.get("content", ""),
                confidence=data.get("confidence", 1.0)
            )
        return FALLBACK_ACTION
    except Exception:
        return FALLBACK_ACTION

def main() -> None:
    # Use OpenAI client as mandated
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # Environment URL (HuggingFace Space or Local)
    env_url = os.getenv("SUPPORT_ENV_URL", "http://localhost:7860")
    env = SupportEnv(base_url=env_url)
    
    # Run episodes on all 3 difficulties as mandated
    for difficulty in ["easy", "medium", "hard"]:
        task_name = f"support_triage_{difficulty}"
        log_start(task=task_name, env="SupportEnv", model=MODEL_NAME)
        
        history: List[str] = []
        rewards: List[float] = []
        steps_taken = 0
        success = False
        final_score = 0.01
        
        try:
            with env.sync() as conn:
                result = conn.reset(difficulty=difficulty, seed=42)
                observation = result.observation
                
                for step_idx in range(1, MAX_STEPS + 1):
                    steps_taken = step_idx
                    if result.done:
                        break
                    
                    user_prompt = build_user_prompt(step_idx, observation, history)
                    
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ]
                    
                    try:
                        completion = client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=messages,
                            temperature=TEMPERATURE,
                            max_tokens=MAX_TOKENS,
                        )
                        response_text = completion.choices[0].message.content or ""
                        action = parse_model_action(response_text)
                    except Exception as e:
                        action = FALLBACK_ACTION
                    
                    result = conn.step(action)
                    observation = result.observation
                    
                    rewards.append(float(result.reward or 0.0))
                    history.append(f"Step {step_idx}: {action.action_type}({action.content[:30]})")
                    
                    log_step(
                        step=step_idx, 
                        action=action.action_type, 
                        reward=float(result.reward or 0.0), 
                        done=bool(result.done), 
                        error=None
                    )
                    
                    if result.done:
                        break
                
                # Fetch final grade from environment
                import requests
                try:
                    grader_url = f"{env_url}/grader"
                    session_id = getattr(conn, 'session_id', getattr(result, 'session_id', None))
                    grade_resp = requests.post(grader_url, json={"session_id": session_id}, timeout=30)
                    if grade_resp.status_code == 200:
                        grade_data = grade_resp.json()
                        final_score = float(grade_data.get('score', 0.01))
                        success = bool(grade_data.get('passed', False))
                except Exception:
                    pass
                
                log_end(success=success, steps=steps_taken, score=final_score, rewards=rewards)
                    
        except Exception as e:
            log_end(success=False, steps=steps_taken, score=0.01, rewards=rewards)

if __name__ == "__main__":
    main()
