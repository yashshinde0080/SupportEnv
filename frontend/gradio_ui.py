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

# Global state
current_session_id = None
cumulative_reward = 0.0
step_count = 0
reward_history = []

def reset_environment(difficulty: str, seed: int = None) -> Tuple[str, str, str, str, str, str]:
    """Reset environment and return initial state with full validation."""
    global current_session_id, cumulative_reward, step_count, reward_history
    try:
        # Reset state
        cumulative_reward = 0.0
        step_count = 0
        reward_history = []

        # Validate inputs
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

        # Format sentiment with emoji
        sentiment_val = obs.get('customer_sentiment', 0)
        sentiment_formatted, sentiment_category = format_sentiment(sentiment_val)

        # Get difficulty info
        difficulty_info = get_difficulty_info(difficulty)

        ticket_display = f"""
        <div class='premium-card' style='background: white !important;'>
            <div class='card-header'>📬 Ticket: {obs.get('ticket_subject', 'N/A')}</div>
            <div class='card-body' style='color: black !important; background: white !important;'>
                <div class='ticket-meta' style='color: black !important; display: flex; justify-content: space-between;'>
                    <span style='color: black !important;'><b>Customer:</b> {obs.get('customer_name', 'N/A')}</span>
                    <span style='color: black !important;'><b>Sentiment:</b> {sentiment_formatted}</span>
                    <span style='color: black !important;'><b>Difficulty:</b> {difficulty.upper()}</span>
                </div>
                <hr style='border-top: 1px solid #e2e8f0; margin: 15px 0;'/>
                <div class='ticket-content' style='background: #f1f5f9 !important; color: black !important; padding: 20px; border-radius: 10px; border: 1px solid #cbd5e1; font-size: 1.1em;'>
                    {obs.get('ticket_text', 'No ticket loaded')}
                </div>
                <div class='difficulty-info' style='color: #475569 !important; font-style: italic; border-top: 1px solid #e2e8f0; padding-top: 10px;'>{difficulty_info}</div>
            </div>
        </div>
        """

        session_id = current_session_id or 'N/A'
        session_display = session_id[:8] if session_id != 'N/A' else 'N/A'
        status = f"""🆔 {session_display}... | 📊 Steps: 0/{obs.get('max_steps', 0)} | 🎯 {difficulty.upper()}"""
        history = "📜 *No actions taken yet.*"

        reward_display = f"""
        <div class='reward-tracker'>
            <div class='reward-val'>0.0000</div>
            <div class='reward-label'>Cumulative Reward</div>
            <div class='reward-grid'>
                <div class='reward-item'><span>Step:</span> 0.0000</div>
                <div class='reward-item'><span>Avg:</span> 0.0000</div>
            </div>
        </div>
        """
        message = "✅ Environment reset successfully. Ready to begin!"
        action_hint = f"💡 {get_action_description('classify')}"

        return ticket_display, status, history, reward_display, message, action_hint

    except Exception as e:
        return f"❌ Error: {str(e)}", "", "", "", f"System Error: {e}", ""


def step_environment(action_type: str, content: str) -> Tuple[str, str, str, str, str]:
    """Take a step in the environment with full validation."""
    global current_session_id, cumulative_reward, step_count, reward_history
    try:
        # Validate session
        if not current_session_id:
            return "⚠️ Please reset the environment first.", "", "", "🚫 No Session", "Select action"

        # Validate action
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
        
        # Update metrics
        step_count += 1
        cumulative_reward += reward
        reward_history.append(reward)
        avg_reward = cumulative_reward / step_count

        # Enhanced status display
        steps_remaining = obs.get('steps_remaining', 0)
        status = f"""{'🏁' if done else '🎮'} Steps: {step_count}/{obs.get('max_steps', step_count+steps_remaining)} | Episode Done: {done}"""

        # Format history
        history_items = obs.get("interaction_history", [])
        if history_items:
            history_parts = []
            for i, item in enumerate(history_items, 1):
                role = item.get('role', 'unknown').title()
                role_class = "role-agent" if role == "Agent" else "role-customer"
                history_parts.append(f"<div class='history-item {role_class}' style='color: #000000 !important; background: {( '#eef2ff' if role == 'Agent' else '#f0fdf4' )} !important; border-left: 5px solid {( '#3b82f6' if role == 'Agent' else '#22c55e' )}; padding: 12px; margin: 8px 0; border-radius: 10px;'><b>{i}. {role}:</b> <span style='color: #000000 !important;'>{item.get('content', '')}</span></div>")
            history = "\n".join(history_parts)
        else:
            history = "📜 *No interactions yet.*"

        # Reward display
        reward_formatted, _ = format_step_reward(reward)
        reward_display = f"""
        <div class='reward-tracker'>
            <div class='reward-val'>{cumulative_reward:+.4f}</div>
            <div class='reward-label'>Cumulative Reward</div>
            <div class='reward-grid'>
                <div class='reward-item'><span>Step:</span> {reward_formatted}</div>
                <div class='reward-item'><span>Avg:</span> {avg_reward:+.4f}</div>
            </div>
        </div>
        """

        message = obs.get("message", "Action executed.")
        next_hint = get_action_description(action_type)

        return status, history, reward_display, message, next_hint

    except Exception as e:
        return f"❌ Error: {str(e)}", "", "", "Unexpected Error", ""


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
            
            schema = task.get('action_schema', {})
            schema_json = json.dumps(schema, indent=2)

            result += f"""
<div class='premium-card' style='margin: 10px 0;'>
    <div class='card-header' style='background: #334155;'>{diff_icon} {task.get('name', 'Unknown')}</div>
    <div class='card-body'>
        <p><b>Task ID:</b> <code>{task.get('task_id', 'N/A')}</code> | <b>Max Steps:</b> {task.get('max_steps', 0)}</p>
        <p>{task.get('description', 'No description available.')}</p>
        <details>
            <summary style='cursor: pointer; color: #3b82f6;'>Show Action Schema</summary>
            <pre style='background: #f1f5f9; padding: 10px; border-radius: 4px; font-size: 0.8em;'>{schema_json}</pre>
        </details>
    </div>
</div>
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
        <div style='margin-bottom: 20px;'>
            <div style='display: flex; justify-content: space-between; margin-bottom: 5px;'>
                <span><b>Success Rate</b></span>
                <span>{success_rate:.1%}</span>
            </div>
            <div style="background: #e2e8f0; border-radius: 999px; height: 12px;">
                <div style="background: {'#22c55e' if success_rate >= 0.7 else '#f59e0b'}; width: {bar_width}%; height: 100%; border-radius: 999px;"></div>
            </div>
        </div>
        """

        # Average scores by difficulty
        result += "<div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;'>\n"
        for diff in ["easy", "medium", "hard"]:
            diff_score = data.get(f"avg_{diff}_score", 0)
            diff_icon = "🟢" if diff == "easy" else "🟡" if diff == "medium" else "🔴"
            result += f"""
            <div style='background: white; border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; text-align: center;'>
                <div style='font-size: 1.5em;'>{diff_icon}</div>
                <div style='font-size: 0.8em; color: #64748b;'>{diff.upper()}</div>
                <div style='font-size: 1.25em; font-weight: 700; color: #0f172a !important;'>{diff_score:.4f}</div>
            </div>
            """
        result += "</div>"
        return result
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return "📊 **Metrics endpoint not available.**\n\nThis feature may not be implemented in your server version."
        return f"🚫 HTTP Error {e.response.status_code}"
    except Exception as e:
        return f"❌ Error fetching metrics: {str(e)}"


# Global state
current_session_id = None
cumulative_reward = 0.0
step_count = 0
reward_history = []


def create_gradio_interface():
    """Create the enhanced Gradio interface."""
    
    # Define theme and explicit high-contrast CSS
    theme = gr.themes.Soft(primary_hue="blue", secondary_hue="slate")
    custom_css = """
        .gradio-container { max-width: 1400px !important; }
        
        /* Premium Card Styling */
        .premium-card { 
            border-radius: 12px; 
            overflow: hidden; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.15); 
            background: #ffffff !important; 
            border: 1px solid #e2e8f0;
            margin-bottom: 24px;
        }
        .card-header {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: #ffffff !important;
            padding: 14px 24px;
            font-weight: 700;
            font-size: 1.15em;
            letter-spacing: 0.5px;
        }
        .card-body { 
            padding: 24px; 
            color: #000000 !important; 
            background: #ffffff !important;
        }
        .card-body * { color: #000000 !important; }
        .ticket-meta { 
            display: flex; 
            justify-content: space-between; 
            margin-bottom: 20px;
            font-size: 0.95em;
            color: #1e293b !important;
            font-weight: 700;
        }
        .ticket-content { 
            background: #f1f5f9 !important; 
            padding: 20px; 
            border-radius: 10px; 
            font-size: 1.15em; 
            line-height: 1.7;
            margin-bottom: 20px;
            border: 1px solid #cbd5e1;
            color: #000000 !important; 
            font-family: 'Inter', system-ui, sans-serif;
        }
        .ticket-content * { color: #000000 !important; }
        .difficulty-info { 
            font-size: 0.9em; 
            font-style: italic; 
            color: #475569 !important; 
            border-top: 1px solid #e2e8f0;
            padding-top: 15px;
            font-weight: 600;
        }
        
        /* Reward Display Styling */
        .reward-tracker {
            background: #0f172a !important;
            color: #ffffff !important;
            padding: 24px;
            border-radius: 16px;
            text-align: center;
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
            border: 1px solid #334155;
        }
        .reward-tracker * { color: #ffffff !important; }
        .reward-val { 
            font-size: 3.2em; 
            font-weight: 900; 
            color: #38bdf8 !important; 
            margin-bottom: 8px; 
        }
        .reward-label { 
            font-size: 0.85em; 
            text-transform: uppercase; 
            letter-spacing: 2px; 
            color: #94a3b8 !important; 
            font-weight: 700;
        }
        .reward-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 12px; 
            margin-top: 24px; 
            border-top: 1px solid #334155;
            padding-top: 24px;
        }
        .reward-item { font-size: 1.05em; color: #ffffff !important; font-weight: 600; }
        
        /* Interaction History Styling */
        .history-item { 
            padding: 14px 20px; 
            margin: 12px 0; 
            border-radius: 12px; 
            font-size: 1.05em;
            line-height: 1.6;
            color: #000000 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .history-item * { color: #000000 !important; }
        .role-agent { background: #eef2ff !important; border-left: 6px solid #3b82f6; }
        .role-customer { background: #f0fdf4 !important; border-left: 6px solid #22c55e; }
    """

    with gr.Blocks(title="SupportEnv Dashboard") as demo:

        # Header
        gr.Markdown("""
        # 🎧 SupportEnv - Advanced AI Platform
        > Interactive RL Environment for Customer Support
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
                            <div style="padding: 20px; text-align: center; color: black !important; background: white !important; border-radius: 12px; border: 1px solid #e2e8f0;">
                                <h3 style='color: black !important;'>📬 No Active Session</h3>
                                <p style='color: black !important;'>Click 'Reset' to start a new episode.</p>
                            </div>
                            """,
                            label="Current Ticket"
                        )

                        status_display = gr.Textbox(
                            label="📊 Session Status",
                            interactive=False,
                            placeholder="Status info..."
                        )

                        message_display = gr.Textbox(
                            label="🔔 Last Message",
                            interactive=False,
                            placeholder="Messages..."
                        )

                    with gr.Column(scale=1):
                        gr.Markdown("### ⚙️ Config")

                        difficulty_dropdown = gr.Dropdown(
                            choices=["easy", "medium", "hard"],
                            value="easy",
                            label="🎯 Difficulty"
                        )

                        seed_input = gr.Number(
                            value=42,
                            label="🌱 Seed",
                            precision=0
                        )

                        reset_btn = gr.Button(
                            "🔄 Reset",
                            variant="primary"
                        )

                gr.Markdown("---")
                gr.Markdown("### 🎬 Action")

                with gr.Row():
                    with gr.Column(scale=1):
                        action_type = gr.Dropdown(
                            choices=["classify", "respond", "escalate", "request_info", "resolve"],
                            value="classify",
                            label="📌 Type"
                        )

                        action_hint = gr.Textbox(
                            label="💡 Hint",
                            interactive=False,
                            value=get_action_description("classify")
                        )

                    with gr.Column(scale=2):
                        action_content = gr.Textbox(
                            label="📝 Content",
                            placeholder="Type here...",
                            lines=4
                        )

                with gr.Row():
                    step_btn = gr.Button("▶️ Execute", variant="secondary")
                    clear_btn = gr.Button("🧹 Clear", variant="stop")

                gr.Markdown("---")

                with gr.Row():
                    with gr.Column(scale=2):
                        history_display = gr.Markdown(
                            value="📜 *None*",
                            label="📜 History"
                        )

                    with gr.Column(scale=1):
                        reward_display = gr.HTML(
                            value="""
                            <div class='reward-tracker'>
                                <div class='reward-val'>0.0000</div>
                                <div class='reward-label'>Reward</div>
                            </div>
                            """
                        )

                gr.Markdown("---")
                grade_btn = gr.Button("📊 Grade", variant="primary")
                grade_output = gr.Markdown(label="Results")

                # Connect events
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

                grade_btn.click(
                    grade_current_episode,
                    outputs=[grade_output]
                )

                action_type.change(
                    lambda x: get_action_description(x),
                    inputs=[action_type],
                    outputs=[action_hint]
                )

                clear_btn.click(lambda: "", outputs=[action_content])

            # ──────────────────────────────────────────────────────────────────
            # Baseline Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("🤖 Baseline"):
                gr.Markdown("### 🤖 Agent Baseline")
                baseline_btn = gr.Button("🚀 Run Baseline", variant="primary")
                baseline_output = gr.Markdown(label="Results")

                baseline_btn.click(run_baseline_demo, outputs=[baseline_output])

            # ──────────────────────────────────────────────────────────────────
            # Tasks Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("📋 Tasks"):
                gr.Markdown("### 📚 Libraries")
                tasks_btn = gr.Button("📖 Load", variant="primary")
                tasks_output = gr.Markdown(label="Tasks")

                tasks_btn.click(get_tasks_info, outputs=[tasks_output])

            # ──────────────────────────────────────────────────────────────────
            # Metrics Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("📈 Metrics"):
                gr.Markdown("### 📊 Stats")
                metrics_btn = gr.Button("🔄 Refresh", variant="primary")
                metrics_output = gr.Markdown(label="Metrics")

                metrics_btn.click(get_metrics, outputs=[metrics_output])

            # ──────────────────────────────────────────────────────────────────
            # About Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("ℹ️ About"):
                gr.Markdown("""
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
                - ⏱️ **Steps remaining** - Episode progress indicator

                ---

                ### 🔗 Links

                - [📖 OpenEnv Documentation](https://openenv.dev)
                """)

    return demo, theme, custom_css


if __name__ == "__main__":
    demo, theme, css = create_gradio_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        debug=True,
        theme=theme,
        css=css
    )
