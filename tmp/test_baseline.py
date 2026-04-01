
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.environment import SupportEnvironment
from baseline.policy import BaselinePolicy

def test_baseline():
    print("Testing baseline policy...")
    try:
        env = SupportEnvironment()
        policy = BaselinePolicy()
        
        difficulty = "easy"
        print(f"Testing difficulty: {difficulty}")
        observation = env.reset(seed=42, difficulty=difficulty)
        policy.reset()
        
        steps = 0
        while not observation.done and steps < 10:
            action = policy.act(observation)
            print(f"Step {steps+1}: Action={action.action_type}")
            observation = env.step(action)
            steps += 1
            
        print("Grading episode...")
        grade_result = env.grade_episode()
        print(f"Score: {grade_result.score}")
        print(f"Feedback: {grade_result.feedback}")
        print("Test PASSED!")
        
    except Exception as e:
        print(f"Test FAILED with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ensure env variables are loaded if needed
    os.environ["USE_LLM_GENERATOR"] = "false" # Force template generator
    test_baseline()
