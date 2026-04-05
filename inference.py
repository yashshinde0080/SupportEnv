
import os
import re
import json
import textwrap
import requests
from typing import List, Optional, Dict, Any

from openai import OpenAI
from client import SupportEnv
from models import SupportAction, SupportObservation

# Environment variables as per OpenEnv spec
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
# Prioritize OPENAI_API_KEY as per standard client expectation, then HF_TOKEN
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("HF_TOKEN") or "your-api-key"
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")

MAX_STEPS = 10
TEMPERATURE = 0.0
MAX_TOKENS = 500

# Fallback action
FALLBACK_ACTION = SupportAction(action_type="respond", content="I apologize, but I am unable to process your request at this time.")

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an AI customer support agent controlling a support environment.
    Your goal is to resolve customer tickets efficiently and accurately.
    Reply with exactly one action in JSON format.
    
    The action MUST follow this schema:
    {
        "action_type": "classify" | "respond" | "escalate" | "request_info" | "resolve",
        "content": "the content for the action (category for classify, message for respond, reason for others)",
        "confidence": float (between 0.0 and 1.0)
    }
    
    Action Types:
    - classify: Categories are 'billing', 'technical', 'account', or 'general'.
    - respond: Send a message to the customer.
    - request_info: Ask the customer for more details (e.g. order ID).
    - lookup_kb: Search internal knowledge‑base for relevant articles (e.g. 'password', 'refund').
    - escalate: Escalate to a human agent if you cannot solve it or if a safety issue is suspect.
    - resolve: Close the ticket when the issue is fully addressed.
    
    Wait for the environment to respond after each action.
    Do not include explanations or any other text.
    """
).strip()


def build_user_prompt(step: int, obs: SupportObservation, history: List[str]) -> str:
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


def parse_model_action(response_text: str) -> SupportAction:
    try:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
            return SupportAction(
                action_type=data.get("action_type", "respond"),
                content=data.get("content", ""),
                confidence=data.get("confidence")
            )
        return FALLBACK_ACTION
    except Exception:
        return FALLBACK_ACTION


def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # Environment URL (default to local port 8000 for server)
    env_url = os.getenv("SUPPORT_ENV_URL", "http://localhost:8000")
    env = SupportEnv(base_url=env_url)
    
    # Run a few episodes on different difficulties
    for difficulty in ["easy", "medium", "hard"]:
        seed = 42
        
        # log_start Equivalent
        print(f"[START] {json.dumps({'task': difficulty, 'env': 'SupportEnv', 'model': MODEL_NAME})}", flush=True)
        
        try:
            with env.sync() as conn:
                result = conn.reset(difficulty=difficulty, seed=seed)
                observation = result.observation
                history: List[str] = []
                rewards: List[float] = []
                steps_taken = 0
                
                for step in range(1, MAX_STEPS + 1):
                    if result.done:
                        break
                    
                    user_prompt = build_user_prompt(step, observation, history)
                    
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
                    except Exception as e:
                        action = FALLBACK_ACTION
                    else:
                        action = parse_model_action(response_text)
                    
                    # conn.step returns a StepResult with reward as an attribute
                    result = conn.step(action)
                    observation = result.observation
                    
                    # log_step Equivalent
                    print(f"[STEP] {json.dumps({'step': step, 'action': action.action_type, 'reward': result.reward, 'done': result.done, 'error': None})}", flush=True)
                    
                    rewards.append(result.reward)
                    steps_taken = step
                    history.append(f"Step {step}: {action.action_type}({action.content[:30]})")
                    
                    if result.done:
                        break
                
                # Final official grade
                try:
                    grader_url = f"{env_url}/grader"
                    session_id = getattr(conn, 'session_id', getattr(result, 'session_id', None))
                    grade_resp = requests.post(grader_url, json={"session_id": session_id})
                    if grade_resp.status_code == 200:
                        grade_data = grade_resp.json()
                        score = grade_data.get('score', 0.0)
                        passed = grade_data.get('passed', False)
                        
                        # log_end Equivalent
                        print(f"[END] {json.dumps({'success': passed, 'steps': steps_taken, 'score': score, 'rewards': rewards})}", flush=True)
                except Exception as e:
                    # In case of grader failure, output minimal end block
                    print(f"[END] {json.dumps({'success': False, 'steps': steps_taken, 'score': 0.0, 'rewards': rewards})}", flush=True)
                    
        except Exception as e:
            # If episode fails to initialize
            print(f"[END] {json.dumps({'success': False, 'steps': 0, 'score': 0.0, 'rewards': []})}", flush=True)

if __name__ == "__main__":
    main()
