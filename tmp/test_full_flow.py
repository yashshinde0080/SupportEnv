
import requests
import json

def test_full_flow():
    base_url = "http://localhost:8001"
    
    # 1. Reset
    print("Resetting environment...")
    reset_resp = requests.post(f"{base_url}/api/reset", json={"difficulty": "easy"})
    reset_data = reset_resp.json()
    session_id = reset_data["session_id"]
    print(f"Session ID: {session_id}")
    
    # 2. Step: Classify
    print("Stepping: classify...")
    step1_resp = requests.post(f"{base_url}/api/step", json={
        "session_id": session_id,
        "action_type": "classify",
        "content": "billing"
    })
    print(f"Step 1 Status: {step1_resp.status_code}")
    
    # 3. Step: Respond
    print("Stepping: respond...")
    step2_resp = requests.post(f"{base_url}/api/step", json={
        "session_id": session_id,
        "action_type": "respond",
        "content": "Hello, I can help with your billing inquiry."
    })
    print(f"Step 2 Status: {step2_resp.status_code}")
    
    # 4. Step: Resolve
    print("Stepping: resolve...")
    step3_resp = requests.post(f"{base_url}/api/step", json={
        "session_id": session_id,
        "action_type": "resolve",
        "content": "Issues resolved."
    })
    print(f"Step 3 Status: {step3_resp.status_code}")
    
    # 5. Grade
    print("Grading episode...")
    grade_resp = requests.post(f"{base_url}/grader", json={"session_id": session_id})
    print(f"Grade Status: {grade_resp.status_code}")
    print(f"Grade Result: {json.dumps(grade_resp.json(), indent=2)}")

if __name__ == "__main__":
    test_full_flow()
