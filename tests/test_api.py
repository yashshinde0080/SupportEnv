import pytest
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_list_tasks():
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert len(data["tasks"]) > 0

def test_reset_and_step():
    # Test reset endpoint
    reset_payload = {
        "difficulty": "easy",
        "seed": 42
    }
    response = client.post("/api/reset", json=reset_payload)
    assert response.status_code == 200
    reset_data = response.json()
    assert "session_id" in reset_data
    session_id = reset_data["session_id"]
    
    # Test step endpoint
    step_payload = {
        "session_id": session_id,
        "action_type": "classify",
        "content": "billing"
    }
    response = client.post("/api/step", json=step_payload)
    assert response.status_code == 200
    step_data = response.json()
    assert "observation" in step_data
    
    # Test state endpoint
    response = client.get(f"/api/state/{session_id}")
    assert response.status_code == 200
    state_data = response.json()
    assert "step_count" in state_data

def test_grader_endpoint():
    response = client.post("/api/reset", json={"difficulty": "easy", "seed": 42})
    session_id = response.json()["session_id"]
    
    # Grade the newly created empty session
    response = client.post("/grader", json={"session_id": session_id})
    assert response.status_code == 200
    result = response.json()
    assert "score" in result
    assert "passed" in result
    
def test_baseline_endpoint():
    """Test the baseline endpoint returns valid results."""
    response = client.post("/baseline", json={"difficulty": "easy", "seed": 42})
    assert response.status_code == 200
    data = response.json()
    assert "score" in data or "result" in data or "actions" in data
    # Baseline should return some actionable response
    assert data is not None
