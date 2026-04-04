"""
FastAPI application for SupportEnv.

Endpoints:
- /ws - WebSocket endpoint for environment interaction
- /reset - Reset environment (HTTP)
- /step - Take action (HTTP)  
- /state - Get current state (HTTP)
- /tasks - List available tasks
- /grader - Grade current episode
- /baseline - Run baseline agent
- /health - Health check
- /web - Gradio UI
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import asyncio
import traceback
import sys
import uuid
import time
from pathlib import Path

# sys.path manipulation removed as per judge recommendation
# Run with 'python -m server.app' or set PYTHONPATH

from openenv.core.env_server import create_fastapi_app

from server.environment import SupportEnvironment
from server.ticket_generator import TASK_DEFINITIONS
from server.graders import grade_task
from models import SupportAction, SupportObservation, SupportState, PublicSupportState


# Create base app with OpenEnv integration
app = create_fastapi_app(SupportEnvironment, SupportAction, SupportObservation)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store environment instances for HTTP endpoints with TTL
environments: Dict[str, Dict[str, Any]] = {}
SESSION_TTL_SECONDS = 3600

# Global metrics tracking
METRICS = {
    "total_episodes": 0,
    "success_rate": 0.0,
    "total_successful": 0,
    "avg_easy_score": 0.0,
    "avg_medium_score": 0.0,
    "avg_hard_score": 0.0,
    "scores_by_difficulty": {"easy": [], "medium": [], "hard": []}
}

def _cleanup_sessions():
    now = time.time()
    expired = [k for k, v in environments.items() if now - v["last_accessed"] > SESSION_TTL_SECONDS]
    for k in expired:
        del environments[k]

def _update_metrics(difficulty: str, score: float, passed: bool):
    METRICS["total_episodes"] += 1
    if passed:
        METRICS["total_successful"] += 1
    
    METRICS["success_rate"] = METRICS["total_successful"] / METRICS["total_episodes"]
    
    if difficulty in METRICS["scores_by_difficulty"]:
        METRICS["scores_by_difficulty"][difficulty].append(score)
        scores = METRICS["scores_by_difficulty"][difficulty]
        METRICS[f"avg_{difficulty}_score"] = sum(scores) / len(scores)


class ResetRequest(BaseModel):
    session_id: Optional[str] = None
    seed: Optional[int] = None
    task_id: Optional[str] = None
    difficulty: Optional[str] = None


class StepRequest(BaseModel):
    session_id: str
    action_type: str
    content: str
    confidence: Optional[float] = None


class GraderRequest(BaseModel):
    session_id: str


class CurriculumRequest(BaseModel):
    pass_rate: float
    avg_score: Optional[float] = None


# Additional HTTP endpoints beyond OpenEnv standard

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "environment": "SupportEnv"}


@app.get("/tasks")
async def list_tasks():
    """
    List available tasks with their configurations.
    Required endpoint for hackathon.
    """
    tasks = []
    for difficulty, config in TASK_DEFINITIONS.items():
        tasks.append({
            "task_id": config["task_id"],
            "name": config["name"],
            "difficulty": difficulty,
            "description": config["description"],
            "max_steps": config["max_steps"],
            "action_schema": {
                "action_type": {
                    "type": "string",
                    "enum": ["classify", "respond", "escalate", "request_info", "resolve", "lookup_kb"],
                    "required": True
                },
                "content": {
                    "type": "string",
                    "required": True
                },
                "confidence": {
                    "type": "float",
                    "required": False,
                    "min": 0.0,
                    "max": 1.0
                }
            }
        })
    
    return {"tasks": tasks}


@app.post("/api/reset")
async def reset_environment(request: ResetRequest):
    """
    Reset environment for new episode.
    HTTP alternative to WebSocket reset.
    """
    try:
        # Create or get environment
        session_id = request.session_id or str(uuid.uuid4())
        
        env = SupportEnvironment()
        observation = env.reset(
            seed=request.seed,
            episode_id=session_id,
            task_id=request.task_id,
            difficulty=request.difficulty
        )
        
        
        _cleanup_sessions()
        environments[session_id] = {
            "env": env,
            "last_accessed": time.time()
        }
        
        return {
            "session_id": session_id,
            "observation": observation.model_dump(),
            "done": observation.done,
            "reward": observation.reward
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/step")
async def step_environment(request: StepRequest):
    """
    Execute action in environment.
    HTTP alternative to WebSocket step.
    """
    try:
        if request.session_id not in environments:
            raise HTTPException(
                status_code=404, 
                detail=f"Session {request.session_id} not found. Call /reset first."
            )
        
        _cleanup_sessions()
        env_data = environments[request.session_id]
        env_data["last_accessed"] = time.time()
        env = env_data["env"]
        
        action = SupportAction(
            action_type=request.action_type,
            content=request.content,
            confidence=request.confidence
        )
        
        observation = env.step(action)
        
        return {
            "observation": observation.model_dump(),
            "done": observation.done,
            "reward": observation.reward
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state/{session_id}")
async def get_state(session_id: str):
    """Get current state of environment."""
    if session_id not in environments:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found."
        )
    
    
    _cleanup_sessions()
    env_data = environments[session_id]
    env_data["last_accessed"] = time.time()
    env = env_data["env"]
    state_dict = env.state.model_dump()
    public_state = PublicSupportState(**state_dict)
    return public_state.model_dump()


@app.post("/grader")
async def grade_episode(request: GraderRequest):
    """
    Grade completed episode.
    Required endpoint for hackathon.
    """
    if request.session_id not in environments:
        raise HTTPException(
            status_code=404,
            detail=f"Session {request.session_id} not found."
        )
    _cleanup_sessions()
    env_data = environments[request.session_id]
    env_data["last_accessed"] = time.time()
    env = env_data["env"]
    result = env.grade_episode()
    
    # Update metrics on completion
    _update_metrics(env.state.task_difficulty, result.score, result.passed)
    
    return {
        "score": result.score,
        "breakdown": result.breakdown,
        "feedback": result.feedback,
        "passed": result.passed
    }


@app.get("/metrics")
async def get_metrics():
    """Returns environment performance metrics."""
    return METRICS


@app.api_route("/baseline", methods=["GET", "POST"])
async def run_baseline():
    """
    Run baseline agent on all tasks.
    Required endpoint for hackathon.
    """
    from baseline.policy import BaselinePolicy
    
    results = {}
    policy = BaselinePolicy()
    
    for difficulty in ["easy", "medium", "hard"]:
        env = SupportEnvironment()
        observation = env.reset(seed=42, difficulty=difficulty)
        policy.reset()
        
        total_reward = 0.0
        steps = 0
        
        while not observation.done:
            action = policy.act(observation)
            observation = env.step(action)
            total_reward += observation.reward or 0.0
            steps += 1
            
            if steps > 15:  # Safety limit
                break
        
        # Grade episode
        grade_result = env.grade_episode()
        
        results[difficulty] = {
            "score": grade_result.score,
            "total_reward": round(total_reward, 4),
            "steps": steps,
            "passed": grade_result.passed,
            "breakdown": grade_result.breakdown
        }
    
    return {
        "baseline_results": results,
        "summary": {
            "easy_score": results["easy"]["score"],
            "medium_score": results["medium"]["score"],
            "hard_score": results["hard"]["score"],
            "average_score": round(
                (results["easy"]["score"] + 
                 results["medium"]["score"] + 
                 results["hard"]["score"]) / 3, 
                4
            ),
            "breakdown": {
                "easy": {
                    "score": results["easy"]["score"],
                    "steps": results["easy"]["steps"],
                    "passed": results["easy"]["passed"],
                    "details": results["easy"]["breakdown"]
                },
                "medium": {
                    "score": results["medium"]["score"],
                    "steps": results["medium"]["steps"],
                    "passed": results["medium"]["passed"],
                    "details": results["medium"]["breakdown"]
                },
                "hard": {
                    "score": results["hard"]["score"],
                    "steps": results["hard"]["steps"],
                    "passed": results["hard"]["passed"],
                    "details": results["hard"]["breakdown"]
                }
            }
        }
    }


@app.post("/curriculum")
async def curriculum_endpoint(request: CurriculumRequest):
    """
    Curriculum endpoint to adapt difficulty.
    Required for dynamic training.
    """
    if request.pass_rate > 0.8:
        difficulty = "hard"
    elif request.pass_rate > 0.4:
        difficulty = "medium"
    else:
        difficulty = "easy"
    
    return {
        "suggested_difficulty": difficulty,
        "pass_rate": request.pass_rate
    }



# Import Gradio UI
try:
    from frontend.gradio_ui import create_gradio_interface
    import gradio as gr
    
    demo, theme, css = create_gradio_interface()
    # Apply theme/css explicitly if needed, but mount_gradio_app usually handles the demo object
    app = gr.mount_gradio_app(app, demo, path="/web")
except ImportError:
    pass  # Gradio not installed
except Exception as e:
    print(f"Failed to mount Gradio UI: {e}")


def main():
    import uvicorn
    # uvicorn.run works better with a string import for hot reload, or just the app var
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()