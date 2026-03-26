"""
Baseline inference script for SupportEnv.

Runs the baseline agent against all tasks and produces reproducible scores.

Usage:
    python baseline/run_baseline.py
    
Or with OpenAI API (for LLM baseline):
    OPENAI_API_KEY=... python baseline/run_baseline.py --use-llm
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.environment import SupportEnvironment
from baseline.policy import BaselinePolicy
from models import SupportAction


def run_baseline_episode(
    env: SupportEnvironment,
    policy: BaselinePolicy,
    difficulty: str,
    seed: int = 42,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run a single baseline episode.
    
    Args:
        env: Environment instance
        policy: Baseline policy
        difficulty: Task difficulty
        seed: Random seed
        verbose: Print step-by-step output
        
    Returns:
        Episode results
    """
    policy.reset()
    observation = env.reset(seed=seed, difficulty=difficulty)
    
    total_reward = 0.0
    steps = 0
    action_history = []
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Task: {difficulty.upper()}")
        print(f"Ticket: {observation.ticket_subject}")
        print(f"Customer: {observation.customer_name}")
        print(f"Sentiment: {observation.customer_sentiment:.2f}")
        print(f"{'='*60}")
    
    while not observation.done:
        # Get action from policy
        action = policy.act(observation)
        action_history.append({
            "step": steps + 1,
            "action_type": action.action_type,
            "content": action.content[:100]  # Truncate for logging
        })
        
        if verbose:
            print(f"\nStep {steps + 1}:")
            print(f"  Action: {action.action_type}")
            print(f"  Content: {action.content[:80]}...")
        
        # Execute action
        observation = env.step(action)
        reward = observation.reward or 0.0
        total_reward += reward
        steps += 1
        
        if verbose:
            print(f"  Reward: {reward:.4f}")
            print(f"  Message: {observation.message}")
        
        # Safety limit
        if steps > 15:
            if verbose:
                print("  [WARNING] Max steps exceeded")
            break
    
    # Grade episode
    grade_result = env.grade_episode()
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Episode Complete!")
        print(f"Final Score: {grade_result.score:.4f}")
        print(f"Total Reward: {total_reward:.4f}")
        print(f"Steps: {steps}")
        print(f"Passed: {grade_result.passed}")
        print(f"Breakdown: {grade_result.breakdown}")
        print(f"{'='*60}")
    
    return {
        "difficulty": difficulty,
        "score": grade_result.score,
        "total_reward": round(total_reward, 4),
        "steps": steps,
        "passed": grade_result.passed,
        "breakdown": grade_result.breakdown,
        "feedback": grade_result.feedback,
        "action_history": action_history
    }


def run_all_baselines(
    seeds: list = [42, 123, 456],
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run baseline on all tasks with multiple seeds for reproducibility.
    
    Args:
        seeds: List of random seeds to use
        verbose: Print detailed output
        
    Returns:
        Complete baseline results
    """
    results = {
        "easy": [],
        "medium": [],
        "hard": []
    }
    
    policy = BaselinePolicy()
    
    for difficulty in ["easy", "medium", "hard"]:
        print(f"\nRunning {difficulty} task baseline...")
        
        for seed in seeds:
            env = SupportEnvironment()
            episode_result = run_baseline_episode(
                env=env,
                policy=policy,
                difficulty=difficulty,
                seed=seed,
                verbose=verbose
            )
            results[difficulty].append(episode_result)
    
    # Compute aggregates
    summary = {}
    for difficulty in ["easy", "medium", "hard"]:
        scores = [r["score"] for r in results[difficulty]]
        rewards = [r["total_reward"] for r in results[difficulty]]
        
        summary[difficulty] = {
            "avg_score": round(sum(scores) / len(scores), 4),
            "min_score": round(min(scores), 4),
            "max_score": round(max(scores), 4),
            "avg_reward": round(sum(rewards) / len(rewards), 4),
            "pass_rate": sum(1 for r in results[difficulty] if r["passed"]) / len(results[difficulty])
        }
    
    # Overall average
    all_scores = [r["score"] for diff in results.values() for r in diff]
    summary["overall"] = {
        "avg_score": round(sum(all_scores) / len(all_scores), 4)
    }
    
    return {
        "timestamp": datetime.now().isoformat(),
        "seeds": seeds,
        "detailed_results": results,
        "summary": summary
    }


def run_llm_baseline(api_key: str = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Run baseline using OpenAI API.
    
    Args:
        api_key: OpenAI API key (or from env var)
        verbose: Print detailed output
        
    Returns:
        Baseline results
    """
    import openai
    
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")
    
    client = openai.OpenAI(api_key=api_key)
    
    SYSTEM_PROMPT = """You are an expert customer support agent. Your task is to handle customer support tickets effectively.

For each ticket, you must:
1. First CLASSIFY the ticket into one of: billing, technical, account, general
2. Then RESPOND with a helpful, empathetic message
3. Finally RESOLVE the issue or ESCALATE if necessary

IMPORTANT RULES:
- Always show empathy for customer concerns
- Provide clear, actionable solutions
- Escalate only for serious issues (fraud, legal threats, discrimination)
- Keep responses professional and concise

Respond in JSON format:
{
    "action_type": "classify" | "respond" | "escalate" | "resolve",
    "content": "your classification/response/reason"
}
"""

    results = {"easy": [], "medium": [], "hard": []}
    
    for difficulty in ["easy", "medium", "hard"]:
        print(f"\nRunning LLM baseline on {difficulty} task...")
        
        env = SupportEnvironment()
        observation = env.reset(seed=42, difficulty=difficulty)
        
        total_reward = 0.0
        steps = 0
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        while not observation.done and steps < 10:
            # Build user message
            user_msg = f"""TICKET:
Subject: {observation.ticket_subject}
Customer: {observation.customer_name}
Sentiment: {"Angry" if observation.customer_sentiment < -0.3 else "Neutral" if observation.customer_sentiment < 0.3 else "Positive"}

{observation.ticket_text}

Current Status:
- Classified: {observation.is_classified} ({observation.current_classification or 'N/A'})
- Steps remaining: {observation.steps_remaining}
- Available actions: {observation.available_actions}

{observation.message}

What action do you take?"""
            
            messages.append({"role": "user", "content": user_msg})
            
            # Get LLM response
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.3,
                    max_tokens=200
                )
                
                response_text = response.choices[0].message.content
                messages.append({"role": "assistant", "content": response_text})
                
                # Parse action
                action_data = json.loads(response_text)
                action = SupportAction(
                    action_type=action_data["action_type"],
                    content=action_data["content"]
                )
                
            except Exception as e:
                if verbose:
                    print(f"  Error parsing LLM response: {e}")
                # Fallback to simple action
                action = SupportAction(
                    action_type="respond",
                    content="I apologize for the inconvenience. Let me help you with this issue."
                )
            
            if verbose:
                print(f"  Step {steps + 1}: {action.action_type}")
            
            # Execute action
            observation = env.step(action)
            total_reward += observation.reward or 0.0
            steps += 1
        
        # Grade episode
        grade_result = env.grade_episode()
        
        results[difficulty].append({
            "score": grade_result.score,
            "total_reward": round(total_reward, 4),
            "steps": steps,
            "passed": grade_result.passed,
            "breakdown": grade_result.breakdown
        })
        
        print(f"  Score: {grade_result.score:.4f}")
    
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run SupportEnv baseline")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--use-llm", action="store_true", help="Use OpenAI LLM baseline")
    parser.add_argument("--output", "-o", type=str, default="baseline/results.json", help="Output file")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 123, 456], help="Random seeds")
    
    args = parser.parse_args()
    
    print("="*60)
    print("SupportEnv Baseline Runner")
    print("="*60)
    
    if args.use_llm:
        results = run_llm_baseline(verbose=args.verbose)
    else:
        results = run_all_baselines(seeds=args.seeds, verbose=args.verbose)
    
    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {args.output}")
    
    # Print summary
    print("\n" + "="*60)
    print("BASELINE SUMMARY")
    print("="*60)
    
    if "summary" in results:
        for difficulty, stats in results["summary"].items():
            if difficulty == "overall":
                print(f"\nOVERALL: {stats['avg_score']:.4f}")
            else:
                print(f"\n{difficulty.upper()}:")
                print(f"  Average Score: {stats['avg_score']:.4f}")
                print(f"  Score Range: {stats['min_score']:.4f} - {stats['max_score']:.4f}")
                print(f"  Pass Rate: {stats['pass_rate']*100:.1f}%")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()