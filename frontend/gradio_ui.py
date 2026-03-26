"""
Gradio UI for SupportEnv.

Provides interactive interface for:
- Running episodes manually
- Testing baseline agent
- Visualizing rewards and scores
"""

import gradio as gr
import requests
import json
from typing import Dict, Any, Tuple
import os

# Get base URL (local or deployed)
BASE_URL = os.environ.get("SUPPORT_ENV_URL", "http://localhost:8000")


def reset_environment(difficulty: str, seed: int = None) -> Tuple[str, str, str, str, str]:
    """Reset environment and return initial state."""
    try:
        payload = {"difficulty": difficulty}
        if seed:
            payload["seed"] = seed
        
        response = requests.post(f"{BASE_URL}/api/reset", json=payload, timeout=10)
        data = response.json()
        
        obs = data.get("observation", {})
        
        ticket_display = f"""**Subject:** {obs.get('ticket_subject', 'N/A')}
**Customer:** {obs.get('customer_name', 'N/A')}
**Sentiment:** {obs.get('customer_sentiment', 0):.2f}

---

{obs.get('ticket_text', 'No ticket loaded')}
"""
        
        status = f"Session: {data.get('session_id', 'N/A')[:8]}... | Steps Remaining: {obs.get('steps_remaining', 0)}"
        history = "No actions taken yet."
        reward_display = "Cumulative Reward: 0.00"
        message = obs.get("message", "Environment reset successfully.")
        
        # Store session ID in state
        global current_session_id
        current_session_id = data.get("session_id")
        
        return ticket_display, status, history, reward_display, message
    
    except Exception as e:
        return f"Error: {str(e)}", "", "", "", ""


def step_environment(action_type: str, content: str) -> Tuple[str, str, str, str]:
    """Take a step in the environment."""
    try:
        global current_session_id
        
        if not current_session_id:
            return "Please reset the environment first.", "", "", ""
        
        payload = {
            "session_id": current_session_id,
            "action_type": action_type,
            "content": content
        }
        
        response = requests.post(f"{BASE_URL}/api/step", json=payload, timeout=10)
        data = response.json()
        
        obs = data.get("observation", {})
        
        status = f"Steps Remaining: {obs.get('steps_remaining', 0)} | Done: {data.get('done', False)}"
        
        # Format history
        history_items = obs.get("interaction_history", [])
        history = "\n".join([
            f"**{item.get('role', 'unknown').title()}:** {item.get('content', '')}"
            for item in history_items
        ]) or "No interactions yet."
        
        reward = data.get("reward", 0.0) or 0.0
        reward_display = f"Step Reward: {reward:.4f}"
        
        message = obs.get("message", "Action executed.")
        
        return status, history, reward_display, message
    
    except Exception as e:
        return f"Error: {str(e)}", "", "", ""


def grade_current_episode() -> str:
    """Grade the current episode."""
    try:
        global current_session_id
        
        if not current_session_id:
            return "No active session. Please reset and run an episode first."
        
        payload = {"session_id": current_session_id}
        response = requests.post(f"{BASE_URL}/grader", json=payload, timeout=10)
        data = response.json()
        
        result = f"""## Grading Results

**Final Score:** {data.get('score', 0):.4f}
**Passed:** {'✅ Yes' if data.get('passed', False) else '❌ No'}

### Breakdown:
"""
        for key, value in data.get("breakdown", {}).items():
            result += f"- **{key.replace('_', ' ').title()}:** {value:.4f}\n"
        
        result += f"\n### Feedback:\n{data.get('feedback', 'No feedback available.')}"
        
        return result
    
    except Exception as e:
        return f"Error grading episode: {str(e)}"


def run_baseline_demo() -> str:
    """Run baseline and display results."""
    try:
        response = requests.get(f"{BASE_URL}/baseline", timeout=60)
        data = response.json()
        
        result = "## Baseline Results\n\n"
        
        for difficulty in ["easy", "medium", "hard"]:
            diff_data = data.get("baseline_results", {}).get(difficulty, {})
            result += f"""### {difficulty.upper()} Task
- **Score:** {diff_data.get('score', 0):.4f}
- **Total Reward:** {diff_data.get('total_reward', 0):.4f}
- **Steps:** {diff_data.get('steps', 0)}
- **Passed:** {'✅' if diff_data.get('passed', False) else '❌'}

"""
        
        summary = data.get("summary", {})
        result += f"""---
### Summary
- Easy: {summary.get('easy_score', 0):.4f}
- Medium: {summary.get('medium_score', 0):.4f}
- Hard: {summary.get('hard_score', 0):.4f}
- **Average: {summary.get('average_score', 0):.4f}**
"""
        
        return result
    
    except Exception as e:
        return f"Error running baseline: {str(e)}"


def get_tasks_info() -> str:
    """Get available tasks information."""
    try:
        response = requests.get(f"{BASE_URL}/tasks", timeout=10)
        data = response.json()
        
        result = "## Available Tasks\n\n"
        
        for task in data.get("tasks", []):
            result += f"""### {task.get('name', 'Unknown')} ({task.get('difficulty', 'unknown').upper()})
**Task ID:** `{task.get('task_id', 'N/A')}`
**Max Steps:** {task.get('max_steps', 0)}

{task.get('description', 'No description available.')}

---
"""
        
        return result
    
    except Exception as e:
        return f"Error fetching tasks: {str(e)}"


# Global state
current_session_id = None


def create_gradio_interface():
    """Create the Gradio interface."""
    
    with gr.Blocks(title="SupportEnv - Customer Support RL Environment") as demo:
        gr.Markdown("""
# 🎧 SupportEnv - Customer Support RL Environment

An OpenEnv environment for training AI agents on customer support workflows.
        """)
        
        with gr.Tabs():
            # Interactive Tab
            with gr.TabItem("🎮 Interactive"):
                with gr.Row():
                    with gr.Column(scale=2):
                        ticket_display = gr.Markdown(
                            value="Click 'Reset Environment' to start.",
                            label="Current Ticket"
                        )
                        status_display = gr.Textbox(
                            label="Status",
                            interactive=False
                        )
                        message_display = gr.Textbox(
                            label="Last Message",
                            interactive=False
                        )
                    
                    with gr.Column(scale=1):
                        difficulty_dropdown = gr.Dropdown(
                            choices=["easy", "medium", "hard"],
                            value="easy",
                            label="Task Difficulty"
                        )
                        seed_input = gr.Number(
                            value=42,
                            label="Random Seed",
                            precision=0
                        )
                        reset_btn = gr.Button("🔄 Reset Environment", variant="primary")
                
                gr.Markdown("### Take Action")
                
                with gr.Row():
                    action_type = gr.Dropdown(
                        choices=["classify", "respond", "escalate", "request_info", "resolve"],
                        value="classify",
                        label="Action Type"
                    )
                    action_content = gr.Textbox(
                        label="Content",
                        placeholder="Enter classification, response, or reason..."
                    )
                
                step_btn = gr.Button("▶️ Execute Action", variant="secondary")
                
                with gr.Row():
                    history_display = gr.Markdown(
                        value="No history yet.",
                        label="Interaction History"
                    )
                    reward_display = gr.Textbox(
                        label="Reward",
                        interactive=False
                    )
                
                grade_btn = gr.Button("📊 Grade Episode")
                grade_output = gr.Markdown(label="Grading Results")
                
                # Connect events
                reset_btn.click(
                    reset_environment,
                    inputs=[difficulty_dropdown, seed_input],
                    outputs=[ticket_display, status_display, history_display, reward_display, message_display]
                )
                
                step_btn.click(
                    step_environment,
                    inputs=[action_type, action_content],
                    outputs=[status_display, history_display, reward_display, message_display]
                )
                
                grade_btn.click(
                    grade_current_episode,
                    outputs=[grade_output]
                )
            
            # Baseline Tab
            with gr.TabItem("🤖 Baseline"):
                gr.Markdown("""
### Run Baseline Agent

This runs the rule-based baseline agent against all three difficulty levels
and shows reproducible scores.
                """)
                
                baseline_btn = gr.Button("🚀 Run Baseline", variant="primary")
                baseline_output = gr.Markdown()
                
                baseline_btn.click(
                    run_baseline_demo,
                    outputs=[baseline_output]
                )
            
            # Tasks Tab
            with gr.TabItem("📋 Tasks"):
                tasks_btn = gr.Button("📖 Load Tasks Info")
                tasks_output = gr.Markdown()
                
                tasks_btn.click(
                    get_tasks_info,
                    outputs=[tasks_output]
                )
            
            # About Tab
            with gr.TabItem("ℹ️ About"):
                gr.Markdown("""
## About SupportEnv

**SupportEnv** is a production-grade reinforcement learning environment 
that simulates customer support workflows.

### Features
- 🎯 3 difficulty levels: Easy, Medium, Hard
- 📊 Deterministic grading with scores 0.0-1.0
- 💰 Dense reward signals for learning
- 🔄 Full OpenEnv API compliance
- 🐳 Containerized deployment

### Action Space
- `classify`: Categorize the ticket (billing, technical, account, general)
- `respond`: Send a response to the customer
- `escalate`: Escalate to human agent
- `request_info`: Ask for more information
- `resolve`: Mark ticket as resolved

### Observation Space
- Ticket text and metadata
- Customer sentiment (-1 to 1)
- Interaction history
- Current classification status
- Steps remaining

### Reward Structure
- Correct classification: +0.25
- Good response: +0.30
- Correct escalation: +0.35
- Resolution bonus: +0.40
- Penalties for harmful/incorrect actions

### Links
- [OpenEnv Documentation](https://openenv.dev)
- [GitHub Repository](https://github.com/username/support-env)
                """)
    
    return demo


if __name__ == "__main__":
    demo = create_gradio_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860)