import os
import uuid
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

import gradio as gr
import pandas as pd

# Internal imports
from server.environment import SupportEnvironment
from server.ticket_generator import TASK_DEFINITIONS
from server.graders import GradeResult
from models import SupportAction, SupportObservation, SupportState, PublicSupportState
from baseline.policy import BaselinePolicy

# Configure logging
logger = logging.getLogger("SupportEnv-UI")

# Global state
active_sessions: Dict[str, SupportEnvironment] = {}
episode_history: List[Dict[str, Any]] = []
GLOBAL_METRICS = {
    "total_episodes": 0,
    "success_rate": 0.0,
    "total_successful": 0,
    "avg_easy_score": 0.0,
    "avg_medium_score": 0.0,
    "avg_hard_score": 0.0,
    "scores_by_difficulty": {"easy": [], "medium": [], "hard": []}
}

# Limit session storage to prevent memory leaks on Spaces
MAX_SESSIONS = 50

def _cleanup_sessions():
    """Simple cleanup if sessions exceed limit."""
    global active_sessions
    if len(active_sessions) > MAX_SESSIONS:
        logger.info(f"Session limit reached ({len(active_sessions)}). Clearing old sessions.")
        active_sessions = {}

METRICS_FILE = "metrics.json"

def _load_metrics():
    """Load global metrics from file."""
    global GLOBAL_METRICS
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, 'r') as f:
                data = json.load(f)
                GLOBAL_METRICS.update(data)
                logger.info("Loaded metrics from persistence.")
        except Exception as e:
            logger.error(f"Error loading metrics: {e}")

def _save_metrics():
    """Save global metrics to file."""
    try:
        with open(METRICS_FILE, 'w') as f:
            json.dump(GLOBAL_METRICS, f)
    except Exception as e:
        logger.error(f"Error saving metrics: {e}")

# Load metrics on startup
_load_metrics()

def _update_global_metrics(difficulty: str, score: float, passed: bool):
    """Update global metrics on episode completion."""
    GLOBAL_METRICS["total_episodes"] += 1
    if passed:
        GLOBAL_METRICS["total_successful"] += 1
    
    if GLOBAL_METRICS["total_episodes"] > 0:
        GLOBAL_METRICS["success_rate"] = GLOBAL_METRICS["total_successful"] / GLOBAL_METRICS["total_episodes"]
    
    if difficulty in GLOBAL_METRICS["scores_by_difficulty"]:
        GLOBAL_METRICS["scores_by_difficulty"][difficulty].append(score)
        scores = GLOBAL_METRICS["scores_by_difficulty"][difficulty]
        GLOBAL_METRICS[f"avg_{difficulty}_score"] = sum(scores) / len(scores)
    
    # Persist changes
    _save_metrics()

# ============== Helper Functions ==============

def format_observation(obs) -> str:
    """Format observation for display."""
    if not obs:
        return "No observation"

    obs_dict = obs.model_dump() if hasattr(obs, 'model_dump') else obs
    
    lines = [
        f"**Ticket ID:** {obs_dict.get('ticket_id', 'N/A')}",
        f"**Customer:** {obs_dict.get('customer_name', 'N/A')}",
        f"**Subject:** {obs_dict.get('ticket_subject', 'N/A')}",
        f"**Difficulty:** {obs_dict.get('task_difficulty', 'N/A')}",
        f"**Steps Remaining:** {obs_dict.get('steps_remaining', 0)}",
        f"**Customer Sentiment:** {obs_dict.get('customer_sentiment', 0):.2f}",
        f"**Classification:** {obs_dict.get('current_classification', 'Not classified')}",
        f"**Done:** {obs_dict.get('done', False)}",
        f"**Reward:** {obs_dict.get('reward', 0.0) if obs_dict.get('reward') is not None else 'N/A'}",
        "",
        "**Ticket Content:**",
        f"```",
        obs_dict.get('ticket_text', 'N/A'),
        f"```",
    ]

    if obs_dict.get('message'):
        lines.extend(["", f"**Status Message:** {obs_dict['message']}"])

    if obs_dict.get('interaction_history'):
        lines.extend(["", "**Interaction History:**"])
        for interaction in obs_dict['interaction_history'][-5:]:
            role = interaction.get('role', 'unknown').capitalize()
            content = interaction.get('content', '')[:100]
            lines.append(f"- **{role}:** {content}...")

    return "\n".join(lines)

def format_state(state) -> str:
    """Format state for display."""
    if not state:
        return "No state available"

    s = state.model_dump() if hasattr(state, 'model_dump') else state
    
    return "\n".join([
        f"**Episode ID:** {s.get('episode_id', 'N/A')}",
        f"**Step Count:** {s.get('step_count', 0)}",
        f"**Task ID:** {s.get('task_id', 'N/A')}",
        f"**Difficulty:** {s.get('task_difficulty', 'N/A')}",
        f"**Max Steps:** {s.get('max_steps', 10)}",
        f"**Classification Correct:** {s.get('classification_correct', False)}",
        f"**Response Quality Score:** {s.get('response_quality_score', 0):.2f}",
        f"**Escalation Correct:** {s.get('escalation_correct', False)}",
        f"**Resolved:** {s.get('resolved', False)}",
        f"**Total Reward:** {s.get('total_reward', 0):.2f}",
        f"**Customer Sentiment:** {s.get('customer_sentiment', 0):.2f}",
    ])

def format_grade(grade) -> str:
    """Format grade result for display."""
    if not grade:
        return "No grade result yet."

    if hasattr(grade, 'model_dump'):
        g = grade.model_dump()
    else:
        g = grade

    breakdown = g.get('breakdown', {})
    breakdown_str = "\n".join([
        f"  - {k.replace('_', ' ').title()}: {v:.2f}"
        for k, v in breakdown.items()
    ])

    return "\n".join([
        f"**Final Score:** {g.get('score', 0):.4f}",
        f"**Passed:** {'Yes' if g.get('passed', False) else 'No'}",
        "",
        "**Score Breakdown:**",
        breakdown_str,
        "",
        f"**Feedback:** {g.get('feedback', 'N/A')}",
    ])

# ============== Tab 1: Interactive Environment ==============

def env_reset(difficulty: str, seed: Optional[int] = None) -> tuple:
    """Reset environment for new episode."""
    global active_sessions
    
    _cleanup_sessions()
    session_id = str(uuid.uuid4())
    env = SupportEnvironment()
    
    try:
        actual_seed = seed if seed and seed > 0 else None
        observation = env.reset(difficulty=difficulty, seed=actual_seed, episode_id=session_id)
        active_sessions[session_id] = env
        
        obs_text = format_observation(observation)
        state_text = f"**Session ID:** `{session_id}`\n\n**Status:** Ready"
        
        logger.info(f"Reset environment: {session_id}, difficulty={difficulty}")
        
        return (
            obs_text,
            state_text,
            gr.update(interactive=True), # Classify
            gr.update(interactive=True), # Respond
            gr.update(interactive=True), # Request Info
            gr.update(interactive=True), # Lookup KB
            gr.update(interactive=True), # Escalate
            gr.update(interactive=True), # Resolve
            session_id
        )
    except Exception as e:
        logger.error(f"Error resetting environment: {e}")
        return (f"**Error:** {str(e)}", "N/A", *[gr.update(interactive=False)]*6, "")

def env_step(session_id: str, action_type: str, content: str, confidence: float = 1.0) -> tuple:
    """Execute action in environment."""
    global active_sessions, episode_history

    if not session_id or session_id not in active_sessions:
        return (
            "**Error:** No active session. Please start a new episode.",
            "",
            gr.update()
        )

    env = active_sessions[session_id]
    
    try:
        action = SupportAction(
            action_type=action_type,
            content=content,
            confidence=confidence
        )
        
        observation = env.step(action)
        obs_text = format_observation(observation)
        
        # Get state
        state_dict = env.state.model_dump()
        public_state = PublicSupportState(**state_dict)
        state_text = format_state(public_state)
        
        grade_text = gr.update()
        if observation.done:
            grade_result = env.grade_episode()
            grade_text = format_grade(grade_result)
            
            # Update history
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            episode_history.append({
                "timestamp": now,
                "difficulty": env.state.task_difficulty,
                "score": grade_result.score,
                "passed": grade_result.passed
            })
            
            # Update global metrics
            _update_global_metrics(env.state.task_difficulty, grade_result.score, grade_result.passed)
            
            if len(episode_history) > 100:
                episode_history.pop(0)

        return obs_text, state_text, grade_text
    except Exception as e:
        logger.error(f"Error in step: {e}")
        return f"**Error executing action:** {str(e)}", "", gr.update()

# ============== Tab 2: Baseline Agent ==============

def run_baseline():
    """Run baseline agent locally on all difficulties with progress updates."""
    
    logger.info("Running baseline agent evaluation")
    results = {}
    policy = BaselinePolicy()
    
    output_lines = ["# 📊 Baseline Agent Evaluation Results", ""]
    yield "\n".join(output_lines) + "\n\n### ⏳ Initializing System..."
    
    for difficulty in ["easy", "medium", "hard"]:
        yield "\n".join(output_lines) + f"\n\n### 🚀 Running '{difficulty.title()}' Difficulty..."
        
        env = SupportEnvironment()
        observation = env.reset(seed=42, difficulty=difficulty)
        policy.reset()
        
        total_reward = 0.0
        steps = 0
        
        while not observation.done and steps < 20:
            action = policy.act(observation)
            observation = env.step(action)
            total_reward += (observation.reward or 0.0)
            steps += 1
        
        grade_result = env.grade_episode()
        results[difficulty] = grade_result
        
        output_lines.extend([
            f"## {'✅' if grade_result.passed else '❌'} {difficulty.title()} Difficulty",
            f"- **Final Score:** `{grade_result.score:.4f}`",
            f"- **Accumulated Reward:** `{total_reward:.2f}`",
            f"- **Total Steps Taken:** `{steps}`",
            f"- **Status:** {'Passed' if grade_result.passed else 'Failed'}",
            "",
        ])
        yield "\n".join(output_lines)
    
    avg_score = sum(g.score for g in results.values()) / len(results)
    output_lines.extend([
        "---",
        "## 🏁 Final Evaluation Summary",
        f"### **Average Balanced Score: {avg_score:.4f}**",
    ])
    
    yield "\n".join(output_lines)

# ============== Tab 3: Task Browser ==============

def load_tasks() -> tuple:
    """Load all available tasks."""
    tasks = []
    for difficulty, config in TASK_DEFINITIONS.items():
        tasks.append({
            "Difficulty": difficulty.title(),
            "Task ID": config["task_id"],
            "Name": config["name"],
            "Max Steps": config["max_steps"],
            "Description": config["description"][:100] + "..." if len(config["description"]) > 100 else config["description"],
        })
    
    df = pd.DataFrame(tasks)
    
    details = []
    for difficulty, config in TASK_DEFINITIONS.items():
        details.extend([
            f"### {config['name']} ({difficulty.title()})",
            f"**Task ID:** `{config['task_id']}`",
            f"**Description:** {config['description']}",
            f"**Max Steps:** {config['max_steps']}",
            f"**Available Actions:** `classify`, `respond`, `escalate`, `request_info`, `resolve`, `lookup_kb`",
            "",
        ])
    
    return "\n".join(details), df

# ============== Tab 4: Metrics Dashboard ==============

def load_metrics() -> tuple:
    """Load performance metrics."""
    summary = [
        "# Global Performance Metrics",
        "",
        "## Overall Statistics",
        f"- **Total Episodes:** {GLOBAL_METRICS['total_episodes']}",
        f"- **Success Rate:** {GLOBAL_METRICS.get('success_rate', 0):.2%}",
        f"- **Total Successful:** {GLOBAL_METRICS['total_successful']}",
        "",
        "## Average Scores by Difficulty",
        f"- **Easy:** {GLOBAL_METRICS.get('avg_easy_score', 0):.4f}",
        f"- **Medium:** {GLOBAL_METRICS.get('avg_medium_score', 0):.4f}",
        f"- **Hard:** {GLOBAL_METRICS.get('avg_hard_score', 0):.4f}",
    ]

    table_data = []
    for diff in ['easy', 'medium', 'hard']:
        scores = GLOBAL_METRICS['scores_by_difficulty'].get(diff, [])
        if scores:
            table_data.append({
                "Difficulty": diff.title(),
                "Episodes": len(scores),
                "Average": f"{sum(scores)/len(scores):.4f}",
                "Best": f"{max(scores):.4f}",
                "Worst": f"{min(scores):.4f}",
            })
    
    table_df = pd.DataFrame(table_data) if table_data else pd.DataFrame(columns=["Difficulty", "Episodes", "Average", "Best", "Worst"])
    
    return "\n".join(summary), table_df

# ============== Tab 5: Episode History ==============

def view_history() -> tuple:
    """View session history."""
    if not episode_history:
        return "No episodes run yet in this session.", pd.DataFrame(columns=["Timestamp", "Difficulty", "Score", "Passed"])
    
    df = pd.DataFrame(episode_history)
    df["Score"] = df["score"].apply(lambda x: f"{x:.4f}")
    df["Difficulty"] = df["difficulty"].str.title()
    df["Passed"] = df["passed"].apply(lambda x: "Yes" if x else "No")
    
    display_df = df[["timestamp", "Difficulty", "Score", "Passed"]].rename(columns={"timestamp": "Timestamp"})
    
    total = len(episode_history)
    passed = sum(1 for ep in episode_history if ep['passed'])
    avg_score = sum(ep['score'] for ep in episode_history) / total
    
    summary = [
        "# Session History Summary",
        "",
        f"**Episodes Run:** {total}",
        f"**Episodes Passed:** {passed} ({passed/total:.1%})",
        f"**Avg Score:** {avg_score:.4f}",
    ]
    
    return "\n".join(summary), display_df

def clear_history():
    """Clear session history."""
    global episode_history
    episode_history = []
    return "History cleared.", pd.DataFrame(columns=["Timestamp", "Difficulty", "Score", "Passed"])

# ============== Tab 6: Configuration ==============

def view_config() -> str:
    """View environment configuration."""
    config_lines = [
        "# SupportEnv Configuration",
        "",
        "## Space Info",
        f"- **SDK:** Gradio 4+",
        f"- **Entry Point:** `app.py`",
        f"- **Python Version:** 3.10",
        "",
        "## Environment Settings",
        f"- `USE_LLM_GENERATOR`: {os.getenv('USE_LLM_GENERATOR', 'False')}",
        f"- `GENERATOR_PROVIDER`: {os.getenv('GENERATOR_PROVIDER', 'N/A')}",
        f"- `MAX_SESSIONS`: {MAX_SESSIONS}",
        "",
        "## Available Categories",
        "- `billing`",
        "- `technical`",
        "- `account`",
        "- `general`",
    ]
    return "\n".join(config_lines)

# ============== UI Construction ==============

CUSTOM_CSS = """
.gradio-container {
    background: radial-gradient(circle at 50% 0%, #1a1c2c 0%, #0d0e14 100%) !important;
    color: #e2e8f0 !important;
}

.observation-box, .state-box, .grade-box, .baseline-box {
    background: rgba(30, 41, 59, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 16px !important;
    padding: 24px !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
    margin-bottom: 20px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.observation-box:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 48px rgba(99, 102, 241, 0.2) !important;
    border-color: rgba(99, 102, 241, 0.3) !important;
}

.observation-box { border-left: 6px solid #6366f1 !important; }
.state-box { border-left: 6px solid #10b981 !important; }
.grade-box { border-left: 6px solid #f59e0b !important; }

.gradio-container * {
    color: #f1f5f9 !important;
}

.gradio-container h1, .gradio-container h2, .gradio-container h3 {
    color: #ffffff !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px !important;
    margin-bottom: 1rem !important;
}

.observation-box strong, .state-box strong, .grade-box strong {
    color: #a5b4fc !important;
}

.observation-box code, .observation-box pre {
    background: rgba(15, 23, 42, 0.9) !important;
    color: #38bdf8 !important;
    border-radius: 8px !important;
    border: 1px solid rgba(56, 189, 248, 0.2) !important;
    padding: 12px !important;
    font-family: 'Fira Code', 'Courier New', monospace !important;
}

.gradio-container table {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
}

.gradio-container th {
    background: rgba(71, 85, 105, 0.6) !important;
    color: #ffffff !important;
    padding: 12px !important;
}

.gradio-container td {
    background: rgba(30, 41, 59, 0.4) !important;
    padding: 10px !important;
}

button.primary {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4) !important;
}

button.primary:hover {
    transform: scale(1.02) !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6) !important;
}
"""

def create_gradio_interface():
    """Create the Gradio interface and return (demo, theme, css)."""
    theme = gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="slate",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    ).set(
        body_background_fill="*neutral_950",
        block_background_fill="*neutral_900",
        block_border_width="0px",
    )

    with gr.Blocks(title="SupportEnv Dashboard", theme=theme, css=CUSTOM_CSS) as demo:
        session_id_state = gr.State("")

        gr.Markdown("# 🎧 SupportEnv: Pro Support Intelligence")
        
        with gr.Tabs():
            with gr.Tab("Environment Interaction"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### ⚙️ Session Setup")
                        diff_input = gr.Dropdown(choices=["easy", "medium", "hard"], value="easy", label="Task Difficulty")
                        seed_input = gr.Number(label="Environment Seed (42 recommended)", value=42, precision=0)
                        reset_btn = gr.Button("🚀 Reset & Start Episode", variant="primary")
                        
                        gr.Markdown("### 🎮 Agent Controls")
                        conf_slider = gr.Slider(0.0, 1.0, value=1.0, step=0.05, label="Action Confidence")
                        
                        with gr.Accordion("Ticket Action Engine", open=True):
                            with gr.Tabs():
                                with gr.Tab("Classify"):
                                    cat_input = gr.Dropdown(["billing", "technical", "account", "general"], value="general", label="Customer Category")
                                    classify_btn = gr.Button("Submit Classification")
                                with gr.Tab("Respond"):
                                    resp_input = gr.Textbox(placeholder="Compose your message to the customer...", lines=4, label="Response Content")
                                    respond_btn = gr.Button("Send Message")
                                with gr.Tab("Gather Info"):
                                    info_input = gr.Textbox(placeholder="What information do you need?", label="Request Details")
                                    info_btn = gr.Button("Request Information")
                                    kb_input = gr.Textbox(placeholder="Search term...", label="KB Knowledge Search")
                                    kb_btn = gr.Button("Search Knowledge Base")
                                with gr.Tab("Resolution"):
                                    res_input = gr.Textbox(placeholder="Summarize the final resolution...", label="Resolution Notes")
                                    resolve_btn = gr.Button("Resolve Ticket", variant="stop")
                                    esc_input = gr.Textbox(placeholder="Reason for transfer...", label="Escalation Details")
                                    escalate_btn = gr.Button("Escalate Ticket", variant="stop")

                    with gr.Column(scale=2):
                        gr.Markdown("### 👁️ Observation Stream")
                        obs_out = gr.Markdown("Initialize an episode to start receiving data.", elem_classes=["observation-box"])
                        
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("### 🧠 Internal State")
                                state_out = gr.Markdown("System inactive", elem_classes=["state-box"])
                            with gr.Column():
                                gr.Markdown("### 🏆 Performance Grade")
                                grade_out = gr.Markdown("Awaiting episode completion.", elem_classes=["grade-box"])

            with gr.Tab("Baseline Agent"):
                gr.Markdown("### 🤖 Heuristic Benchmark Agent\nTest the built-in rule-based agent across all tiers to establish a performance baseline.")
                baseline_btn = gr.Button("⚡ Run Heuristic Evaluation", variant="secondary")
                baseline_out = gr.Markdown("Benchmarking results will appear here.", elem_classes=["baseline-box"])
                baseline_btn.click(fn=run_baseline, outputs=baseline_out)

            with gr.Tab("Task Repository"):
                refresh_tasks_btn = gr.Button("Load Available Tasks", variant="secondary")
                task_details_out = gr.Markdown("No tasks loaded.")
                task_df_out = gr.Dataframe(interactive=False)
                refresh_tasks_btn.click(fn=load_tasks, outputs=[task_details_out, task_df_out])

            with gr.Tab("Metrics Dashboard"):
                refresh_metrics_btn = gr.Button("Refresh Analytics", variant="secondary")
                metrics_summary_out = gr.Markdown("No analytics data.")
                metrics_df_out = gr.Dataframe(interactive=False)
                refresh_metrics_btn.click(fn=load_metrics, outputs=[metrics_summary_out, metrics_df_out])

            with gr.Tab("Session Logs"):
                with gr.Row():
                    refresh_hist_btn = gr.Button("Refresh Log History", variant="secondary")
                    clear_hist_btn = gr.Button("Clear Logs", variant="stop")
                hist_summary_out = gr.Markdown("No logs in current session.")
                hist_df_out = gr.Dataframe(interactive=False)
                refresh_hist_btn.click(fn=view_history, outputs=[hist_summary_out, hist_df_out])
                clear_hist_btn.click(fn=clear_history, outputs=[hist_summary_out, hist_df_out])

            with gr.Tab("Configuration"):
                config_out = gr.Markdown(view_config())

        reset_btn.click(
            fn=env_reset,
            inputs=[diff_input, seed_input],
            outputs=[obs_out, state_out, classify_btn, respond_btn, info_btn, kb_btn, escalate_btn, resolve_btn, session_id_state]
        )

        classify_btn.click(fn=lambda s, c, conf: env_step(s, "classify", c, conf), inputs=[session_id_state, cat_input, conf_slider], outputs=[obs_out, state_out, grade_out])
        respond_btn.click(fn=lambda s, c, conf: env_step(s, "respond", c, conf), inputs=[session_id_state, resp_input, conf_slider], outputs=[obs_out, state_out, grade_out])
        info_btn.click(fn=lambda s, c, conf: env_step(s, "request_info", c, conf), inputs=[session_id_state, info_input, conf_slider], outputs=[obs_out, state_out, grade_out])
        kb_btn.click(fn=lambda s, c, conf: env_step(s, "lookup_kb", c, conf), inputs=[session_id_state, kb_input, conf_slider], outputs=[obs_out, state_out, grade_out])
        resolve_btn.click(fn=lambda s, c, conf: env_step(s, "resolve", c, conf), inputs=[session_id_state, res_input, conf_slider], outputs=[obs_out, state_out, grade_out])
        escalate_btn.click(fn=lambda s, c, conf: env_step(s, "escalate", c, conf), inputs=[session_id_state, esc_input, conf_slider], outputs=[obs_out, state_out, grade_out])

    return demo, theme, CUSTOM_CSS
