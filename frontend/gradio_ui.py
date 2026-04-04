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

        sentiment_val = obs.get('customer_sentiment', 0)
        sentiment_label = "Positive" if sentiment_val >= 0.5 else "Neutral" if sentiment_val >= -0.1 else "Negative"
        sentiment_class = "badge-emerald" if sentiment_val >= 0.5 else "badge-indigo" if sentiment_val >= -0.1 else "badge-rose"

        ticket_display = f"""
        <div class='premium-card' style='margin:0'>
            <div class='card-header'>
                <div style='display:flex; align-items:center; gap: 8px; color: black !important;'>
                    <span style='font-size: 1.25rem;'>📬</span>
                    <span style='color: black !important;'>{obs.get('ticket_subject', 'General Support Inquiry')}</span>
                </div>
                <span class='badge badge-indigo' style='color: black !important;'>{difficulty.upper()} LEVEL</span>
            </div>
            <div class='card-body'>
                <div style='display: flex; gap: 1rem; margin-bottom: 1.5rem;'>
                    <div class='metric-card' style='padding: 0.75rem 1rem; flex: 1; border: 1px solid #e2e8f0;'>
                        <div class='metric-label'>Customer</div>
                        <div style='font-weight:700; color: black !important;'>{obs.get('customer_name', 'Client')}</div>
                    </div>
                    <div class='metric-card' style='padding: 0.75rem 1rem; flex: 1; border: 1px solid #e2e8f0;'>
                        <div class='metric-label'>Sentiment</div>
                        <span class='badge {sentiment_class}' style='color: black !important;'>{sentiment_label}</span>
                    </div>
                </div>
                <div class='ticket-view' style='color: black !important;'>
                    {obs.get('ticket_text', 'No ticket content loaded')}
                </div>
                <div style='margin-top: 1rem; font-size: 0.875rem; color: #334155 !important;'>
                    <b style='color: black !important;'>Challenge Profile:</b> <span style='color: black !important;'>{get_difficulty_info(difficulty)}</span>
                </div>
            </div>
        </div>
        """

        session_id = current_session_id or 'N/A'
        session_short = session_id[:8] if session_id != 'N/A' else 'None'
        status = f"CONNECTED: {session_short} | PHASE: INITIALIZED"
        message = "✅ Environment successfully reset for new episode."
        
        history = "<div style='text-align: center; color: #94a3b8; padding: 20px;'>Awaiting first interaction...</div>"
        reward_display = f"""
        <div style='background: #1e293b; border-radius: 12px; padding: 15px; color: white; text-align: center;'>
            <div style='font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8;'>CUMULATIVE</div>
            <div style='font-size: 1.5rem; font-weight: 800; color: #38bdf8;'>0.000</div>
            <div style='font-size: 0.6rem; margin-top: 5px; color: #64748b;'>REWARD</div>
        </div>
        """
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

        # Format status
        steps_total = obs.get('max_steps', step_count + obs.get('steps_remaining', 0))
        status = f"{'🏁 COMPLETE' if done else '🎮 ACTIVE'} | STEP: {step_count}/{steps_total}"

        # Format history as chat bubbles
        history_items = obs.get("interaction_history", [])
        if history_items:
            history_parts = ["<div style='display: flex; flex-direction: column; gap: 0.5rem;'>"]
            for item in history_items:
                role = item.get('role', 'unknown').lower()
                chat_class = "chat-agent" if role == "agent" else "chat-customer"
                role_label = "Agent" if role == "agent" else "Customer"
                
                history_parts.append(f"""
                <div class='history-chat-item {chat_class}'>
                    <div style='font-size: 0.65rem; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; opacity: 0.8;'>{role_label}</div>
                    <div>{item.get('content', '')}</div>
                </div>
                """)
            history_parts.append("</div>")
            history = "\n".join(history_parts)
        else:
            history = "<div style='text-align: center; color: #94a3b8; padding: 20px;'>No interactions logged.</div>"

        # Reward display
        reward_formatted, _ = format_step_reward(reward)
        reward_display = f"""
        <div style='background: #1e293b; border-radius: 12px; padding: 15px; color: white; text-align: center;'>
            <div style='font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8;'>CUMULATIVE</div>
            <div style='font-size: 1.5rem; font-weight: 800; color: #38bdf8;'>{cumulative_reward:+.3f}</div>
            <div style='font-size: 0.65rem; margin-top: 5px; color: #22c55e;'>LAST: {reward_formatted}</div>
        </div>
        """

        message = obs.get("message", "Action processed.")
        next_hint = f"💡 {get_action_description(action_type)}"

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

        # Score visual data
        score_percentage = score * 100
        score_color = "#10b981" if passed else "#ef4444"
        score_emoji = "🏆" if passed else "💪"
        
        result = f"""
        <div class='score-box'>
            <div class='score-circle' style='color: {score_color}; border-color: {score_color}20;'>
                {score:.2f}
            </div>
            <h2 style='margin: 0;'>{score_emoji} {data.get('message', 'Assessment Complete')}</h2>
            <div class='badge {'badge-emerald' if passed else 'badge-rose'}' style='font-size: 1rem; margin-top: 1rem;'>
                {'PASSED' if passed else 'FAILED'}
            </div>
            <p style='color: #64748b; margin-top: 1.5rem; font-style: italic;'>"{data.get('feedback', 'No specific feedback available.')}"</p>
        </div>
        
        <div class='premium-card'>
            <div class='card-header'>📊 Performance Breakdown</div>
            <div class='card-body'>
        """

        breakdown = data.get("breakdown", {})
        if breakdown:
            for key, value in breakdown.items():
                label = key.replace('_', ' ').title()
                val_pct = value * 100
                color = "#4f46e5" if value >= 0.8 else "#f59e0b" if value >= 0.5 else "#ef4444"
                
                result += f"""
                <div style='margin-bottom: 1.5rem;'>
                    <div style='display: flex; justify-content: space-between; font-weight: 600; font-size: 0.9rem;'>
                        <span>{label}</span>
                        <span>{value:.2f}</span>
                    </div>
                    <div class='progress-bar-container'>
                        <div class='progress-bar-fill' style='width: {val_pct}%; background: {color};'></div>
                    </div>
                </div>
                """
        else:
            result += "<p style='text-align: center; color: #94a3b8;'>Detailed metrics not available for this session.</p>"

        result += """
            </div>
        </div>
        """
        return result

        return result

    except requests.exceptions.Timeout:
        return "⏱️ Grading request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "🔌 Connection failed. Is the server running?"
    except requests.exceptions.HTTPError as e:
        return f"🚫 HTTP Error {e.response.status_code}: {str(e)}"
    except Exception as e:
        return f"❌ Error grading episode: {str(e)}"


def run_baseline_demo(baseline_diff: str = "easy") -> str:
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
        result += "<div class='metric-grid'>\n"
        for diff in ["easy", "medium", "hard"]:
            diff_score = data.get(f"avg_{diff}_score", 0)
            diff_icon = "🟢" if diff == "easy" else "🟡" if diff == "medium" else "🔴"
            result += f"""
            <div class='metric-card'>
                <div style='font-size: 1.5rem;'>{diff_icon}</div>
                <div class='metric-label'>{diff.upper()} AVG</div>
                <div class='metric-value'>{diff_score:.4f}</div>
            </div>
            """
        result += "</div>"
        return result
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return "<div class='alert alert-warning'>📊 Metrics endpoint not available in this server version.</div>"
        return f"🚫 HTTP Error {e.response.status_code}"
    except Exception as e:
        return f"<div class='alert alert-error'>❌ Error fetching metrics: {str(e)}</div>"


def create_gradio_interface():
    """Create the enhanced Gradio interface with a premium, modern design."""
    
    # Define theme
    theme = gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
        spacing_size="md",
        radius_size="lg",
    )
    
    custom_css = """
        /* Global Styles */
        body { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
        .gradio-container { max-width: 1400px !important; margin: 0 auto !important; }
        
        /* Modern Typography */
        h1, h2, h3 { color: #1e293b !important; font-weight: 800 !important; letter-spacing: -0.025em !important; }
        .gr-markdown { font-size: 1.05rem; line-height: 1.6; }
        
        /* Main Container Cards */
        .premium-card { 
            background: white !important; 
            border: 1px solid #e2e8f0; 
            border-radius: 16px; 
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            overflow: hidden;
            margin-bottom: 1.5rem;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .premium-card:hover { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
        
        .card-header {
            background: #f1f5f9 !important;
            border-bottom: 1px solid #e2e8f0;
            padding: 1.25rem 1.5rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: #000000 !important;
        }
        .card-header * { color: #000000 !important; }
        
        .card-body { padding: 1.5rem; background: white !important; color: #000000 !important; }
        .card-body * { color: #000000 !important; }
        
        /* Sidebar/Control Panel */
        .sidebar { background: #f1f5f9 !important; border-radius: 16px; padding: 1.5rem; height: 100%; border: 1px solid #e2e8f0; color: #000000 !important; }
        .sidebar * { color: #000000 !important; }
        
        /* Interactive Elements */
        .gr-button-primary { 
            background: linear-gradient(to right, #4f46e5, #4338ca) !important; 
            border: none !important; 
            box-shadow: 0 4px 14px 0 rgba(79, 70, 229, 0.39) !important;
            transition: all 0.2s ease !important;
            color: white !important; /* Buttons stay white for contrast */
        }
        .gr-button-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5) !important; }
        
        /* Status Badges */
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #000000 !important;
            border: 1px solid rgba(0,0,0,0.1);
        }
        .badge-indigo { background: #e0e7ff; color: #000000 !important; }
        .badge-emerald { background: #d1fae5; color: #000000 !important; }
        .badge-amber { background: #fef3c7; color: #000000 !important; }
        .badge-rose { background: #ffe4e6; color: #000000 !important; }

        /* Ticket Content Area */
        .ticket-view {
            background: #ffffff !important;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.5rem;
            font-family: 'Inter', system-ui, sans-serif;
            font-size: 1.125rem;
            line-height: 1.75;
            color: #000000 !important;
            margin: 1rem 0;
            white-space: pre-wrap;
            box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.05);
        }
        
        /* History Items */
        .history-chat-item {
            margin-bottom: 1rem;
            max-width: 85%;
            padding: 1rem 1.25rem;
            border-radius: 1rem;
            position: relative;
            color: #000000 !important;
        }
        .chat-agent {
            background: #4f46e5 !important;
            color: white !important;
            align-self: flex-end;
            margin-left: auto;
            border-bottom-right-radius: 0.25rem;
        }
        .chat-agent * { color: white !important; }
        .chat-customer {
            background: #f1f5f9 !important;
            color: #000000 !important;
            align-self: flex-start;
            border-bottom-left-radius: 0.25rem;
            border: 1px solid #e2e8f0;
        }
        .chat-customer * { color: #000000 !important; }
        
        /* Score Visualizations */
        .score-box {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
            color: #000000 !important;
        }
        .score-box * { color: #000000 !important; }
        
        .score-circle {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
            font-weight: 900;
            margin: 0 auto 1.5rem;
            border: 8px solid #f1f5f9;
        }
        
        .progress-bar-container {
            width: 100%;
            background: #f1f5f9;
            border-radius: 9999px;
            height: 0.75rem;
            overflow: hidden;
            margin: 0.5rem 0 1.5rem;
        }
        .progress-bar-fill {
            height: 100%;
            border-radius: 9999px;
            transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        /* Dashboard Metric Cards */
        .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }
        .metric-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            color: #000000 !important;
        }
        .metric-card * { color: #000000 !important; }
        .metric-value { font-size: 1.5rem; font-weight: 700; color: #000000 !important; }
        .metric-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #64748b !important; margin-top: 0.25rem; }
        
        /* Alert components */
        .alert { border-radius: 8px; padding: 12px 16px; margin-bottom: 1rem; font-weight: 500; }
        .alert-warning { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
        .alert-error { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
        
        /* Force Markdown text to black */
        .gr-markdown h1, .gr-markdown h2, .gr-markdown h3, .gr-markdown p, .gr-markdown li, .gr-markdown span {
            color: #000000 !important;
        }
        
        /* Alert components */
        .alert { border-radius: 8px; padding: 12px 16px; margin-bottom: 1rem; font-weight: 500; }
        .alert-warning { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
        .alert-error { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
    """

    with gr.Blocks(title="SupportEnv Dashboard", css=custom_css, theme=theme) as demo:
        
        with gr.Row(elem_classes="header-row"):
            with gr.Column(scale=8):
                gr.Markdown("""
                # 🎧 SupportEnv <span class='badge badge-indigo'>PRO</span>
                A premium reinforcement learning environment for customer support automation.
                """)
            with gr.Column(scale=2):
                gr.Markdown("<div style='text-align: right; padding-top: 20px;'><span class='badge badge-emerald'>V2.1.0 STABLE</span></div>")

        with gr.Tabs():
            # ──────────────────────────────────────────────────────────────────
            # Interactive Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("🎮 Interactive Agent"):
                with gr.Row():
                    # Left Column: Configuration & Controls
                    with gr.Column(scale=1, elem_classes="sidebar"):
                        gr.Markdown("### ⚙️ Session Config")
                        difficulty_dropdown = gr.Dropdown(
                            choices=["easy", "medium", "hard"],
                            value="easy",
                            label="🎯 Target Difficulty",
                            info="Select the challenge level for the agent."
                        )
                        seed_input = gr.Number(
                            value=42,
                            label="🌱 Environment Seed",
                            precision=0,
                            info="Use a specific seed for reproducible tasks."
                        )
                        reset_btn = gr.Button(
                            "🔄 Initialize Environment",
                            variant="primary"
                        )
                        
                        gr.Markdown("---")
                        gr.Markdown("### 📊 Live Metrics")
                        status_display = gr.Textbox(
                            label="Current Status",
                            interactive=False,
                            placeholder="Awaiting initialization..."
                        )
                        message_display = gr.Textbox(
                            label="System Feedback",
                            interactive=False,
                            placeholder="System logs will appear here..."
                        )

                    # Right Column: The Interaction Workspace
                    with gr.Column(scale=3):
                        with gr.Group(elem_classes="premium-card"):
                            with gr.Row(elem_classes="card-header"):
                                gr.Markdown("### 📬 Active Support Ticket")
                                gr.Markdown("<span class='badge badge-indigo' id='interaction-count'>LIVE FEED</span>")
                            
                            with gr.Column(elem_classes="card-body"):
                                ticket_display = gr.HTML(
                                    value="""
                                    <div style='text-align: center; padding: 40px;'>
                                        <div style='font-size: 3rem; margin-bottom: 1rem;'>🌑</div>
                                        <h3 style='margin:0'>No Active Session</h3>
                                        <p style='color: #64748b'>Initialize the environment from the sidebar to begin testing.</p>
                                    </div>
                                    """
                                )
                        
                        with gr.Group(elem_classes="premium-card"):
                            with gr.Row(elem_classes="card-header"):
                                gr.Markdown("### 🎬 Action Control")
                                action_hint = gr.Markdown("<small><i>💡 Select an action type to see documentation</i></small>")
                            
                            with gr.Row(elem_classes="card-body"):
                                with gr.Column(scale=1):
                                    action_type = gr.Dropdown(
                                        choices=["classify", "respond", "escalate", "request_info", "resolve"],
                                        value="classify",
                                        label="Action Type"
                                    )
                                with gr.Column(scale=3):
                                    action_content = gr.Textbox(
                                        label="Action Content / Payload",
                                        placeholder="Enter the agent's response or classification data...",
                                        lines=3
                                    )
                                    with gr.Row():
                                        clear_btn = gr.Button("🧹 Clear Input", size="sm")
                                        step_btn = gr.Button("🚀 Execute Action", variant="primary", size="lg")

                        with gr.Group(elem_classes="premium-card"):
                            with gr.Row(elem_classes="card-header"):
                                gr.Markdown("### 📜 Session History")
                                gr.Markdown("<small>Real-time interaction log</small>")
                            
                            with gr.Column(elem_classes="card-body"):
                                with gr.Row():
                                    with gr.Column(scale=4):
                                        history_display = gr.HTML(
                                            value="<div style='text-align: center; color: #94a3b8; padding: 20px;'>No interactions yet.</div>"
                                        )
                                    with gr.Column(scale=1):
                                        reward_display = gr.HTML(
                                            value="""
                                            <div style='background: #1e293b; border-radius: 12px; padding: 15px; color: white; text-align: center;'>
                                                <div style='font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8;'>CUMULATIVE</div>
                                                <div style='font-size: 1.5rem; font-weight: 800; color: #38bdf8;'>0.000</div>
                                                <div style='font-size: 0.6rem; margin-top: 5px; color: #64748b;'>REWARD</div>
                                            </div>
                                            """
                                        )

            # ──────────────────────────────────────────────────────────────────
            # Grading & Evaluation Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("📊 Evaluation Report"):
                with gr.Row():
                    with gr.Column(scale=1, elem_classes="sidebar"):
                        gr.Markdown("""
                        ### 🔍 Agent Assessment
                        The grader evaluates:
                        - **Accuracy**: Correct classification
                        - **Tone**: Professionalism
                        - **Efficiency**: Speed to resolve
                        - **Decisioning**: Logical escalations
                        """)
                        grade_btn = gr.Button("🏆 Final Evaluation", variant="primary", size="lg")
                        
                    with gr.Column(scale=3):
                        grade_output = gr.HTML(
                            value="""
                            <div style='border: 2px dashed #e2e8f0; border-radius: 16px; padding: 60px; text-align: center; color: #94a3b8;'>
                                <div style='font-size: 4rem; margin-bottom: 1rem;'>📋</div>
                                <h3>Results Pending</h3>
                                <p>Complete an episode and click evaluate.</p>
                            </div>
                            """
                        )

            # ──────────────────────────────────────────────────────────────────
            # Tasks/Benchmarks Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("📚 Benchmarks"):
                with gr.Row():
                    with gr.Column(scale=1, elem_classes="sidebar"):
                        gr.Markdown("### 🏁 Baseline Tests")
                        baseline_diff = gr.Dropdown(
                            choices=["easy", "medium", "hard"],
                            value="easy",
                            label="Test Difficulty"
                        )
                        baseline_btn = gr.Button("🏃 Run Group Benchmark")
                        gr.Markdown("---")
                        tasks_btn = gr.Button("🔍 Refresh Task List")
                    
                    with gr.Column(scale=3):
                        with gr.Tabs():
                            with gr.TabItem("📋 Task Repository"):
                                tasks_display = gr.HTML("Click 'Refresh' to load tasks")
                            with gr.TabItem("🔬 Benchmark Results"):
                                baseline_output = gr.Markdown("Results will appear here...")

            # ──────────────────────────────────────────────────────────────────
            # Metrics Tab
            # ──────────────────────────────────────────────────────────────────
            with gr.TabItem("📈 Metrics"):
                with gr.Row():
                    with gr.Column(scale=1, elem_classes="sidebar"):
                        gr.Markdown("### 📉 System Stats")
                        metrics_btn = gr.Button("🔄 Refresh Metrics")
                    with gr.Column(scale=3):
                        metrics_display = gr.HTML("Click 'Refresh' to load stats")

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

                ### 🔗 Resources
                - [📖 OpenEnv Documentation](https://openenv.dev)
                - [🧑‍💻 Source Repository](https://github.com/support-env)
                """)

        # ──────────────────────────────────────────────────────────────────
        # Event Listeners
        # ──────────────────────────────────────────────────────────────────
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
        
        tasks_btn.click(get_tasks_info, outputs=[tasks_display])
        metrics_btn.click(get_metrics, outputs=[metrics_display])
        baseline_btn.click(run_baseline_demo, inputs=[baseline_diff], outputs=[baseline_output])
        
        clear_btn.click(lambda: "", outputs=[action_content])
        
        action_type.change(
            lambda x: f"💡 {get_action_description(x)}",
            inputs=[action_type],
            outputs=[action_hint]
        )

    return demo, theme, custom_css


if __name__ == "__main__":
    demo, theme, css = create_gradio_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        debug=True
    )
