import os

with open('frontend/gradio_ui.py', 'w', encoding='utf-8') as f:
    f.write('''"""
Gradio UI for SupportEnv.

Provides interactive interface for:
- Running episodes manually
- Testing baseline agent
- Visualizing rewards and scores
- Real-time metrics and analytics
"""

import gradio as gr
import requests
import json
from typing import Dict, Any, Tuple, List, Optional
import os

# Get base URL (local or deployed)
BASE_URL = os.environ.get("SUPPORT_ENV_URL", "http://localhost:8001")

# Validation constants
MAX_CONTENT_LENGTH = 5000
MIN_CONTENT_LENGTH = 1
VALID_ACTION_TYPES = ["classify", "respond", "escalate", "request_info", "resolve", "lookup_kb"]
VALID_DIFFICULTIES = ["easy", "medium", "hard"]
VALID_CATEGORIES = ["billing", "technical", "account", "general", "urgent", "feature_request"]
REQUEST_TIMEOUT = 30
BASELINE_TIMEOUT = 120


# ─────────────────────────────────────────────────────────────────────────────
# Validation & Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def validate_content(content: str, min_len: int = MIN_CONTENT_LENGTH, max_len: int = MAX_CONTENT_LENGTH) -> Tuple[bool, str]:
    if not content or not content.strip():
        return False, "⚠️ Content cannot be empty."
    if len(content) > max_len:
        return False, f"⚠️ Content exceeds maximum length of {max_len} characters."
    if len(content) < min_len:
        return False, f"⚠️ Content must be at least {min_len} characters."
    return True, "✅ Valid"


def validate_action_type(action_type: str) -> Tuple[bool, str]:
    if action_type not in VALID_ACTION_TYPES:
        return False, f"⚠️ Invalid action type. Must be one of: {', '.join(VALID_ACTION_TYPES)}"
    return True, "✅ Valid"


def validate_difficulty(difficulty: str) -> Tuple[bool, str]:
    if difficulty not in VALID_DIFFICULTIES:
        return False, f"⚠️ Invalid difficulty. Must be one of: {', '.join(VALID_DIFFICULTIES)}"
    return True, "✅ Valid"


def validate_seed(seed: Optional[int]) -> Tuple[bool, str]:
    if seed is None:
        return True, "ℹ️ No seed specified (will use random)"
    if not isinstance(seed, int) or seed < 0:
        return False, "⚠️ Seed must be a non-negative integer."
    if seed > 2**32 - 1:
        return False, "⚠️ Seed value too large (max: 4294967295)"
    return True, "✅ Valid"


def format_sentiment(sentiment: float) -> Tuple[str, str]:
    if sentiment >= 0.5:
        return f"{sentiment:+.2f} 😊", "positive"
    elif sentiment >= 0.1:
        return f"{sentiment:+.2f} 🙂", "neutral-positive"
    elif sentiment >= -0.1:
        return f"{sentiment:+.2f} 😐", "neutral"
    elif sentiment >= -0.5:
        return f"{sentiment:+.2f} 🙁", "neutral-negative"
    else:
        return f"{sentiment:+.2f} 😠", "negative"


def format_step_reward(reward: float) -> Tuple[str, str]:
    if reward >= 0.3:
        return f"+{reward:.4f} ⭐", "excellent"
    elif reward > 0:
        return f"+{reward:.4f} ✓", "positive"
    elif reward == 0:
        return f"{reward:.4f} ○", "neutral"
    else:
        return f"{reward:.4f} ✗", "negative"


def get_action_description(action_type: str) -> str:
    descriptions = {
        "classify": "📋 Categorize the ticket into: billing, technical, account, general, urgent, or feature_request",
        "respond": "💬 Send a helpful response to the customer's inquiry",
        "escalate": "⬆️ Transfer the ticket to a human agent when needed",
        "request_info": "❓ Ask the customer for additional information or clarification",
        "resolve": "✅ Mark the ticket as resolved when the issue is fully addressed",
        "lookup_kb": "🔍 Search the knowledge base for answers."
    }
    return descriptions.get(action_type, "Unknown action type")


def get_difficulty_info(difficulty: str) -> str:
    info = {
        "easy": "🟢 Simple inquiry with clear intent. Single-turn resolution expected.",
        "medium": "🟡 Multi-faceted issue requiring investigation. May need 2-3 interactions.",
        "hard": "🔴 Complex scenario with multiple issues or frustrated customer. Requires careful handling."
    }
    return info.get(difficulty, "Unknown difficulty level")


def validate_action_for_type(action_type: str, content: str) -> Tuple[bool, str]:
    is_valid, msg = validate_content(content)
    if not is_valid:
        return is_valid, msg

    content_lower = content.lower().strip()

    if action_type == "classify":
        found_category = False
        for category in VALID_CATEGORIES:
            if category in content_lower:
                found_category = True
                break
        if not found_category:
            return False, f"⚠️ Classification must include a category: {', '.join(VALID_CATEGORIES)}"
        return True, "✅ Valid classification"

    elif action_type == "respond":
        if len(content) < 10:
            return False, "⚠️ Response should be at least 10 characters for meaningful communication."
        return True, "✅ Valid response"

    elif action_type == "escalate":
        if len(content) < 15:
            return False, "⚠️ Escalation reason should explain why (min 15 chars)."
        return True, "✅ Valid escalation"

    elif action_type == "request_info":
        if "?" not in content and not any(word in content_lower for word in ["please", "could", "would", "can you"]):
            return False, "⚠️ Request should be polite and/or contain a question."
        return True, "✅ Valid request"

    elif action_type == "resolve":
        if not any(word in content_lower for word in ["resolved", "complete", "fixed", "solved", "addressed"]):
            return False, "⚠️ Resolution should indicate the issue is addressed."
        return True, "✅ Valid resolution"

    return True, "✅ Valid"


# ─────────────────────────────────────────────────────────────────────────────
# Environment Interaction Functions
# ─────────────────────────────────────────────────────────────────────────────

# Global state
current_session_id = None
cumulative_reward = 0.0
step_count = 0
reward_history = []

def reset_environment(difficulty: str, seed: int = None) -> Tuple[str, str, str, str, str, str]:
    global current_session_id, cumulative_reward, step_count, reward_history
    try:
        cumulative_reward = 0.0
        step_count = 0
        reward_history = []

        is_valid, msg = validate_difficulty(difficulty)
        if not is_valid:
            return f"⚠️ {msg}", "", "", "", "", "Validation Error"

        is_valid, msg = validate_seed(seed)
        if not is_valid:
            return f"⚠️ {msg}", "", "", "", "", "Validation Error"

        payload = {"difficulty": difficulty}
        if seed is not None:
            payload["seed"] = int(seed)

        response = requests.post(f"{BASE_URL}/api/reset", json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        obs = data.get("observation", {})
        current_session_id = data.get("session_id")

        sentiment_val = obs.get("customer_sentiment", 0)
        sentiment_label = "Positive 😊" if sentiment_val >= 0.5 else "Neutral 😐" if sentiment_val >= -0.1 else "Negative 😠"

        ticket_display = f"""
## 📬 {obs.get("ticket_subject", "General Support Inquiry")}
**Level:** {difficulty.upper()}  |  **Customer:** {obs.get("customer_name", "Client")}  |  **Sentiment:** {sentiment_label}

> {obs.get("ticket_text", "No ticket content loaded")}

**Challenge Profile:** {get_difficulty_info(difficulty)}
"""

        session_id = current_session_id or "N/A"
        session_short = session_id[:8] if session_id != "N/A" else "None"
        status = f"CONNECTED: {session_short} | PHASE: INITIALIZED"
        message = "✅ Environment successfully reset for new episode."
        
        history = "Awaiting first interaction..."
        reward_display = "**Cumulative Reward:** `0.000`"
        action_hint = f"💡 {get_action_description('classify')}"

        return ticket_display, status, history, reward_display, message, action_hint

    except Exception as e:
        return f"❌ Error: {str(e)}", "", "", "", f"System Error: {e}", ""


def step_environment(action_type: str, content: str) -> Tuple[str, str, str, str, str]:
    global current_session_id, cumulative_reward, step_count, reward_history
    try:
        if not current_session_id:
            return "⚠️ Please reset the environment first.", "", "", "🚫 No Session", "Select action"

        is_val, msg = validate_action_type(action_type)
        if not is_val: return msg, "", "", "🚫 Invalid Action", ""
        is_val, msg = validate_content(content)
        if not is_val: return msg, "", "", "🚫 Invalid Content", ""

        payload = {
            "session_id": current_session_id,
            "action_type": action_type,
            "content": content
        }

        response = requests.post(f"{BASE_URL}/api/step", json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        obs = data.get("observation", {})
        reward = data.get("reward", 0.0) or 0.0
        done = data.get("done", False)
        
        step_count += 1
        cumulative_reward += reward
        reward_history.append(reward)

        steps_total = obs.get("max_steps", step_count + obs.get("steps_remaining", 0))
        status = f"{'🏁 COMPLETE' if done else '🎮 ACTIVE'} | STEP: {step_count}/{steps_total}"

        history_items = obs.get("interaction_history", [])
        if history_items:
            history_parts = []
            for item in history_items:
                role = item.get("role", "unknown").capitalize()
                history_parts.append(f"**{role}**: {item.get('content', '')}")
            history = "\n\n---\n\n".join(history_parts)
        else:
            history = "No interactions logged."

        reward_formatted, _ = format_step_reward(reward)
        reward_display = f"""
**Cumulative Reward:** `{cumulative_reward:+.3f}`  
**Last Action Reward:** `{reward_formatted}`
"""

        message = obs.get("message", "Action processed.")
        next_hint = f"💡 {get_action_description(action_type)}"

        return status, history, reward_display, message, next_hint

    except Exception as e:
        return f"❌ Error: {str(e)}", "", "", "Unexpected Error", ""


def grade_current_episode() -> str:
    try:
        global current_session_id
        if not current_session_id:
            return "❌ **No Active Session**. Please reset the environment and run an episode first."

        payload = {"session_id": current_session_id}
        response = requests.post(f"{BASE_URL}/grader", json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        score = data.get("score", 0.0)
        passed = data.get("passed", False)
        
        result = f"""
## {'🏆' if passed else '💪'} {data.get("message", "Assessment Complete")}
### **Status:** {'✅ PASSED' if passed else '❌ FAILED'}  |  **Score:** `{score:.2f}`

> *{data.get("feedback", "No specific feedback available.")}*

---
### 📊 Performance Breakdown
"""

        breakdown = data.get("breakdown", {})
        if breakdown:
            for key, value in breakdown.items():
                label = key.replace("_", " ").title()
                result += f"- **{label}:** `{value:.2f}`\n"
        else:
            result += "Detailed metrics not available for this session."

        return result

    except Exception as e:
        return f"❌ Error grading episode: {str(e)}"


def run_baseline_demo(baseline_diff: str = "easy") -> str:
    try:
        response = requests.get(f"{BASE_URL}/baseline", timeout=BASELINE_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        result = "## 🤖 Baseline Agent Results\n*Running rule-based baseline agent across all difficulty levels...*\n\n---\n\n"

        for difficulty in ["easy", "medium", "hard"]:
            diff_data = data.get("baseline_results", {}).get(difficulty, {})
            score = diff_data.get("score", 0.0)
            passed = diff_data.get("passed", False)
            diff_icon = "🟢" if difficulty == "easy" else "🟡" if difficulty == "medium" else "🔴"

            result += f"""
### {diff_icon} {difficulty.upper()} Task
- **Status:** {'✅ Passed' if passed else '❌ Failed'}
- **Score:** `{score:.4f}`
- **Total Reward:** `{diff_data.get('total_reward', 0):.4f}`
- **Steps Taken:** `{diff_data.get('steps', 0)}`
"""

        summary = data.get("summary", {})
        avg_score = summary.get("average_score", 0.0)

        result += f"""
---
## 📊 Summary Overview
- 🟢 Easy: `{summary.get('easy_score', 0):.4f}`
- 🟡 Medium: `{summary.get('medium_score', 0):.4f}`
- 🔴 Hard: `{summary.get('hard_score', 0):.4f}`

### 🎯 Average Score: `{avg_score:.4f}`
"""
        return result

    except Exception as e:
        return f"❌ Error running baseline: {str(e)}"


def get_tasks_info() -> str:
    try:
        response = requests.get(f"{BASE_URL}/tasks", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        tasks = data.get("tasks", [])
        if not tasks:
            return "📋 **No tasks available at this time.**"

        result = "## 📋 Available Tasks\n\n"

        for task in tasks:
            difficulty = task.get("difficulty", "unknown")
            diff_icon = "🟢" if difficulty == "easy" else "🟡" if difficulty == "medium" else "🔴"
            
            schema = task.get("action_schema", {})
            schema_json = json.dumps(schema, indent=2)

            result += f"""
### {diff_icon} {task.get("name", "Unknown")}
**Task ID:** `{task.get("task_id", "N/A")}`  |  **Max Steps:** {task.get("max_steps", 0)}

{task.get("description", "No description available.")}

<details><summary><b>Show Action Schema</b></summary>
```json
{schema_json}
```
</details>
---
"""
        return result

    except Exception as e:
        return f"❌ Error fetching tasks: {str(e)}"


def get_metrics() -> str:
    try:
        response = requests.get(f"{BASE_URL}/metrics", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        result = "## 📈 Environment Metrics\n\n"

        total = data.get("total_episodes", 0)
        success_rate = data.get("success_rate", 0)
        
        result += f"""
### 🎮 Total Episodes: `{total}`
**Success Rate:** `{success_rate:.1%}`

"""
        for diff in ["easy", "medium", "hard"]:
            diff_score = data.get(f"avg_{diff}_score", 0)
            diff_icon = "🟢" if diff == "easy" else "🟡" if diff == "medium" else "🔴"
            result += f"- {diff_icon} **{diff.upper()} AVG:** `{diff_score:.4f}`\n"
            
        return result
    except Exception as e:
        return f"❌ Error fetching metrics: {str(e)}"


def create_gradio_interface():
    with gr.Blocks(title="SupportEnv Dashboard") as demo:
        
        gr.Markdown("""
        # 🎧 SupportEnv PRO
        A reinforcement learning environment for customer support automation.
        """)

        with gr.Tabs():
            with gr.TabItem("🎮 Interactive Agent"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### ⚙️ Session Config")
                        difficulty_dropdown = gr.Dropdown(
                            choices=["easy", "medium", "hard"],
                            value="easy",
                            label="Target Difficulty"
                        )
                        seed_input = gr.Number(
                            value=42,
                            label="Environment Seed",
                            precision=0
                        )
                        reset_btn = gr.Button("🔄 Initialize Environment", variant="primary")
                        
                        gr.Markdown("---")
                        gr.Markdown("### 📊 Live Metrics")
                        status_display = gr.Textbox(label="Current Status", interactive=False)
                        message_display = gr.Textbox(label="System Feedback", interactive=False)

                    with gr.Column(scale=3):
                        gr.Markdown("### 📬 Active Support Ticket")
                        ticket_display = gr.Markdown("No Active Session.")
                        
                        gr.Markdown("### �� Action Control")
                        action_hint = gr.Markdown("💡 Select an action type...")
                        with gr.Row():
                            with gr.Column(scale=1):
                                action_type = gr.Dropdown(
                                    choices=["classify", "respond", "escalate", "request_info", "resolve"],
                                    value="classify",
                                    label="Action Type"
                                )
                            with gr.Column(scale=3):
                                action_content = gr.Textbox(label="Action Content", lines=3)
                                with gr.Row():
                                    clear_btn = gr.Button("🧹 Clear")
                                    step_btn = gr.Button("🚀 Execute Action", variant="primary")

                        gr.Markdown("### 📜 Session History")
                        with gr.Row():
                            with gr.Column(scale=4):
                                history_display = gr.Markdown("No interactions yet.")
                            with gr.Column(scale=1):
                                reward_display = gr.Markdown("**Cumulative Reward:** `0.000`")

            with gr.TabItem("📊 Evaluation Report"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 🔍 Agent Assessment")
                        grade_btn = gr.Button("🏆 Final Evaluation", variant="primary")
                    with gr.Column(scale=3):
                        grade_output = gr.Markdown("Complete an episode and click evaluate.")

            with gr.TabItem("📚 Benchmarks"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 🏁 Baseline Tests")
                        baseline_diff = gr.Dropdown(
                            choices=["easy", "medium", "hard"],
                            value="easy",
                            label="Test Difficulty"
                        )
                        baseline_btn = gr.Button("🏃 Run Benchmark")
                        gr.Markdown("---")
                        tasks_btn = gr.Button("🔍 Refresh Tasks")
                    
                    with gr.Column(scale=3):
                        with gr.Tabs():
                            with gr.TabItem("📋 Task Repository"):
                                tasks_display = gr.Markdown("Click 'Refresh Tasks'.")
                            with gr.TabItem("🔬 Benchmark Results"):
                                baseline_output = gr.Markdown("Results will appear here.")

            with gr.TabItem("📈 Metrics"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📉 System Stats")
                        metrics_btn = gr.Button("🔄 Refresh Metrics")
                    with gr.Column(scale=3):
                        metrics_display = gr.Markdown("Click 'Refresh Metrics'.")

        reset_btn.click(
            reset_environment,
            inputs=[difficulty_dropdown, seed_input],
            outputs=[ticket_display, status_display, history_display, reward_display, message_display, action_hint]
        )
        
        step_btn.click(
            step_environment,
            inputs=[action_type, action_content],
            outputs=[status_display, history_display, reward_display, message_display, action_hint]
        )
        
        grade_btn.click(grade_current_episode, outputs=[grade_output])
        tasks_btn.click(get_tasks_info, outputs=[tasks_display])
        metrics_btn.click(get_metrics, outputs=[metrics_display])
        baseline_btn.click(run_baseline_demo, inputs=[baseline_diff], outputs=[baseline_output])
        clear_btn.click(lambda: "", outputs=[action_content])
        
    return demo

if __name__ == "__main__":
    demo = create_gradio_interface()
    # Explicit syntax ensures it binds to 0.0.0.0
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True)
''')
    
print("Re-written frontend/gradio_ui.py to use standard Gradio components instead of custom HTML/CSS")
