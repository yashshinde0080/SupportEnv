import os
import re
import json
import textwrap
import asyncio
from typing import List, Optional

from openai import OpenAI
from client import SupportEnv
from models import SupportAction, SupportObservation

# Environment variables from mandate
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME", "support-env-local")
TASK_NAME = os.getenv("SUPPORT_ENV_TASK", "customer-support")
BENCHMARK = os.getenv("SUPPORT_ENV_BENCHMARK", "support_env")

MAX_STEPS = 10
TEMPERATURE = 0.2
MAX_TOKENS = 500
SUCCESS_SCORE_THRESHOLD = 0.5

# Fallback in case model fails or gives invalid action
FALLBACK_ACTION = SupportAction(action_type="respond", content="I apologize, but I am unable to process your request at this time.", confidence=0.0)

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
    - escalate: Escalate to a human agent if you cannot solve it.
    - resolve: Close the ticket when the issue is fully addressed.
    
    Wait for the environment to respond after each action.
    Do not include explanations or any other text.
    """
).strip()

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

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
                confidence=data.get("confidence", 1.0)
            )
        return FALLBACK_ACTION
    except Exception:
        return FALLBACK_ACTION

def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    env_url = os.getenv("SUPPORT_ENV_URL", "http://localhost:7860")
    env = SupportEnv(base_url=env_url)
    
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    
    difficulty = os.getenv("SUPPORT_ENV_DIFFICULTY", "medium")
    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
    
    try:
        with env.sync() as conn:
            result = conn.reset(difficulty=difficulty, seed=42)
            observation = result.observation
            
            for step in range(1, MAX_STEPS + 1):
                if result.done:
                    break
                
                user_prompt = build_user_prompt(step, observation, history)
                
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
                
                error = None
                action = FALLBACK_ACTION
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
                    error = str(e)
                
                action_str = f"{action.action_type}(\"{action.content}\")"
                
                try:
                    result = conn.step(action)
                    observation = result.observation
                    reward = result.reward or 0.0
                    done = result.done
                except Exception as e:
                    error = str(e)
                    reward = 0.0
                    done = True
                
                rewards.append(reward)
                steps_taken = step
                
                log_step(step=step, action=action_str, reward=reward, done=done, error=error)
                history.append(f"Step {step}: {action_str} -> Reward: {reward:.2f}")
                
                if done:
                    break
            
            # Fetch final grade from /grader
            import requests
            try:
                grader_url = f"{env_url}/grader"
                session_id = getattr(conn, 'session_id', getattr(result, 'session_id', None))
                if session_id:
                    grade_resp = requests.post(grader_url, json={"session_id": session_id})
                    if grade_resp.status_code == 200:
                        grade_data = grade_resp.json()
                        score = grade_data.get('score', 0.0)
                        success = grade_data.get('passed', False)
                    else:
                        score = sum(rewards) / MAX_STEPS
                        score = max(0.0, min(1.0, score))
                        success = score >= SUCCESS_SCORE_THRESHOLD
                else:
                    score = sum(rewards) / MAX_STEPS
                    score = max(0.0, min(1.0, score))
                    success = score >= SUCCESS_SCORE_THRESHOLD
            except Exception:
                score = sum(rewards) / MAX_STEPS
                score = max(0.0, min(1.0, score))
                success = score >= SUCCESS_SCORE_THRESHOLD
                
    except Exception as e:
        # Catch unexpected errors during setup
        pass
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    main()
