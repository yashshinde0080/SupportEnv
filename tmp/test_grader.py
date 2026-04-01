
import requests

def test_grader():
    url = "http://localhost:8001/grader"
    payload = {
        "task_id": "task_easy_faq",
        "episode_data": {
            "trajectory": [
                {"action": {"action_type": "classify", "content": "billing"}, "reward": 0.25},
                {"action": {"action_type": "respond", "content": "I can help with that."}, "reward": 0.3},
                {"action": {"action_type": "resolve", "content": "Closed."}, "reward": 0.4}
            ],
            "difficulty": "easy",
            "is_resolved": True,
            "classification_correct": True,
            "escalation_correct": True,
            "total_steps": 3,
            "max_steps": 5
        }
    }
    
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {response.json()}")
    except:
        print(f"Response text: {response.text}")

if __name__ == "__main__":
    test_grader()
