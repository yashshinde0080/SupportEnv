# 🛠 Project Improvement Roadmap (improve_new_1.md)

This document outlines the top priority improvements required to make the **Root Project (D:/SupportEnv)** superior in both structure and technical compliance for the hackathon.

## 🔴 1. Critical: Reward Clamping (The "Hackathon-Critical" Fix)
Currently, the root project calculates rewards that can exceed the `(0, 1)` range. Many automated evaluators will reject episodes containing rewards exactly at `0.0`, `1.0`, or outside these bounds.

### Improvement:
Apply strict clamping in `server/environment.py` within the `step()` method.
```diff
- reward = reward_breakdown.total
- self._state.total_reward += reward
+ # Add strictly inside (0, 1) clamping
+ raw_reward = reward_breakdown.total
+ reward = max(0.01, min(0.99, float(raw_reward))) 
+ self._state.total_reward += raw_reward  # Track true reward internally
```

---

## 🟡 2. Grader & Reward Logic Alignment
In `server/reward.py` and `server/graders.py`, the weights for "efficiency" and "empathy" vary slightly. This can cause a discrepancy where an agent receives a high reward during the episode but a lower final grade.

### Improvement:
- Standardize the `weighted_total` compute logic.
- Ensure `compute_episode_final_reward` in `reward.py` also uses the `0.01-0.99` clamping logic before returning.

---

## 🟢 3. Semantic Scorer Robustness
The current `server/semantic_scorer.py` depends on an LLM or specific library availability. If it fails, it returns `None`.

### Improvement:
- Implement a **Weighted Keyword Overlap** fallback within the semantic scorer itself if the primary model is unavailable. This ensures the agent always gets a meaningful (and deterministic) signal, which judges love for reproducibility.

---

## 🔵 4. UI: Performance Analytics
The Gradio UI is beautiful, but it doesn't persist metrics between refreshes for the judge to see.

### Improvement:
- **Local Persistence**: Save `GLOBAL_METRICS` to a `metrics.json` file in the root.
- **Visuals**: Add a "Success Rate Trend" plot using Gradio's `gr.LinePlot` to show the agent's performance over multiple episodes.

---

## 🟣 5. Project Cleanup (The "Root is King" Strategy)
Ensure no remnants of the nested `SupportEnv/SupportEnv` structure remain.

### Improvement:
- Delete any empty `__init__.py` files in the root that might cause shadowing (e.g., if there's a `SupportEnv/__init__.py` making the root itself a package).
- Verify `pyproject.toml` entry points point correctly to `app.py`.

---
**Verdict:** Implementing Section 1 and 2 immediately elevates the root project from "Clean but Risky" to "Production Grade / Winning Quality."
