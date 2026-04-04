import unittest
import asyncio
import httpx
import uuid
import time
from server.app import app

class TestConcurrency(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_sessions(self):
        """Verify that multiple sessions maintain independent state."""
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Reset two separate sessions
            session_a = str(uuid.uuid4())
            session_b = str(uuid.uuid4())
            
            resp_a = await client.post("/api/reset", json={"session_id": session_a, "difficulty": "easy"})
            resp_b = await client.post("/api/reset", json={"session_id": session_b, "difficulty": "hard"})
            
            self.assertEqual(resp_a.status_code, 200)
            self.assertEqual(resp_b.status_code, 200)
            
            data_a = resp_a.json()
            data_b = resp_b.json()
            
            # 2. Verify settings are different
            self.assertEqual(data_a["observation"]["task_difficulty"], "easy")
            self.assertEqual(data_b["observation"]["task_difficulty"], "hard")
            
            # 3. Take a step in A
            await client.post("/api/step", json={
                "session_id": session_a,
                "action_type": "classify",
                "content": "billing"
            })
            
            # 4. Check state of both
            state_a_resp = await client.get(f"/api/state/{session_a}")
            state_b_resp = await client.get(f"/api/state/{session_b}")
            
            state_a = state_a_resp.json()
            state_b = state_b_resp.json()
            
            self.assertEqual(state_a["step_count"], 1)
            self.assertEqual(state_b["step_count"], 0)
            
            print(f"Concurrency verified: Session A (steps={state_a['step_count']}), Session B (steps={state_b['step_count']})")

if __name__ == "__main__":
    unittest.main()
