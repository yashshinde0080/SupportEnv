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
from pathlib import Path

# Need to ensure the root project directory is in sys.path
# so that root modules like "models" can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from openenv.core.env_server import create_fastapi_app

from server.environment import SupportEnvironment
from server.ticket_generator import TASK_DEFINITIONS
from server.graders import grade_task
from models import SupportAction, SupportObservation, SupportState


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

# Store environment instances for HTTP endpoints
environments: Dict[str, SupportEnvironment] = {}


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
                    "enum": ["classify", "respond", "escalate", "request_info", "resolve"],
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
        
        environments[session_id] = env
        
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
        
        env = environments[request.session_id]
        
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
    
    env = environments[session_id]
    return env.state.model_dump()


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
    
    env = environments[request.session_id]
    result = env.grade_episode()
    
    return {
        "score": result.score,
        "breakdown": result.breakdown,
        "feedback": result.feedback,
        "passed": result.passed
    }


@app.get("/baseline")
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
            )
        }
    }


# Import Gradio UI
import uuid
try:
    from frontend.gradio_ui import create_gradio_interface
    import gradio as gr
    
    demo = create_gradio_interface()
    app = gr.mount_gradio_app(app, demo, path="/web")
except ImportError:
    pass  # Gradio not installed


def main():
    import uvicorn
    # uvicorn.run works better with a string import for hot reload, or just the app var
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()