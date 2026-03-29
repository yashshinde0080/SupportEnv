# PRD: SupportEnv – AI Customer Support RL Environment

## Overview

Build a complete OpenEnv-compliant environment that simulates a real-world customer support system where an AI agent can:

- Classify support tickets
- Generate responses
- Decide escalation
- Resolve issues

### Requirements

- Follow OpenEnv spec: `reset()`, `step()`, `state()`
- Include 3 tasks (easy → medium → hard)
- Include deterministic graders (0.0–1.0)
- Include baseline inference
- Deploy via Docker + Hugging Face Spaces

---

## Task 1: Project Setup & Structure

Create full project structure:

SupportEnv/
├── models.py                    # Typed Action, Observation, State
├── client.py                    # WebSocket client for external use
├── openenv.yaml                 # Environment metadata
├── pyproject.toml               # Package dependencies
├── requirements.txt             # Pip requirements
├── README.md                    # Documentation
│
├── server/
│   ├── __init__.py
│   ├── app.py                   # FastAPI application
│   ├── environment.py           # Core RL logic
│   ├── tasks.py                 # Task definitions (easy/medium/hard)
│   ├── graders.py               # Deterministic scoring
│   ├── reward.py                # Reward computation
│   ├── ticket_generator.py      # Realistic ticket generation
│   ├── utils.py                 # Helper functions
│   └── Dockerfile               # Container definition
│
├── baseline/
│   ├── __init__.py
│   ├── run_baseline.py          # Baseline execution script
│   ├── policy.py                # Rule-based baseline agent
│   └── results.json             # Saved baseline scores
│
├── frontend/
│   ├── __init__.py
│   └── gradio_ui.py             # Gradio interface
│
├── tests/
│   ├── __init__.py
│   ├── test_environment.py
│   ├── test_graders.py
│   ├── test_api.py
│   └── test_baseline.py
│
└── scripts/
    ├── start_local.sh
    ├── validate.sh
    └── deploy.sh

### Requirements

- Follow OpenEnv structure
- All files created (no placeholders)
- Project runs locally without errors

---

## Task 2: Define Typed Models

### Action

- `action_type`: classify | respond | escalate | resolve  
- `content`: string  

### Observation

- `ticket_text`
- `history`
- `customer_sentiment`
- `issue_category`

### State

- `episode_id`
- `step_count`
- `resolved`

### Requirements

- Fully typed (Pydantic)
- OpenEnv compatible
- No missing fields

---

## Task 3: Implement Ticket Generator

### Features

Generate tickets for:
- Billing
- Technical
- Account

Include:
- Difficulty (easy / medium / hard)
- Sentiment score
- Keywords

### Requirements

- Minimum 20 tickets
- Include ambiguous hard cases
- Deterministic with seed

---

## Task 4: Implement Environment Core

### reset()

- Generate new ticket
- Initialize state
- Clear history

### step(action)

Handle:
- classify
- respond
- escalate
- resolve

Return:
- observation
- reward
- done

### state()

- Return metadata

### Requirements

- Multi-step interaction supported
- Episode ends correctly
- No crashes on invalid input

---

## Task 5: Implement Reward System

### Rewards

- Correct classification → +0.2  
- Helpful response → +0.4  
- Correct resolution → +0.2  
- Wrong escalation → -0.3  
- Harmful response → -0.5  

### Requirements

- Step-level rewards
- Not purely binary
- Penalizes bad behavior

---

## Task 6: Implement Grader System

### Evaluate

- Classification accuracy  
- Response quality  
- Escalation correctness  
- Action ordering  
- Efficiency  

### Output
