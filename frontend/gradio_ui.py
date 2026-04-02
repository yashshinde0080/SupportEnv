"""
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
from datetime import datetime

# Get base URL (local or deployed)
BASE_URL = os.environ.get("SUPPORT_ENV_URL", "http://localhost:8000")

# Validation constants
MAX_CONTENT_LENGTH = 5000
MIN_CONTENT_LENGTH = 1
VALID_ACTION_TYPES = ["classify", "respond", "escalate", "request_info", "resolve"]
VALID_DIFFICULTIES = ["easy", "medium", "hard"]
VALID_CATEGORIES = ["billing", "technical", "account", "general", "urgent", "feature_request"]
REQUEST_TIMEOUT = 30
BASELINE_TIMEOUT = 120


# ─────────────────────────────────────────────────────────────────────────────
# Validation & Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def validate_content(content: str, min_len: int = MIN_CONTENT_LENGTH, max_len: int = MAX_CONTENT_LENGTH) -> Tuple[bool, str]:
    """Validate content length and return status."""
    if not content or not content.strip():
        return False, "⚠️ Content cannot be empty."
    if len(content) > max_len:
        return False, f"⚠️ Content exceeds maximum length of {max_len} characters."
    if len(content) < min_len:
        return False, f"⚠️ Content must be at least {min_len} characters."
    return True, "✅ Valid"


def validate_action_type(action_type: str) -> Tuple[bool, str]:
    """Validate action type."""
    if action_type not in VALID_ACTION_TYPES:
        return False, f"⚠️ Invalid action type. Must be one of: {', '.join(VALID_ACTION_TYPES)}"
    return True, "✅ Valid"


def validate_difficulty(difficulty: str) -> Tuple[bool, str]:
    """Validate difficulty level."""
    if difficulty not in VALID_DIFFICULTIES:
        return False, f"⚠️ Invalid difficulty. Must be one of: {', '.join(VALID_DIFFICULTIES)}"
    return True, "✅ Valid"


def validate_seed(seed: Optional[int]) -> Tuple[bool, str]:
    """Validate random seed value."""
    if seed is None:
        return True, "ℹ️ No seed specified (will use random)"
    if not isinstance(seed, int) or seed < 0:
        return False, "⚠️ Seed must be a non-negative integer."
    if seed > 2**32 - 1:
        return False, "⚠️ Seed value too large (max: 4294967295)"
    return True, "✅ Valid"


def format_sentiment(sentiment: float) -> Tuple[str, str]:
    """Format sentiment with emoji indicator."""
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
    """Format reward with color indicator."""
    if reward >= 0.3:
        return f"+{reward:.4f} ⭐", "excellent"
    elif reward > 0:
        return f"+{reward:.4f} ✓", "positive"
    elif reward == 0:
        return f"{reward:.4f} ○", "neutral"
    else:
        return f"{reward:.4f} ✗", "negative"


def get_action_description(action_type: str) -> str:
    """Get helpful description for each action type."""
    descriptions = {
        "classify": "📋 Categorize the ticket into: billing, technical, account, general, urgent, or feature_request",
        "respond": "💬 Send a helpful response to the customer's inquiry",
        "escalate": "⬆️ Transfer the ticket to a human agent when needed",
        "request_info": "❓ Ask the customer for additional information or clarification",
        "resolve": "✅ Mark the ticket as resolved when the issue is fully addressed"
    }
    return descriptions.get(action_type, "Unknown action type")


def get_difficulty_info(difficulty: str) -> str:
    """Get detailed information about difficulty levels."""
    info = {
        "easy": "🟢 Simple inquiry with clear intent. Single-turn resolution expected.",
        "medium": "🟡 Multi-faceted issue requiring investigation. May need 2-3 interactions.",
        "hard": "🔴 Complex scenario with multiple issues or frustrated customer. Requires careful handling."
    }
    return info.get(difficulty, "Unknown difficulty level")


def validate_action_for_type(action_type: str, content: str) -> Tuple[bool, str]:
    """Validate content based on action type."""
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

def reset_environment(difficulty: str, seed: int = None) -> Tuple[str, str, str, str, str, str, str]:
    """Reset environment and return initial state with full validation."""
    try:
        # Validate inputs
        is_valid, msg = validate_difficulty(difficulty)
        if not is_valid:
            return f"⚠️ {msg}", "", "", "", "", "", "Validation Error"

        is_valid, msg = validate_seed(seed)
        if not is_valid:
            return f"⚠️ {msg}", "", "", "", "", "", "Validation Error"

        payload = {"difficulty": difficulty}
        if seed:
            payload["seed"] = seed

        response = requests.post(f"{BASE_URL}/api/reset", json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        obs = data.get("observation", {})

        # Format sentiment with emoji
        sentiment_val = obs.get('customer_sentiment', 0)
        sentiment_formatted, sentiment_category = format_sentiment(sentiment_val)

        # Get difficulty info
        difficulty_info = get_difficulty_info(difficulty)

        ticket_display = f"""
<div style="padding: 10px; border-left: 4px solid {'#22c55e' if sentiment_val > 0.1 else '#ef4444' if sentiment_val < -0.1 else '#eab308'}; background: {'#f0fdf4' if sentiment_val > 0.1 else '#fef2f2' if sentiment_val < -0.1 else '#fefce8'};">

### 📬 Ticket Details

| Field | Value |
|-------|-------|
| **Subject** | {obs.get('ticket_subject', 'N/A')} |
| **Customer** | {obs.get('customer_name', 'N/A')} |
| **Sentiment** | {sentiment_formatted} |
| **Difficulty** | {difficulty.upper()} |

---

**{difficulty_info}**

---

### 📝 Ticket Content

{obs.get('ticket_text', 'No ticket loaded')}

</div>
"""

        session_id = data.get('session_id', 'N/A')
        session_display = session_id[:8] if session_id != 'N/A' else 'N/A'
        status = f"""🆔 Session: `{session_display}...` | 📊 Steps Remaining: {obs.get('steps_remaining', 0)} | 🎯 Difficulty: {difficulty.upper()}"""
        history = "📜 *No actions taken yet.*"

        # Enhanced reward display
        reward_display = """
📊 **Reward Tracker**
━━━━━━━━━━━━━━━━━━━━━
│ Step Reward:    `0.0000`
│ Cumulative:     `0.0000`
│ Average:        `0.0000`
━━━━━━━━━━━━━━━━━━━━━
"""
        message = "✅ Environment reset successfully. Ready to begin!"

        # Store session ID in state
        global current_session_id
        current_session_id = data.get("session_id")

        # Action hint
        action_hint = f"💡 {get_action_description('classify')}"

        return ticket_display, status, history, reward_display, message, action_hint, "✅ Ready"

    except requests.exceptions.Timeout:
        return "⏱️ Request timed out. Please try again.", "", "", "", "", "", "Timeout Error"
    except requests.exceptions.ConnectionError:
        return "🔌 Connection failed. Is the server running?", "", "", "", "", "", "Connection Error"
    except requests.exceptions.HTTPError as e:
        return f"🚫 HTTP Error {e.response.status_code}: {str(e)}", "", "", "", "", "", "HTTP Error"
    except Exception as e:
        return f"❌ Error: {str(e)}", "", "", "", "", "", "Unexpected Error"


def step_environment(action_type: str, content: str) -> Tuple[str, str, str, str, str, str]:
    """Take a step in the environment with full validation."""
    try:
        global current_session_id

        # Validate session
        if not current_session_id:
            return "⚠️ Please reset the environment first.", "", "", "", "🚫 No Session", "Select an action to begin"

        # Validate action type
        is_valid, msg = validate_action_type(action_type)
        if not is_valid:
            return msg, "", "", "", "🚫 Validation Failed", get_action_description(action_type)

        # Validate content
        is_valid, msg = validate_content(content)
        if not is_valid:
            return msg, "", "", "", "🚫 Validation Failed", get_action_description(action_type)

        # Validate action for specific type
        is_valid, msg = validate_action_for_type(action_type, content)
        if not is_valid:
            return msg, "", "", "", "🚫 Validation Failed", get_action_description(action_type)

        payload = {
            "session_id": current_session_id,
            "action_type": action_type,
            "content": content
        }

        response = requests.post(f"{BASE_URL}/api/step", json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        obs = data.get("observation", {})

        # Enhanced status display
        steps_remaining = obs.get('steps_remaining', 0)
        done = data.get('done', False)
        status_icon = "🏁" if done else "🎮"
        status = f"""{status_icon} Steps Remaining: {steps_remaining} | Episode Done: {done}"""

        # Format history with styling
        history_items = obs.get("interaction_history", [])
        if history_items:
            history_parts = []
            for i, item in enumerate(history_items, 1):
                role = item.get('role', 'unknown').title()
                content_item = item.get('content', '')
                role_color = "#3b82f6" if role == "Agent" else "#22c55e" if role == "Customer" else "#6b7280"
                history_parts.append(f'<div style="padding: 8px; margin: 4px 0; border-left: 3px solid {role_color}; background: #f9fafb;">**{i}. {role}:** {content_item}</div>')
            history = "\n".join(history_parts)
        else:
            history = "📜 *No interactions yet.*"

        # Enhanced reward display
        reward = data.get("reward", 0.0) or 0.0
        reward_formatted, reward_category = format_step_reward(reward)

        # Track cumulative (would need state management for real tracking)
        reward_display = f"""
📊 **Reward Tracker**
━━━━━━━━━━━━━━━━━━━━━
│ Step Reward:    `{reward_formatted}`
│ Category:       `{reward_category}`
━━━━━━━━━━━━━━━━━━━━━
"""

        message = obs.get("message", "Action executed.")
        if reward > 0.2:
            message = f"🌟 {message} Great job!"
        elif reward > 0:
            message = f"✓ {message}"
        elif reward < 0:
            message = f"⚠️ {message} Consider a different approach."

        # Update action hint for next action
        next_action_hint = f"💡 {get_action_description(action_type)}"

        return status, history, reward_display, message, "✅ Success", next_action_hint

    except requests.exceptions.Timeout:
        return "⏱️ Request timed out.", "", "", "", "Timeout Error", ""
    except requests.exceptions.ConnectionError:
        return "🔌 Connection failed.", "", "", "", "Connection Error", ""
    except requests.exceptions.HTTPError as e:
        return f"🚫 HTTP Error {e.response.status_code}", "", "", "", "HTTP Error", ""
    except Exception as e:
        return f"❌ Error: {str(e)}", "", "", "", "Unexpected Error", ""


def grade_current_episode() -> str:
    """Grade the current episode with detailed results."""
    try:
        global current_session_id

        if not current_session_id:
            return """
❌ **No Active Session**

Please reset the environment and run an episode first.

**Steps:**
1. Go to the **Interactive** tab
2. Click **🔄 Reset Environment**
3. Take some actions
4. Return here to grade
"""

        payload = {"session_id": current_session_id}
        response = requests.post(f"{BASE_URL}/grader", json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        score = data.get('score', 0)
        passed = data.get('passed', False)

        # Score color and emoji
        if score >= 0.8:
            score_emoji = "🏆"
            score_color = "#22c55e"
            score_msg = "Excellent performance!"
        elif score >= 0.6:
            score_emoji = "👍"
            score_color = "#3b82f6"
            score_msg = "Good job!"
        elif score >= 0.4:
            score_emoji = "📚"
            score_color = "#eab308"
            score_msg = "Room for improvement."
        else:
            score_emoji = "💪"
            score_color = "#ef4444"
            score_msg = "Keep practicing!"

        result = f"""
<div style="padding: 15px; border-radius: 8px; background: {'#f0fdf4' if passed else '#fef2f2'}; border: 2px solid {score_color};">

## {score_emoji} Grading Results

### 📈 Final Score

# <span style="color: {score_color}; font-size: 2em;">{score:.4f}</span>

**Passed:** {'✅ Yes' if passed else '❌ No'}

*{score_msg}*

---

### 📊 Detailed Breakdown

"""

        breakdown = data.get("breakdown", {})
        if breakdown:
            for key, value in breakdown.items():
                key_display = key.replace('_', ' ').title()
                bar_width = min(100, int(value * 100))
                bar_color = "#22c55e" if value >= 0.7 else "#eab308" if value >= 0.4 else "#ef4444"
                result += f"""
**{key_display}**
<div style="background: #e5e7eb; border-radius: 4px; height: 20px; margin: 4px 0;">
  <div style="background: {bar_color}; width: {bar_width}%; height: 100%; border-radius: 4px; text-align: center; color: white; font-size: 12px; line-height: 20px;">{value:.2f}</div>
</div>
"""
        else:
            result += "*No detailed breakdown available.*\n"

        feedback = data.get("feedback", "No feedback available.")
        result += f"""
---

### 💬 Feedback

{feedback}

</div>
"""

        return result

    except requests.exceptions.Timeout:
        return "⏱️ Grading request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "🔌 Connection failed. Is the server running?"
    except requests.exceptions.HTTPError as e:
        return f"🚫 HTTP Error {e.response.status_code}: {str(e)}"
    except Exception as e:
        return f"❌ Error grading episode: {str(e)}"


def run_baseline_demo() -> str:
    """Run baseline and display results with enhanced formatting."""
    try:
        response = requests.get(f"{BASE_URL}/baseline", timeout=BASELINE_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        result = """
## 🤖 Baseline Agent Results

*Running rule-based baseline agent across all difficulty levels...*

---

"""

        for difficulty in ["easy", "medium", "hard"]:
            diff_data = data.get("baseline_results", {}).get(difficulty, {})
            score = diff_data.get('score', 0)
            passed = diff_data.get('passed', False)

            # Difficulty-specific styling
            diff_icon = "🟢" if difficulty == "easy" else "🟡" if difficulty == "medium" else "🔴"
            diff_color = "#22c55e" if passed else "#ef4444"

            result += f"""
### {diff_icon} {difficulty.upper()} Task

<div style="padding: 10px; border-left: 4px solid {diff_color}; background: #f9fafb; margin: 10px 0;">

| Metric | Value |
|--------|-------|
| **Score** | `{score:.4f}` |
| **Total Reward** | `{diff_data.get('total_reward', 0):.4f}` |
| **Steps Taken** | `{diff_data.get('steps', 0)}` |
| **Status** | {'✅ Passed' if passed else '❌ Failed'} |

</div>

"""

        summary = data.get("summary", {})
        avg_score = summary.get('average_score', 0)

        # Overall assessment
        if avg_score >= 0.7:
            assessment = "🌟 Excellent baseline performance!"
        elif avg_score >= 0.5:
            assessment = "👍 Solid baseline performance."
        else:
            assessment = "📚 Baseline needs improvement."

        result += f"""
---

## 📊 Summary Overview

| Difficulty | Score |
|------------|-------|
| 🟢 Easy | `{summary.get('easy_score', 0):.4f}` |
| 🟡 Medium | `{summary.get('medium_score', 0):.4f}` |
| 🔴 Hard | `{summary.get('hard_score', 0):.4f}` |

### 🎯 Average Score: `{avg_score:.4f}`

*{assessment}*

"""

        return result

    except requests.exceptions.Timeout:
        return "⏱️ Baseline request timed out. This may take up to 2 minutes for full execution."
    except requests.exceptions.ConnectionError:
        return "🔌 Connection failed. Is the server running?"
    except requests.exceptions.HTTPError as e:
        return f"🚫 HTTP Error {e.response.status_code}: {str(e)}"
    except Exception as e:
        return f"❌ Error running baseline: {str(e)}"


def get_tasks_info() -> str:
    """Get available tasks information with enhanced display."""
    try:
        response = requests.get(f"{BASE_URL}/tasks", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        tasks = data.get("tasks", [])
        if not tasks:
            return "📋 **No tasks available at this time.**\n\nCheck back later or contact the administrator."

        result = "## 📋 Available Tasks\n\n"

        for task in tasks:
            difficulty = task.get('difficulty', 'unknown')
            diff_icon = "🟢" if difficulty == "easy" else "🟡" if difficulty == "medium" else "🔴"

            result += f"""
<div style="padding: 15px; border-radius: 8px; background: #f9fafb; margin: 10px 0; border: 1px solid #e5e7eb;">

### {diff_icon} {task.get('name', 'Unknown')} ({difficulty.upper()})

| Property | Value |
|----------|-------|
| **Task ID** | `{task.get('task_id', 'N/A')}` |
| **Max Steps** | `{task.get('max_steps', 0)}` |
| **Difficulty** | {difficulty.title()} |

**Description:**

{task.get('description', 'No description available.')}

</div>

---

"""

        return result

    except requests.exceptions.Timeout:
        return "⏱️ Request timed out."
    except requests.exceptions.ConnectionError:
        return "🔌 Connection failed. Is the server running?"
    except Exception as e:
        return f"❌ Error fetching tasks: {str(e)}"


def get_metrics() -> str:
    """Fetch and display environment metrics."""
    try:
        response = requests.get(f"{BASE_URL}/metrics", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        result = "## 📈 Environment Metrics\n\n"

        # Total episodes
        total = data.get("total_episodes", 0)
        result += f"""
### 🎮 Total Episodes: `{total}`

"""

        # Success rate
        success_rate = data.get("success_rate", 0)
        bar_width = int(success_rate * 100)
        result += f"""
### 📊 Success Rate

<div style="background: #e5e7eb; border-radius: 8px; height: 24px; margin: 8px 0;">
  <div style="background: {'#22c55e' if success_rate >= 0.7 else '#eab308' if success_rate >= 0.4 else '#ef4444'}; width: {bar_width}%; height: 100%; border-radius: 8px; text-align: center; color: white; font-size: 14px; line-height: 24px;">{success_rate:.1%}</div>
</div>

"""

        # Average scores by difficulty
        result += "### 🎯 Average Scores by Difficulty\n\n"
        for diff in ["easy", "medium", "hard"]:
            diff_score = data.get(f"avg_{diff}_score", 0)
            diff_icon = "🟢" if diff == "easy" else "🟡" if diff == "medium" else "🔴"
            result += f"- {diff_icon} **{diff.title()}:** `{diff_score:.4f}`\n"

        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return "📊 **Metrics endpoint not available.**\n\nThis feature may not be implemented in your server version."
        return f"🚫 HTTP Error {e.response.status_code}"
    except Exception as e:
        return f"❌ Error fetching metrics: {str(e)}"


# Global state
current_session_id = None
reward_history = []


def create_gradio_interface():
    """Create the enhanced Gradio interface."""

    with gr.Blocks(
        title="SupportEnv - Customer Support RL Environment",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container { max-width: 1400px !important; }
        .md text { font-size: 14px; }
        """
    ) as demo:

        # Header
        gr.Markdown("""
        # 🎧 SupportEnv - Customer Support RL Environment

        > An OpenEnv environment for training AI agents on customer support workflows.

        **Features:** Interactive Episode Running | Baseline Testing | Real-time Metrics | Detailed Grading
        """)

        with gr.Tabs():
            # ──────────────────────────────────────────────────────────────────
            # Interactive Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("🎮 Interactive"):

                with gr.Row():
                    with gr.Column(scale=3):
                        ticket_display = gr.Markdown(
                            value="""
                            <div style="padding: 20px; text-align: center; color: #6b7280;">
                                <h3>📬 No Active Session</h3>
                                <p>Click 'Reset Environment' to start a new episode.</p>
                            </div>
                            """,
                            label="Current Ticket"
                        )

                        status_display = gr.Textbox(
                            label="📊 Session Status",
                            interactive=False,
                            placeholder="Status will appear here..."
                        )

                        message_display = gr.Textbox(
                            label="🔔 Last Message",
                            interactive=False,
                            placeholder="Messages will appear here..."
                        )

                    with gr.Column(scale=1):
                        gr.Markdown("### ⚙️ Configuration")

                        difficulty_dropdown = gr.Dropdown(
                            choices=["easy", "medium", "hard"],
                            value="easy",
                            label="🎯 Task Difficulty",
                            info="Select the challenge level"
                        )

                        seed_input = gr.Number(
                            value=42,
                            label="🌱 Random Seed",
                            precision=0,
                            info="For reproducible episodes (optional)"
                        )

                        reset_btn = gr.Button(
                            "🔄 Reset Environment",
                            variant="primary",
                            size="lg"
                        )

                gr.Markdown("---")

                gr.Markdown("### 🎬 Take Action")

                with gr.Row():
                    with gr.Column(scale=1):
                        action_type = gr.Dropdown(
                            choices=["classify", "respond", "escalate", "request_info", "resolve"],
                            value="classify",
                            label="📌 Action Type",
                            info="Choose your action"
                        )

                        action_hint = gr.Textbox(
                            label="💡 Action Guide",
                            interactive=False,
                            value=get_action_description("classify"),
                            lines=2
                        )

                    with gr.Column(scale=2):
                        action_content = gr.Textbox(
                            label="📝 Content",
                            placeholder="Enter your action content here...",
                            lines=4,
                            info="Classification category, response text, or escalation reason"
                        )

                with gr.Row():
                    step_btn = gr.Button("▶️ Execute Action", variant="secondary", size="lg")
                    clear_btn = gr.Button("🧹 Clear Content", variant="stop")

                gr.Markdown("---")

                with gr.Row():
                    with gr.Column(scale=2):
                        history_display = gr.Markdown(
                            value="📜 *No actions taken yet.*",
                            label="📜 Interaction History"
                        )

                    with gr.Column(scale=1):
                        reward_display = gr.Textbox(
                            label="📊 Reward Tracker",
                            interactive=False,
                            value="""
📊 **Reward Tracker**
━━━━━━━━━━━━━━━━━━━━━
│ Step Reward:    `0.0000`
│ Cumulative:     `0.0000`
│ Average:        `0.0000`
━━━━━━━━━━━━━━━━━━━━━
""",
                            lines=7
                        )

                gr.Markdown("---")

                with gr.Row():
                    grade_btn = gr.Button("📊 Grade Episode", variant="primary", size="lg")

                grade_output = gr.Markdown(label="📋 Grading Results")

                # Connect events
                reset_btn.click(
                    reset_environment,
                    inputs=[difficulty_dropdown, seed_input],
                    outputs=[ticket_display, status_display, history_display, reward_display, message_display, action_hint, message_display]
                )

                step_btn.click(
                    step_environment,
                    inputs=[action_type, action_content],
                    outputs=[status_display, history_display, reward_display, message_display, message_display, action_hint]
                )

                grade_btn.click(
                    grade_current_episode,
                    outputs=[grade_output]
                )

                # Update action hint when action type changes
                action_type.change(
                    lambda x: get_action_description(x),
                    inputs=[action_type],
                    outputs=[action_hint]
                )

                # Clear content button
                clear_btn.click(
                    lambda: "",
                    outputs=[action_content]
                )

            # ──────────────────────────────────────────────────────────────────
            # Baseline Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("🤖 Baseline"):
                gr.Markdown("""
                ### 🤖 Run Baseline Agent

                This runs the rule-based baseline agent against all three difficulty levels
                and shows reproducible scores.

                **What to expect:**
                - Tests easy, medium, and hard tasks
                - Takes ~30-60 seconds to complete
                - Results are deterministic with same seed
                """)

                baseline_btn = gr.Button("🚀 Run Baseline", variant="primary", size="lg")
                baseline_output = gr.Markdown(label="Baseline Results")

                baseline_btn.click(
                    run_baseline_demo,
                    outputs=[baseline_output]
                )

            # ──────────────────────────────────────────────────────────────────
            # Tasks Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("📋 Tasks"):
                gr.Markdown("""
                ### 📚 Task Library

                Browse available tasks and their configurations.
                """)

                tasks_btn = gr.Button("📖 Load Tasks Info", variant="primary")
                tasks_output = gr.Markdown(label="Available Tasks")

                tasks_btn.click(
                    get_tasks_info,
                    outputs=[tasks_output]
                )

            # ──────────────────────────────────────────────────────────────────
            # Metrics Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("📈 Metrics"):
                gr.Markdown("""
                ### 📊 Environment Metrics

                View aggregate statistics about environment usage.
                """)

                metrics_btn = gr.Button("🔄 Refresh Metrics", variant="primary")
                metrics_output = gr.Markdown(label="Metrics")

                metrics_btn.click(
                    get_metrics,
                    outputs=[metrics_output]
                )

            # ──────────────────────────────────────────────────────────────────
            # About Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("ℹ️ About"):
                gr.Markdown("""
                ## About SupportEnv

                **SupportEnv** is a production-grade reinforcement learning environment
                that simulates customer support workflows.

                ---

                ### ✨ Features

                | Feature | Description |
                |---------|-------------|
                | 🎯 Difficulty Levels | 3 levels: Easy, Medium, Hard |
                | 📊 Deterministic Grading | Scores 0.0-1.0 with detailed breakdowns |
                | 💰 Dense Rewards | Immediate feedback for each action |
                | 🔄 OpenEnv Compliant | Full API compatibility |
                | 🐳 Docker Ready | Easy deployment |

                ---

                ### 🎬 Action Space

                | Action | Description | Use Case |
                |--------|-------------|----------|
                | `classify` | Categorize the ticket | First action to understand the issue |
                | `respond` | Send a response | Address customer concerns |
                | `escalate` | Transfer to human | Complex issues beyond AI scope |
                | `request_info` | Ask for details | When more context is needed |
                | `resolve` | Close the ticket | When issue is fully addressed |

                ---

                ### 👁️ Observation Space

                - 📝 **Ticket text and metadata** - Full context of the customer issue
                - 💭 **Customer sentiment** - Emotional state (-1 to 1 scale)
                - 📜 **Interaction history** - Previous exchanges
                | 🏷️ **Classification status** - Current category assignment
                - ⏱️ **Steps remaining** - Episode progress indicator

                ---

                ### 💰 Reward Structure

                | Action | Reward | Conditions |
                |--------|--------|------------|
                | Correct classification | +0.25 | Matching the expected category |
                | Good response | +0.30 | Appropriate and helpful |
                | Correct escalation | +0.35 | When escalation is the right choice |
                | Resolution bonus | +0.40 | Successfully closing the ticket |
                | Incorrect action | Negative | Varies by severity |

                ---

                ### 🔗 Links

                - [📖 OpenEnv Documentation](https://openenv.dev)
                - [💻 GitHub Repository](https://github.com/username/support-env)

                ---

                *Built with ❤️ for advancing AI customer support research*
                """)

    return demo


if __name__ == "__main__":
    demo = create_gradio_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        debug=True
    )
