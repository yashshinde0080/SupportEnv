"""
Comprehensive Gradio UI for SupportEnv - Customer Support RL Environment.

This UI provides:
1. Interactive Environment - Run episodes manually or with auto-play
2. Baseline Agent - Test the rule-based baseline policy
3. Task Browser - View all available tasks and their definitions
4. Metrics Dashboard - View performance metrics across episodes
5. Episode History - Track and review past episodes
6. Configuration - View system configuration
"""

import gradio as gr
import requests
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd

# Server configuration
DEFAULT_SERVER_URL = "http://localhost:8000"

# Global state
episode_history = []
current_session = None
current_observation = None
current_difficulty = None


def get_server_url() -> str:
    """Get server URL from environment or default."""
    import os
    return os.getenv("SUPPORT_ENV_URL", DEFAULT_SERVER_URL)


# ============== Helper Functions ==============

def call_api(endpoint: str, method: str = "GET", json_data: Optional[Dict] = None) -> Dict:
    """Make API call to server."""
    url = f"{get_server_url()}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=json_data or {}, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to server. Is it running?"}
    except Exception as e:
        return {"error": str(e)}


def format_observation(obs: Dict) -> str:
    """Format observation for display."""
    if not obs:
        return "No observation"

    lines = [
        f"**Ticket ID:** {obs.get('ticket_id', 'N/A')}",
        f"**Customer:** {obs.get('customer_name', 'N/A')}",
        f"**Subject:** {obs.get('ticket_subject', 'N/A')}",
        f"**Difficulty:** {obs.get('task_difficulty', 'N/A')}",
        f"**Steps Remaining:** {obs.get('steps_remaining', 0)}",
        f"**Customer Sentiment:** {obs.get('customer_sentiment', 0):.2f}",
        f"**Classification:** {obs.get('current_classification', 'Not classified')}",
        f"**Done:** {obs.get('done', False)}",
        f"**Reward:** {obs.get('reward', 'N/A')}",
        "",
        "**Ticket Content:**",
        f"```",
        obs.get('ticket_text', 'N/A'),
        f"```",
    ]

    if obs.get('message'):
        lines.extend(["", f"**Message:** {obs['message']}"])

    if obs.get('interaction_history'):
        lines.extend(["", "**Interaction History:**"])
        for interaction in obs['interaction_history'][-5:]:
            role = interaction.get('role', 'unknown').capitalize()
            content = interaction.get('content', '')[:100]
            lines.append(f"- **{role}:** {content}...")

    return "\n".join(lines)


def format_state(state: Dict) -> str:
    """Format state for display."""
    if not state:
        return "No state available"

    return "\n".join([
        f"**Episode ID:** {state.get('episode_id', 'N/A')}",
        f"**Step Count:** {state.get('step_count', 0)}",
        f"**Task ID:** {state.get('task_id', 'N/A')}",
        f"**Difficulty:** {state.get('task_difficulty', 'N/A')}",
        f"**Max Steps:** {state.get('max_steps', 10)}",
        f"**Classification Correct:** {state.get('classification_correct', False)}",
        f"**Response Quality Score:** {state.get('response_quality_score', 0):.2f}",
        f"**Escalation Correct:** {state.get('escalation_correct', False)}",
        f"**Resolved:** {state.get('resolved', False)}",
        f"**Total Reward:** {state.get('total_reward', 0):.2f}",
        f"**Customer Sentiment:** {state.get('customer_sentiment', 0):.2f}",
    ])


def format_grade(grade: Dict) -> str:
    """Format grade result for display."""
    if not grade or 'error' in grade:
        return f"Grade Error: {grade.get('error', 'Unknown error')}"

    breakdown = grade.get('breakdown', {})
    breakdown_str = "\n".join([
        f"  - {k.replace('_', ' ').title()}: {v:.2f}"
        for k, v in breakdown.items()
    ])

    return "\n".join([
        f"**Final Score:** {grade.get('score', 0):.4f}",
        f"**Passed:** {'Yes' if grade.get('passed', False) else 'No'}",
        "",
        "**Score Breakdown:**",
        breakdown_str,
        "",
        f"**Feedback:** {grade.get('feedback', 'N/A')}",
    ])


# ============== Tab 1: Interactive Environment ==============

def env_reset(difficulty: str, seed: int = None) -> tuple:
    """Reset environment for new episode."""
    global current_session, current_observation, current_difficulty

    json_data = {"difficulty": difficulty}
    if seed:
        json_data["seed"] = seed

    result = call_api("/reset", method="POST", json_data=json_data)

    if 'error' in result:
        return (
            f"**Error:** {result['error']}",
            "N/A",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
        )

    current_session = result.get('session_id')
    current_observation = result.get('observation')
    current_difficulty = difficulty

    obs_text = format_observation(current_observation)
    state_text = f"**Session ID:** {current_session}\n\n**Status:** Ready for actions"

    return (
        obs_text,
        state_text,
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
    )


def env_step(action_type: str, content: str, confidence: float = 1.0) -> tuple:
    """Execute action in environment."""
    global current_session, current_observation

    if not current_session:
        return (
            "**Error:** No active session. Please reset first.",
            "",
            gr.update(),
            gr.update(),
        )

    json_data = {
        "session_id": current_session,
        "action_type": action_type,
        "content": content,
        "confidence": confidence
    }

    result = call_api("/step", method="POST", json_data=json_data)

    if 'error' in result:
        return (
            f"**Error:** {result['error']}",
            "",
            gr.update(),
            gr.update(),
        )

    current_observation = result.get('observation')
    obs_text = format_observation(current_observation)

    # Get state
    state_result = call_api(f"/state/{current_session}")
    state_text = format_state(state_result) if 'error' not in state_result else ""

    # If done, automatically fetch grade
    if result.get('done', False):
        time.sleep(0.1)  # Small delay to ensure server processed
        grade_result = call_api("/grader", method="POST", json_data={"session_id": current_session})
        grade_text = format_grade(grade_result)

        # Add to history
        episode_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "difficulty": current_difficulty,
            "score": grade_result.get('score', 0),
            "passed": grade_result.get('passed', False),
            "total_reward": current_observation.get('ticket_text', '')[:50],
        })
    else:
        grade_text = gr.update()

    return obs_text, state_text, grade_text


def env_classify(category: str, confidence: float) -> tuple:
    """Classify ticket."""
    return env_step("classify", category, confidence)


def env_respond(message: str, confidence: float) -> tuple:
    """Send response."""
    return env_step("respond", message, confidence)


def env_escalate(reason: str, confidence: float) -> tuple:
    """Escalate ticket."""
    return env_step("escalate", reason, confidence)


def env_request_info(info: str, confidence: float) -> tuple:
    """Request more information."""
    return env_step("request_info", info, confidence)


def env_lookup_kb(query: str, confidence: float) -> tuple:
    """Lookup in knowledge base."""
    return env_step("lookup_kb", query, confidence)


def env_resolve(summary: str, confidence: float) -> tuple:
    """Resolve ticket."""
    return env_step("resolve", summary, confidence)


def env_grade() -> str:
    """Grade current episode."""
    global current_session

    if not current_session:
        return "**Error:** No active session"

    result = call_api("/grader", method="POST", json_data={"session_id": current_session})
    return format_grade(result)


# ============== Tab 2: Baseline Agent ==============

def run_baseline() -> str:
    """Run baseline agent on all difficulties."""
    result = call_api("/baseline", method="POST")

    if 'error' in result:
        return f"**Error:** {result['error']}"

    baseline = result.get('baseline_results', {})
    summary = result.get('summary', {})

    output_lines = ["# Baseline Agent Results", ""]

    for difficulty in ["easy", "medium", "hard"]:
        if difficulty in baseline:
            data = baseline[difficulty]
            output_lines.extend([
                f"## {difficulty.title()} Difficulty",
                f"- **Score:** {data.get('score', 0):.4f}",
                f"- **Total Reward:** {data.get('total_reward', 0):.2f}",
                f"- **Steps:** {data.get('steps', 0)}",
                f"- **Passed:** {'Yes' if data.get('passed', False) else 'No'}",
                "",
            ])

    if 'average_score' in summary:
        output_lines.extend([
            "## Summary",
            f"- **Easy Score:** {summary.get('easy_score', 0):.4f}",
            f"- **Medium Score:** {summary.get('medium_score', 0):.4f}",
            f"- **Hard Score:** {summary.get('hard_score', 0):.4f}",
            f"- **Average Score:** {summary.get('average_score', 0):.4f}",
        ])

    return "\n".join(output_lines)


# ============== Tab 3: Task Browser ==============

def load_tasks() -> tuple:
    """Load and display all available tasks."""
    result = call_api("/tasks")

    if 'error' in result:
        return f"**Error:** {result['error']}", None

    tasks = result.get('tasks', [])

    if not tasks:
        return "No tasks available", None

    # Create DataFrame for table
    df_data = []
    for task in tasks:
        df_data.append({
            "Difficulty": task.get('difficulty', '').title(),
            "Task ID": task.get('task_id', ''),
            "Name": task.get('name', ''),
            "Max Steps": task.get('max_steps', 0),
            "Description": task.get('description', '')[:100] + "..." if len(task.get('description', '')) > 100 else task.get('description', ''),
        })

    df = pd.DataFrame(df_data)

    # Create detailed view
    details = []
    for task in tasks:
        actions = task.get('action_schema', {})
        actions_str = ", ".join(actions.keys()) if actions else "N/A"

        details.extend([
            f"### {task.get('name', 'Unknown')} ({task.get('difficulty', '').title()})",
            f"**Task ID:** `{task.get('task_id', 'N/A')}`",
            f"**Description:** {task.get('description', 'N/A')}",
            f"**Max Steps:** {task.get('max_steps', 'N/A')}",
            f"**Available Actions:** {actions_str}",
            "",
        ])

    return "\n".join(details), df


# ============== Tab 4: Metrics Dashboard ==============

def load_metrics() -> tuple:
    """Load and display metrics."""
    result = call_api("/metrics")

    if 'error' in result:
        return f"**Error:** {result['error']}", None, None

    metrics = result

    # Create summary cards
    summary = [
        "# Performance Metrics",
        "",
        "## Overall Statistics",
        f"- **Total Episodes:** {metrics.get('total_episodes', 0)}",
        f"- **Success Rate:** {metrics.get('success_rate', 0):.2%}",
        f"- **Total Successful:** {metrics.get('total_successful', 0)}",
        "",
        "## Average Scores by Difficulty",
        f"- **Easy:** {metrics.get('avg_easy_score', 0):.4f}",
        f"- **Medium:** {metrics.get('avg_medium_score', 0):.4f}",
        f"- **Hard:** {metrics.get('avg_hard_score', 0):.4f}",
    ]

    # Create difficulty comparison table
    diff_data = metrics.get('scores_by_difficulty', {})
    table_data = []

    for diff in ['easy', 'medium', 'hard']:
        scores = diff_data.get(diff, [])
        if scores:
            table_data.append({
                "Difficulty": diff.title(),
                "Episodes": len(scores),
                "Average": f"{sum(scores)/len(scores):.4f}" if scores else "N/A",
                "Best": f"{max(scores):.4f}" if scores else "N/A",
                "Worst": f"{min(scores):.4f}" if scores else "N/A",
            })

    table_df = pd.DataFrame(table_data) if table_data else None

    return "\n".join(summary), table_df, None


# ============== Tab 5: Episode History ==============

def view_history() -> tuple:
    """View episode history."""
    if not episode_history:
        return "No episodes run yet. Start interacting with the environment!", None

    # Create DataFrame
    df_data = []
    for ep in episode_history:
        df_data.append({
            "Timestamp": ep.get('timestamp', ''),
            "Difficulty": ep.get('difficulty', ''),
            "Score": f"{ep.get('score', 0):.4f}",
            "Passed": "Yes" if ep.get('passed', False) else "No",
        })

    df = pd.DataFrame(df_data)

    # Summary
    total = len(episode_history)
    passed = sum(1 for ep in episode_history if ep.get('passed', False))
    avg_score = sum(ep.get('score', 0) for ep in episode_history) / total if total > 0 else 0

    summary = [
        "# Episode History",
        "",
        f"**Total Episodes:** {total}",
        f"**Passed:** {passed} ({passed/total:.2%} if total > 0 else 0)",
        f"**Average Score:** {avg_score:.4f}",
        "",
    ]

    return "\n".join(summary), df


def clear_history() -> tuple:
    """Clear episode history."""
    global episode_history
    episode_history = []
    return "Episode history cleared.", None


# ============== Tab 6: Configuration ==============

def view_config() -> str:
    """View current configuration."""
    # Try to get config from server if available
    result = call_api("/health")

    config_lines = [
        "# SupportEnv Configuration",
        "",
        "## Server Settings",
        f"- **Server URL:** {get_server_url()}",
        f"- **Server Status:** {'Online' if 'error' not in result else 'Offline'}",
        "",
        "## Environment Variables",
        "",
        "Key environment variables (from `.env` file):",
        "",
        "### LLM Configuration",
        "- `USE_LLM_GENERATOR`: Enable LLM-based ticket generation",
        "- `GENERATOR_PROVIDER`: Provider (openai, gemini, groq, openrouter, ollama)",
        "- `GENERATOR_MODEL`: Model name",
        "",
        "### API Keys",
        "- `OPENAI_API_KEY`: OpenAI API key",
        "- `GEMINI_API_KEY`: Google Gemini API key",
        "- `GROQ_API_KEY`: Groq API key",
        "- `OPENROUTER_API_KEY`: OpenRouter API key",
        "",
        "### Server Configuration",
        "- `HOST`: Server host (default: 0.0.0.0)",
        "- `PORT`: Server port (default: 7860)",
        "- `WORKERS`: Number of workers",
        "- `DEBUG`: Debug mode",
        "",
        "### Environment Settings",
        "- `MAX_CONCURRENT_ENVS`: Maximum concurrent environments",
        "- `DEFAULT_SEED`: Default random seed",
        "",
        "### Grading Configuration",
        "- `GRADING_STRICT_MODE`: Enable strict grading",
        "- `GRADING_VERBOSE`: Verbose grading output",
    ]

    return "\n".join(config_lines)


# ============== UI Creation ==============

def create_gradio_interface():
    """Create the full Gradio interface."""

    # Custom CSS
    custom_css = """
    .gradio-container {
        max-width: 1400px !important;
        background-color: #0b0f19 !important; /* Deep dark background default */
    }
    
    /* Content Boxes - Forced Visibility Aesthetics */
    .observation-box, .state-box, .grade-box {
        border-radius: 12px !important;
        padding: 20px !important;
        margin: 12px 0 !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
        border: 2px solid #ddd !important;
        background-color: #ffffff !important; /* Force white background */
        color: #000000 !important; /* Force black text */
    }

    /* Force black text for all nested elements */
    .observation-box *, .state-box *, .grade-box * {
        color: #000000 !important;
        background-color: transparent !important;
    }

    /* Baseline Result Aesthetics */
    .baseline-box {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
        padding: 30px !important;
        border-radius: 12px !important;
        border-left: 10px solid #6c757d !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1) !important;
        min-height: 400px !important;
    }

    .baseline-box * {
        color: #1a1a1a !important;
    }

    /* Hover effects */
    .observation-box:hover, .state-box:hover, .grade-box:hover, .baseline-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0, 0, 0, 0.2);
    }

    /* Premium border-left tints */
    .observation-box { border-color: #4a90d9 !important; border-left: 6px solid #4a90d9 !important; }
    .state-box { border-color: #5cb85c !important; border-left: 6px solid #5cb85c !important; }
    .grade-box { border-color: #f0ad4e !important; border-left: 6px solid #f0ad4e !important; }

    /* Headers / Labels outside the boxes */
    .gradio-container h1, .gradio-container h2, .gradio-container h3 {
        color: #ffffff !important; /* Keep headers white on dark background */
    }
    
    button.primary, button.secondary {
        color: white !important;
        font-weight: 600 !important;
    }
    """

    # Theme
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="green",
    )

    with gr.Blocks(
        title="SupportEnv - Customer Support RL Environment",
    ) as demo:

        gr.Markdown("""
        # SupportEnv - Customer Support Reinforcement Learning Environment

        Train and evaluate AI agents on realistic customer support scenarios.
        """)

        with gr.Tabs() as tabs:

            # ============== Tab 1: Interactive Environment ==============
            with gr.TabItem("Interactive Environment", id=1):
                gr.Markdown("""
                ## Interact with the Environment

                Manually control an agent or test different strategies.
                """)

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Episode Controls")

                        difficulty_dropdown = gr.Dropdown(
                            choices=["easy", "medium", "hard"],
                            value="easy",
                            label="Difficulty",
                        )

                        seed_input = gr.Number(
                            label="Seed (optional)",
                            value=42,
                            precision=0,
                        )

                        reset_btn = gr.Button("Start New Episode", variant="primary")

                        gr.Markdown("### Actions")

                        confidence_slider = gr.Slider(
                            minimum=0.0,
                            maximum=1.0,
                            value=1.0,
                            step=0.1,
                            label="Confidence",
                        )

                        with gr.Accordion("Classification", open=True):
                            category_dropdown = gr.Dropdown(
                                choices=["billing", "technical", "account", "general"],
                                label="Category",
                                value="billing",
                            )
                            classify_btn = gr.Button("Classify", variant="secondary")

                        with gr.Accordion("Response", open=True):
                            response_textbox = gr.Textbox(
                                label="Response Message",
                                placeholder="Enter your response to the customer...",
                                lines=3,
                            )
                            respond_btn = gr.Button("Send Response", variant="secondary")

                        with gr.Accordion("Information Gathering", open=False):
                            info_textbox = gr.Textbox(
                                label="Information to Request",
                                placeholder="e.g., Order ID, email address, phone number...",
                                lines=2,
                            )
                            request_info_btn = gr.Button("Request Info", variant="secondary")

                            kb_query_textbox = gr.Textbox(
                                label="KB Search Query",
                                placeholder="e.g., password, refund, billing...",
                                lines=2,
                            )
                            lookup_kb_btn = gr.Button("Lookup in KB", variant="secondary")

                        with gr.Accordion("Escalation & Resolution", open=False):
                            escalate_reason_textbox = gr.Textbox(
                                label="Escalation Reason",
                                placeholder="Explain why this needs human assistance...",
                                lines=3,
                            )
                            escalate_btn = gr.Button("Escalate to Human", variant="stop")

                            resolve_summary_textbox = gr.Textbox(
                                label="Resolution Summary",
                                placeholder="Summarize how the issue was resolved...",
                                lines=3,
                            )
                            resolve_btn = gr.Button("Resolve Ticket", variant="stop")

                        grade_btn = gr.Button("Grade Episode", variant="secondary")

                    with gr.Column(scale=2):
                        gr.Markdown("### Observation")
                        observation_output = gr.Markdown(
                            "Click 'Start New Episode' to begin.",
                            elem_classes=["observation-box"],
                        )

                        gr.Markdown("### State")
                        state_output = gr.Markdown(
                            "No active session",
                            elem_classes=["state-box"],
                        )

                        gr.Markdown("### Grade Result")
                        grade_output = gr.Markdown(
                            "Complete an episode to see the grade.",
                            elem_classes=["grade-box"],
                        )

                # Wire up buttons
                reset_btn.click(
                    fn=env_reset,
                    inputs=[difficulty_dropdown, seed_input],
                    outputs=[
                        observation_output,
                        state_output,
                        classify_btn,
                        respond_btn,
                        request_info_btn,
                        lookup_kb_btn,
                        escalate_btn,
                        resolve_btn,
                    ],
                )

                classify_btn.click(
                    fn=env_classify,
                    inputs=[category_dropdown, confidence_slider],
                    outputs=[observation_output, state_output, grade_output],
                )

                respond_btn.click(
                    fn=env_respond,
                    inputs=[response_textbox, confidence_slider],
                    outputs=[observation_output, state_output, grade_output],
                )

                request_info_btn.click(
                    fn=env_request_info,
                    inputs=[info_textbox, confidence_slider],
                    outputs=[observation_output, state_output, grade_output],
                )

                lookup_kb_btn.click(
                    fn=env_lookup_kb,
                    inputs=[kb_query_textbox, confidence_slider],
                    outputs=[observation_output, state_output, grade_output],
                )

                escalate_btn.click(
                    fn=env_escalate,
                    inputs=[escalate_reason_textbox, confidence_slider],
                    outputs=[observation_output, state_output, grade_output],
                )

                resolve_btn.click(
                    fn=env_resolve,
                    inputs=[resolve_summary_textbox, confidence_slider],
                    outputs=[observation_output, state_output, grade_output],
                )

                grade_btn.click(
                    fn=env_grade,
                    outputs=[grade_output],
                )

            # ============== Tab 2: Baseline Agent ==============
            with gr.TabItem("Baseline Agent", id=2):
                gr.Markdown("""
                ## Baseline Policy Evaluation

                Run the rule-based baseline agent on all difficulty levels.

                The baseline uses keyword matching and template responses.
                Expected scores:
                - Easy: ~0.85
                - Medium: ~0.65
                - Hard: ~0.40
                """)

                baseline_run_btn = gr.Button("Run Baseline on All Difficulties", variant="primary")
                baseline_output = gr.Markdown("Click the button to run the baseline agent.", elem_classes=["baseline-box"])

                baseline_run_btn.click(
                    fn=run_baseline,
                    outputs=[baseline_output],
                )

            # ============== Tab 3: Task Browser ==============
            with gr.TabItem("Task Browser", id=3):
                gr.Markdown("""
                ## Available Tasks

                View all available tasks and their configurations.
                """)

                tasks_refresh_btn = gr.Button("Refresh Tasks", variant="secondary")

                with gr.Row():
                    with gr.Column(scale=2):
                        task_details = gr.Markdown("Click refresh to load tasks.")
                    with gr.Column(scale=1):
                        task_table = gr.Dataframe(
                            label="Tasks Overview",
                            headers=["Difficulty", "Task ID", "Name", "Max Steps", "Description"],
                        )

                tasks_refresh_btn.click(
                    fn=load_tasks,
                    outputs=[task_details, task_table],
                )

            # ============== Tab 4: Metrics Dashboard ==============
            with gr.TabItem("Metrics", id=4):
                gr.Markdown("""
                ## Performance Metrics

                View aggregated performance metrics across all episodes.
                """)

                metrics_refresh_btn = gr.Button("Refresh Metrics", variant="secondary")

                with gr.Row():
                    with gr.Column(scale=1):
                        metrics_summary = gr.Markdown("Click refresh to load metrics.")
                    with gr.Column(scale=1):
                        metrics_table = gr.Dataframe(
                            label="Scores by Difficulty",
                            headers=["Difficulty", "Episodes", "Average", "Best", "Worst"],
                        )

                metrics_refresh_btn.click(
                    fn=load_metrics,
                    outputs=[metrics_summary, metrics_table],
                )

            # ============== Tab 5: Episode History ==============
            with gr.TabItem("History", id=5):
                gr.Markdown("""
                ## Episode History

                Track all episodes run in this session.
                """)

                with gr.Row():
                    history_refresh_btn = gr.Button("Refresh", variant="secondary")
                    history_clear_btn = gr.Button("Clear History", variant="stop")

                with gr.Row():
                    with gr.Column(scale=1):
                        history_summary = gr.Markdown("No episodes yet.")
                    with gr.Column(scale=2):
                        history_table = gr.Dataframe(
                            label="Episode History",
                            headers=["Timestamp", "Difficulty", "Score", "Passed"],
                        )

                history_refresh_btn.click(
                    fn=view_history,
                    outputs=[history_summary, history_table],
                )

                history_clear_btn.click(
                    fn=clear_history,
                    outputs=[history_summary, history_table],
                )

            # ============== Tab 6: Configuration ==============
            with gr.TabItem("Configuration", id=6):
                gr.Markdown("""
                ## System Configuration

                View current system configuration and environment variables.
                """)

                config_refresh_btn = gr.Button("Refresh Configuration", variant="secondary")
                config_output = gr.Markdown("Click refresh to view configuration.")

                config_refresh_btn.click(
                    fn=view_config,
                    outputs=[config_output],
                )

        # Footer
        gr.Markdown("""
        ---
        **SupportEnv** - Customer Support Reinforcement Learning Environment

        Built with Gradio | Supports: Easy, Medium, Hard difficulties
        """)

    return demo, theme, custom_css


# Create the demo for mounting
demo, theme, css = create_gradio_interface()


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True,
        theme=theme,
        css=css,
    )
