# SupportEnv — Customer Support RL Environment

---

<div align="center">

<img src="https://img.shields.io/badge/OpenEnv-Compatible-4F46E5?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0tMiAxNWwtNS01IDEuNDEtMS40MUwxMCAxNC4xN2w3LjU5LTcuNTlMMTkgOGwtOSA5eiIvPjwvc3ZnPg==" alt="OpenEnv Compatible">
<img src="https://img.shields.io/badge/HuggingFace-Space-F59E0B?style=for-the-badge&logo=huggingface&logoColor=white" alt="HuggingFace Space">
<img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge" alt="MIT License">
<img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Ready">

<br/><br/>

**A production-grade reinforcement learning environment for training AI agents on real-world customer support workflows.**

<p>Classify tickets · De-escalate customers · Make escalation decisions · Resolve issues efficiently</p>

[**Quick Start**](#-quick-start) · [**Tasks**](#-tasks) · [**API Reference**](#-api-reference) · [**Reward Structure**](#-reward-structure) · [**Deployment**](#-deployment)

</div>

---

## Why SupportEnv?

Customer support is a **$400B+ industry** where AI agents can deliver immediate, measurable value. Existing RL benchmarks focus on games or synthetic domains — SupportEnv models the messy, high-stakes dynamics of real support operations:

- **Multi-step reasoning** — Agents must sequence actions logically (classify → investigate → respond → resolve)
- **Sentiment-aware responses** — Observations include real-time customer sentiment signals
- **Escalation judgment** — Fraud, legal threats, and sensitive cases must be recognized and routed
- **Efficiency incentives** — Rewards penalize unnecessary steps, training for practical throughput

SupportEnv is designed to be **immediately deployable** as a training signal for production agents, not a research toy.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                        SupportEnv                        │
│                                                          │
│  ┌────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │  FastAPI   │    │   RL Core   │    │   Graders    │   │
│  │  Server    │◄──►│ Environment │◄──►│ (Deterministic│  │
│  │  /reset    │    │  .step()    │    │  Scoring)    │   │
│  │  /step     │    │  .reset()   │    └──────────────┘   │
│  │  /grader   │    └─────────────┘                       │
│  └────────────┘           │                              │
│        │            ┌─────▼──────┐                       │
│        │            │   Tasks    │                       │
│        │            │ Easy/Med/  │                       │
│        │            │   Hard     │                       │
│        │            └────────────┘                       │
│        │                                                 │
│  ┌─────▼──────────────────────────────────────────────┐  │
│  │  WebSocket Client  ←→  Agent Policy                │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option A — Use the Deployed Environment

```python
from support_env.client import SupportEnv
from support_env.models import SupportAction

env = SupportEnv(base_url="https://yashshinde0080-support-env.hf.space")

with env.sync() as client:
    result = client.reset(difficulty="medium")
    print(f"Ticket: {result.observation.ticket_text}")
    print(f"Sentiment: {result.observation.customer_sentiment:.2f}")

    while not result.done:
        action = SupportAction(
            action_type="classify",
            content="billing"
        )
        result = client.step(action)
        print(f"Reward: {result.reward:+.2f} | Steps left: {result.observation.steps_remaining}")
```

### Option B — Run Locally

```bash
# 1. Clone
git clone https://huggingface.co/spaces/yashshinde0080/support-env
cd support-env

# 2. Install
pip install -r requirements.txt

# 3. Start server
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

# 4. Verify
curl http://localhost:8000/health
# → {"status": "ok", "version": "1.0.0"}

# 5. Run baseline agent
python baseline/run_baseline.py --verbose
```

### Option C — Docker

```bash
docker build -t support-env:latest -f server/Dockerfile .
docker run -p 7860:7860 support-env:latest

# Confirm
curl http://localhost:7860/health
```

---

## 📁 Project Structure

```
support_env/
├── models.py                   # Typed dataclasses: Action, Observation, State
├── client.py                   # WebSocket client with sync/async context managers
├── openenv.yaml                # OpenEnv environment manifest
│
├── server/
│   ├── app.py                  # FastAPI application, route definitions
│   ├── environment.py          # Core RL logic: reset(), step(), state transitions
│   ├── tasks.py                # Task configs: Easy / Medium / Hard
│   ├── graders.py              # Deterministic scoring (classification, response, escalation)
│   ├── reward.py               # Reward computation and shaping
│   └── Dockerfile              # Production container definition
│
├── baseline/
│   ├── run_baseline.py         # End-to-end baseline runner with reporting
│   └── policy.py               # Rule-based reference agent
│
├── frontend/
│   └── gradio_ui.py            # Gradio web interface at /web
│
└── tests/
    ├── test_environment.py     # Environment unit tests
    └── test_graders.py         # Grader determinism and edge case tests
```

---

## 📋 Tasks

Three progressive difficulty levels, each with distinct action sequences and scoring weights.

### Task 1 · FAQ Resolution `easy`

> Handle common queries: password resets, account access, store hours, basic billing questions.

| Property | Value |
|---|---|
| Max Steps | 5 |
| Expected Sequence | `classify → respond → resolve` |
| Baseline Score | **0.75** |
| Escalation Rate | ~2% |
| Key Challenge | Speed — efficiency bonus is weighted heavily |

```python
result = client.reset(difficulty="easy")
# Typical ticket: "How do I reset my password? I can't log in."
```

---

### Task 2 · Multi-Step Issue Handling `medium`

> Handle billing disputes, technical bugs requiring investigation, account anomalies needing verification.

| Property | Value |
|---|---|
| Max Steps | 8 |
| Expected Sequence | `classify → request_info → respond → resolve` |
| Baseline Score | **0.73** |
| Escalation Rate | ~15% |
| Key Challenge | Knowing when to gather more information vs. respond directly |

```python
result = client.reset(difficulty="medium")
# Typical ticket: "I was charged twice for my subscription last month."
```

---

### Task 3 · Complex Escalation Handling `hard`

> Handle angry customers, fraud reports, legal threats, and sensitive account issues requiring human judgment.

| Property | Value |
|---|---|
| Max Steps | 10 |
| Expected Sequence | `classify → respond (de-escalate) → escalate` |
| Baseline Score | **0.82** |
| Escalation Rate | ~60% |
| Key Challenge | Detecting genuine escalation signals vs. venting; missed escalations are heavily penalized |

```python
result = client.reset(difficulty="hard")
# Typical ticket: "This is fraud. I'm contacting my bank and a lawyer."
```

---

## 🎮 Action Space

All actions are submitted as `SupportAction` objects.

```python
from support_env.models import SupportAction

# Classify the ticket type
SupportAction(action_type="classify", content="billing")
# content options: "billing" | "technical" | "account" | "general"

# Send a response to the customer
SupportAction(
    action_type="respond",
    content="I understand your frustration. Let me look into this charge right away..."
)

# Escalate to a human agent
SupportAction(
    action_type="escalate",
    content="Customer reporting potential fraud. Immediate human review required."
)

# Request more information
SupportAction(
    action_type="request_info",
    content="Could you provide your order number so I can investigate?"
)

# Mark the issue as resolved
SupportAction(
    action_type="resolve",
    content="Refund of $29.99 processed. Customer confirmed satisfaction."
)
```

| `action_type` | Description | `content` Format |
|---|---|---|
| `classify` | Categorize the ticket | One of: `billing`, `technical`, `account`, `general` |
| `respond` | Send a reply to the customer | Free-form response text |
| `escalate` | Route to a human agent | Reason for escalation |
| `request_info` | Ask the customer for more detail | Specific question or info needed |
| `resolve` | Close the ticket | Resolution summary |

---

## 👁️ Observation Space

Every `step()` and `reset()` returns a `StepResult` containing a `SupportObservation`.

```python
@dataclass
class SupportObservation:
    # === Ticket ===
    ticket_id: str                      # Unique ticket identifier
    ticket_text: str                    # Full customer message body
    ticket_subject: str                 # Email/chat subject line
    customer_name: str                  # Customer display name

    # === Context ===
    interaction_history: List[Dict]     # Prior agent/customer turns
    customer_sentiment: float           # -1.0 (furious) → 0.0 (neutral) → 1.0 (delighted)

    # === State Flags ===
    current_classification: Optional[str]   # Set after classify action
    is_classified: bool
    is_escalated: bool

    # === Episode Meta ===
    task_difficulty: str                # "easy" | "medium" | "hard"
    steps_remaining: int
    max_steps: int
```

**Sentiment signal** — `customer_sentiment` updates each step based on the quality of agent responses. De-escalation actions that improve sentiment before escalation receive partial credit.

---

## 💰 Reward Structure

Rewards are shaped to encourage both correctness and efficiency.

### Per-Action Rewards

| Action & Outcome | Reward |
|---|---|
| ✅ Correct classification | `+0.25` |
| ✅ High-quality empathetic response | `+0.30` |
| ✅ Correct escalation decision | `+0.35` |
| ✅ Successful resolution | `+0.40` |
| ✅ Efficiency bonus (resolved under step budget) | `+0.10` |
| ❌ Incorrect classification | `-0.15` |
| ❌ Harmful or inappropriate response | `-0.40` |
| ❌ Missed mandatory escalation | `-0.35` |
| ❌ Unnecessary escalation | `-0.20` |

### Response Quality Scoring

Response quality is scored along three axes, then averaged:

```
response_score = (empathy_score + solution_score + appropriateness_score) / 3
```

- **Empathy** — Does the response acknowledge the customer's frustration or situation?
- **Solution** — Does it address the root issue or ask for the right information?
- **Appropriateness** — Is the tone and length appropriate for the context?

### Escalation Detection

The grader identifies mandatory escalation signals in ticket text:

- Explicit mentions of fraud, chargebacks, or unauthorized transactions
- Legal threats (`"lawyer"`, `"attorney"`, `"sue"`, `"legal action"`)
- Safety concerns or threatening language
- Regulatory keywords (`"GDPR"`, `"FTC"`, `"data breach"`)

Missing any of these in a `hard` task triggers the `-0.35` missed escalation penalty.

---

## 📊 Grading

Scores are computed **deterministically** — given the same episode trajectory, the grader always returns the same score. No stochastic components in scoring.

### Score Composition by Difficulty

| Component | Easy Weight | Medium Weight | Hard Weight |
|---|---|---|---|
| Classification accuracy | 30% | 20% | 15% |
| Response quality | 40% | 35% | 20% |
| Escalation decision | 5% | 15% | 30% |
| Resolution | 15% | 20% | 20% |
| Efficiency | 10% | 10% | 15% |

### Using the Grader Endpoint

```python
import httpx

# After completing an episode
response = httpx.post("http://localhost:8000/grader", json={
    "episode_id": "ep_abc123",
    "trajectory": [
        {"action": "classify", "content": "billing", "reward": 0.25},
        {"action": "respond", "content": "...", "reward": 0.28},
        {"action": "resolve", "content": "...", "reward": 0.40}
    ]
})

result = response.json()
print(f"Final score: {result['score']:.3f}")
print(f"Breakdown: {result['breakdown']}")
```

---

## 🔌 API Reference

Full REST API. All endpoints return JSON.

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check and version info |
| `POST` | `/reset` | Start a new episode |
| `POST` | `/step` | Submit an action, receive next observation |
| `GET` | `/state/{episode_id}` | Retrieve full episode state |
| `POST` | `/grader` | Score a completed episode trajectory |
| `GET` | `/tasks` | List all available tasks with metadata |
| `GET` | `/baseline` | Run the reference baseline agent |
| `GET` | `/web` | Gradio UI (browser) |

### `POST /reset`

```json
// Request
{
  "difficulty": "medium",         // "easy" | "medium" | "hard"
  "seed": 42                      // Optional — for reproducibility
}

// Response
{
  "episode_id": "ep_abc123",
  "observation": {
    "ticket_id": "TKT-8821",
    "ticket_text": "I was charged twice this month...",
    "ticket_subject": "Double charge on account",
    "customer_name": "Alex Chen",
    "customer_sentiment": -0.42,
    "is_classified": false,
    "is_escalated": false,
    "steps_remaining": 8,
    "max_steps": 8,
    "interaction_history": []
  },
  "done": false,
  "reward": 0.0
}
```

### `POST /step`

```json
// Request
{
  "episode_id": "ep_abc123",
  "action": {
    "action_type": "classify",
    "content": "billing"
  }
}

// Response
{
  "episode_id": "ep_abc123",
  "observation": { "...updated state..." },
  "reward": 0.25,
  "done": false,
  "info": {
    "classification_correct": true,
    "sentiment_delta": 0.05
  }
}
```

---

## 📈 Baseline Results

The reference rule-based agent (`baseline/policy.py`) uses keyword matching and heuristic escalation detection.

| Task | Score | Avg Reward | Avg Steps | Escalation Accuracy |
|---|---|---|---|---|
| Easy | 0.75 | 0.92 | 3.1 | 100% |
| Medium | 0.73 | 0.58 | 5.3 | 73% |
| Hard | 0.82 | 0.25 | 4.2 | 61% |
| **Average** | **0.77** | — | — | — |

The baseline is intentionally limited — it cannot reason about response quality or adapt tone. A well-trained RL agent should comfortably exceed these scores, especially on hard tasks.

---

## 🧪 Testing & Validation

### Run Tests

```bash
# Full test suite
pytest tests/ -v

# Specific modules
pytest tests/test_environment.py -v
pytest tests/test_graders.py -v

# With coverage report
pytest tests/ --cov=server --cov-report=html
```

### Run OpenEnv Validation

```bash
# Validates manifest, endpoints, and score determinism
openenv validate

# Expected output:
# ✓ /health returns 200
# ✓ /reset returns valid observation
# ✓ /step returns reward + done flag
# ✓ /tasks returns task list
# ✓ /grader returns [0.0, 1.0] score
# ✓ Grader is deterministic (10/10 runs match)
# ✓ Baseline runs without error
# All checks passed.
```

### Grader Determinism Test

```python
# Graders must be deterministic — same trajectory → same score
from server.graders import EpisodeGrader

grader = EpisodeGrader()
trajectory = load_trajectory("tests/fixtures/medium_trajectory.json")

scores = [grader.score(trajectory) for _ in range(100)]
assert len(set(scores)) == 1, "Grader is non-deterministic!"
```

---

## 🚀 Deployment

### Local Development

```bash
# Hot-reload server
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

# Run baseline with verbose output
python baseline/run_baseline.py --verbose --difficulty hard

# Validate before pushing
openenv validate
```

### Docker

```bash
# Build
docker build -t support-env:latest -f server/Dockerfile .

# Run
docker run -p 7860:7860 support-env:latest

# Health check
curl http://localhost:7860/health
```

### HuggingFace Spaces

```bash
# Authenticate
huggingface-cli login

# Push via OpenEnv CLI
openenv push --repo-id yashshinde0080/support-env

# Or manually via git
git init
git remote add origin https://huggingface.co/spaces/yashshinde0080/support-env
git add .
git commit -m "feat: initial SupportEnv deployment"
git push origin main
```

**Required Spaces hardware:** CPU Basic (2 vCPU, 16GB RAM) is sufficient for all tasks. GPU is not required.

---

## ✅ Pre-Submission Checklist

**Core Environment**
- [x] `reset()` returns a valid `SupportObservation`
- [x] `step()` returns `reward` (float) and `done` (bool)
- [x] `state/{id}` returns full episode metadata
- [x] 3 tasks with progressive difficulty implemented

**Scoring**
- [x] Graders return scores in `[0.0, 1.0]`
- [x] Graders are deterministic (same trajectory → same score)
- [x] Baseline produces reproducible scores across runs

**API**
- [x] `/tasks` endpoint responds correctly
- [x] `/grader` endpoint accepts trajectory and returns score
- [x] `/baseline` endpoint runs without error
- [x] `/health` returns HTTP 200

**Deployment**
- [x] Docker builds without errors
- [x] Docker runs without errors
- [x] HuggingFace Space deploys successfully
- [x] `openenv validate` passes all checks

**Quality**
- [x] README is complete
- [x] All tests pass (`pytest tests/ -v`)
- [x] No hardcoded secrets or API keys

---

## 🤝 Contributing

Contributions are welcome — especially new task scenarios, improved grading heuristics, and alternative baseline agents.

```bash
# 1. Fork and clone
git clone https://github.com/yashshinde0080/support-env
cd support-env

# 2. Create a feature branch
git checkout -b feat/new-escalation-scenarios

# 3. Install dev dependencies
pip install -r requirements-dev.txt

# 4. Make changes and test
pytest tests/ -v

# 5. Submit pull request
```

**Areas most in need of contribution:**
- New ticket templates for edge cases (multilingual, multi-issue tickets)
- Advanced models for empathy analysis and semantic grading
- Async WebSocket client improvements
- Additional baseline agents (LLM-based, retrieval-augmented)

---

## 📚 References

- [OpenEnv Documentation](https://openenv.dev/docs)
- [HuggingFace Spaces](https://huggingface.co/spaces)
- [FastAPI](https://fastapi.tiangolo.com)
- [Gradio](https://gradio.app)
- [Gymnasium (RL interface standard)](https://gymnasium.farama.org)

---

## 📜 License

MIT License — see [`LICENSE`](LICENSE) for full terms.

---

<div align="center">

Built for the OpenEnv ecosystem · [Report an issue](https://github.com/yashshinde0080/support-env/issues) · [Discuss](https://github.com/yashshinde0080/support-env/discussions)

</div>