# 🚀 SupportEnv — Road to 95+/100

> **Current Score**: ~72/100
> **Target Score**: 95+/100
> **Gap**: +23 points across 5 rubric categories

---

## Score Gap Analysis

| Parameter | Weight | Current | Target | Gap | Points Available |
|---|---|---|---|---|---|
| Real-world utility | 30% | 23.4 | 28.5 | +5.1 | Must reach 95% of weight |
| Task & grader quality | 25% | 17.0 | 23.5 | +6.5 | **LARGEST GAIN AREA** |
| Environment design | 20% | 14.4 | 19.0 | +4.6 | State leak fix + reward polish |
| Code quality & spec compliance | 15% | 10.5 | 14.0 | +3.5 | Fix critical bugs + tests |
| Creativity & novelty | 10% | 6.5 | 9.5 | +3.0 | Novel mechanics needed |
| **TOTAL** | **100%** | **71.8** | **94.5** | **+22.7** | — |

---

## 🔴 PHASE 1 — Critical Fixes (Do These FIRST)

> These are blocking issues. If you don't fix these, nothing else matters.
> **Estimated gain: +12 points**

---

### Fix 1.1 — Kill the Difficulty Inversion (Hard > Easy scores)

**Problem**: Baseline scores 0.80 on hard but only 0.70 on easy. Judges will flag this instantly.

**Root Cause**: Hard tickets ALL have obvious escalation keywords → baseline detects them trivially → escalation has 30% weight in hard → free 1.0. Plus hard has 12 max_steps but baseline finishes in 3 → efficiency = 1.0 (another free perfect score).

**Fix — In `server/graders.py`**:

```python
# === CHANGE 1: Require de-escalation attempt BEFORE escalation gets full credit ===
# Replace _grade_escalation() entirely:

def _grade_escalation(
    self,
    action_history: List[Dict[str, Any]],
    should_escalate: bool
) -> float:
    """Grade escalation decision — requires empathetic response before escalation."""
    escalations = [a for a in action_history if a.get("type") == "escalate"]
    responses = [a for a in action_history if a.get("type") == "respond"]
    escalated = len(escalations) > 0

    if should_escalate and escalated:
        reason = escalations[0].get("content", "")
        reason_quality = 0.0

        # Must have detailed reason (10+ words with specific keywords)
        if len(reason.split()) >= 10 and any(kw in reason.lower() for kw in ["immediate", "severity", "sensitivity", "human", "safety", "legal", "fraud"]):
            reason_quality = 1.0
        elif len(reason.split()) >= 5:
            reason_quality = 0.7
        else:
            reason_quality = 0.4

        # *** NEW: Require at least one empathetic response BEFORE escalation ***
        # De-escalation attempt is critical for hard tasks
        responded_before_escalation = False
        escalation_step = escalations[0].get("step", 999)
        for resp in responses:
            if resp.get("step", 999) < escalation_step:
                content = resp.get("content", "").lower()
                has_empathy = any(kw in content for kw in ["understand", "sorry", "apologize", "help", "frustrating"])
                if has_empathy:
                    responded_before_escalation = True
                    break

        if responded_before_escalation:
            return reason_quality  # Full credit range
        else:
            return reason_quality * 0.5  # Halved — escalated without empathy first

    elif not should_escalate and not escalated:
        return 1.0
    elif should_escalate and not escalated:
        return 0.0
    else:
        return 0.1
```

```python
# === CHANGE 2: Cap efficiency score for hard tasks ===
# In _grade_efficiency(), penalize hard tasks that finish too fast (indicates superficial handling):

def _grade_efficiency(self, steps: int, max_steps: int, difficulty: str = "easy") -> float:
    """Grade step efficiency — hard tasks should NOT be rewarded for rushing."""
    if steps <= 1:
        if difficulty == "hard":
            return 0.4  # Suspiciously fast for complex escalation
        return 1.0
    elif steps >= max_steps:
        return 0.2
    else:
        base = round(1.0 - 0.8 * ((steps - 1) / (max_steps - 1)), 2)
        # Hard tasks: penalize finishing in under 3 steps (too rushed)
        if difficulty == "hard" and steps < 3:
            base *= 0.5
        elif difficulty == "medium" and steps < 2:
            base *= 0.7
        return base
```

Then update the call site in `grade_episode()`:
```python
efficiency_score = self._grade_efficiency(total_steps, max_steps, task_difficulty)
```

```python
# === CHANGE 3: Add hard-specific de-escalation grading component ===
# In grade_episode(), add a new scoring dimension for hard tasks:

# After computing escalation_score, ADD:
if task_difficulty == "hard":
    deescalation_score = self._grade_deescalation(action_history)
    breakdown["deescalation_attempt"] = deescalation_score
```

```python
def _grade_deescalation(self, action_history: List[Dict[str, Any]]) -> float:
    """Grade whether agent attempted to de-escalate before escalating (hard tasks only)."""
    responses = [a for a in action_history if a.get("type") == "respond"]
    escalations = [a for a in action_history if a.get("type") == "escalate"]

    if not escalations:
        return 0.3  # Didn't escalate at all

    # Check if there was a response before escalation
    escalation_step = escalations[0].get("step", 999)
    pre_escalation_responses = [r for r in responses if r.get("step", 999) < escalation_step]

    if not pre_escalation_responses:
        return 0.0  # Jumped straight to escalation — no de-escalation attempt

    # Check response quality (empathy + acknowledgment)
    best_score = 0.0
    for resp in pre_escalation_responses:
        content = resp.get("content", "").lower()
        empathy = sum(1 for kw in ["understand", "sorry", "apologize", "frustrating", "help"] if kw in content)
        solution = sum(1 for kw in ["looking into", "investigating", "let me", "I'll"] if kw in content)
        score = min(1.0, empathy * 0.25 + solution * 0.25)
        best_score = max(best_score, score)

    return best_score
```

And update hard weights:
```python
# hard weights — add deescalation, reduce efficiency
else:  # hard
    return {
        "classification": 0.15,
        "response_quality": 0.15,
        "escalation_decision": 0.25,
        "deescalation_attempt": 0.15,  # NEW
        "resolution": 0.20,
        "efficiency": 0.10  # REDUCED from 0.15
    }
```

**Expected result after fix**: Hard baseline drops to ~0.45-0.55. Easy stays at ~0.75. Proper difficulty curve restored.

---

### Fix 1.2 — Hide Target Info from State Endpoint

**Problem**: `state()` exposes `target_category` and `target_resolution`. Any agent can cheat.

**Fix — In `models.py`, add a public state model**:

```python
class PublicSupportState(State):
    """State information safe to expose to agents (no answer leaks)."""
    task_id: str = ""
    task_difficulty: str = ""
    max_steps: int = 10
    resolved: bool = False
    total_reward: float = 0.0
    # NOTE: target_category, target_resolution, requires_escalation are HIDDEN
```

**Fix — In `server/environment.py`**:

```python
@property
def public_state(self) -> PublicSupportState:
    """Return agent-safe state (no target info leaked)."""
    return PublicSupportState(
        episode_id=self._state.episode_id,
        step_count=self._state.step_count,
        task_id=self._state.task_id,
        task_difficulty=self._state.task_difficulty,
        max_steps=self._state.max_steps,
        resolved=self._state.resolved,
        total_reward=self._state.total_reward,
    )
```

**Fix — In `server/app.py`**, change the state endpoint:

```python
@app.get("/api/state/{session_id}")
async def get_state(session_id: str):
    """Get current state of environment (agent-safe, no target info)."""
    if session_id not in environments:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")
    _cleanup_sessions()
    env_data = environments[session_id]
    env_data["last_accessed"] = time.time()
    env = env_data["env"]
    return env.public_state.model_dump()  # <-- Use public_state
```

---

### Fix 1.3 — Fix inference.py to Report Grader Scores

**Problem**: `inference.py` never calls `/grader` and never prints final scores.

**Fix — Replace the episode loop ending in `inference.py`**:

```python
# After the episode loop, REPLACE lines 148-152 with:

                # Call grader endpoint for final score
                import httpx
                grader_response = httpx.post(
                    f"{env_url}/grader",
                    json={"session_id": result.observation.ticket_id}
                )
                if grader_response.status_code == 200:
                    grade = grader_response.json()
                    print(f"  Final Score: {grade['score']:.4f}")
                    print(f"  Breakdown: {grade['breakdown']}")
                    print(f"  Passed: {grade['passed']}")
                else:
                    # Fallback: compute locally
                    print(f"  Total Reward: {sum(r for r in history_rewards):.4f}")

        except Exception as e:
            print(f"Episode failed: {e}")

    print("\n=== INFERENCE COMPLETE ===")
```

---

### Fix 1.4 — Remove Dead `sentence_transformers` from Dockerfile

**Problem**: ~400MB dead weight. But DON'T just delete it — **use it** (see Fix 2.2 below).

**If you implement Fix 2.2 (semantic grading)**, keep the line.
**If you don't**, remove line 25:
```dockerfile
# DELETE THIS LINE if not using semantic grading:
RUN pip install --no-cache-dir -r requirements.txt && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# REPLACE WITH:
RUN pip install --no-cache-dir -r requirements.txt
```

---

## 🟡 PHASE 2 — Grader & Task Overhaul (+6.5 points)

> This is the **largest gain area**. Task & Grader Quality is 25% of the score.

---

### Fix 2.1 — Add Ambiguous Hard Tickets (Not All Should Need Escalation)

**Problem**: Every single hard ticket requires escalation → trivially detected by keyword matching.

**Fix — In `server/ticket_generator.py`, add 3-4 hard tickets that DON'T require escalation**:

```python
# Add to HARD_TICKETS list:

TicketTemplate(
    category="billing",
    subject="Very Frustrated About Recurring Issue",
    body="""I've contacted support FOUR TIMES about being overcharged $15.99.
    Every time I'm told it will be fixed but it keeps happening. I'm seriously
    considering switching to your competitor. This is RIDICULOUS. Can someone
    who actually has authority to fix things please handle this? I've spent
    hours on this already.""",
    sentiment=-0.7,
    expected_resolution="Root cause identified for recurring billing error. Permanent fix applied. Credit issued for all overcharges.",
    requires_escalation=False,  # ← Angry but NOT needing escalation
    difficulty="hard",
    keywords=["overcharged", "recurring", "frustrated", "competitor", "authority"]
),

TicketTemplate(
    category="technical",
    subject="CRITICAL: Production System Down",
    body="""Our entire team of 50 people cannot work because your API has been
    returning 500 errors for the past 3 HOURS. We're losing thousands of dollars
    per hour. I need this resolved IMMEDIATELY. Your status page says everything
    is fine which is absolutely WRONG. We've tried everything on our end.""",
    sentiment=-0.8,
    expected_resolution="API issue identified and resolved. Incident report provided. SLA credit applied.",
    requires_escalation=False,  # ← Urgent but technical, not needing human escalation
    difficulty="hard",
    keywords=["critical", "production", "API", "500 errors", "immediately", "thousands"]
),

TicketTemplate(
    category="account",
    subject="Outraged About Account Restriction",
    body="""My account was RANDOMLY restricted without any explanation. I've been
    a paying customer for 4 years spending over $10,000 with your company. This is
    how you treat loyal customers?? I demand an explanation and immediate
    reinstatement. I've never violated any terms of service.""",
    sentiment=-0.75,
    expected_resolution="Account restriction reviewed and lifted. Explanation provided for the automated flag. Loyalty appreciation applied.",
    requires_escalation=False,  # ← Angry but can be resolved without escalation
    difficulty="hard",
    keywords=["restricted", "loyal", "demand", "explanation", "reinstatement"]
),
```

**Why this matters**: Now the hard task isn't "detect escalation keywords → escalate." The agent must actually REASON about whether the situation requires human intervention or can be resolved autonomously. This **genuinely challenges frontier models**.

---

### Fix 2.2 — Implement Semantic Response Grading

**Problem**: Response quality scoring is bag-of-words keyword counting. Easily gamed, doesn't measure actual helpfulness.

**Fix — Create `server/semantic_scorer.py`**:

```python
"""
Semantic response quality scoring using sentence-transformers.
Provides meaningful response evaluation beyond keyword matching.
"""

from sentence_transformers import SentenceTransformer, util
from functools import lru_cache
from typing import List

@lru_cache(maxsize=1)
def _get_model():
    """Load model once and cache."""
    return SentenceTransformer('all-MiniLM-L6-v2')

# Pre-defined quality anchors
EMPATHY_ANCHORS = [
    "I completely understand your frustration and I'm sorry for the inconvenience.",
    "I can see how this would be upsetting. Let me help resolve this right away.",
    "Thank you for your patience while we look into this matter.",
]

SOLUTION_ANCHORS = [
    "Here are the steps to resolve your issue.",
    "I've processed your refund and it should appear within 3-5 business days.",
    "I've identified the problem and applied a fix to your account.",
]

HARMFUL_ANCHORS = [
    "That's your fault, not ours.",
    "There's nothing we can do about it.",
    "You should have read the terms of service.",
]


def score_response_semantic(
    response: str,
    expected_resolution: str,
    customer_sentiment: float
) -> dict:
    """
    Score a response using semantic similarity.
    
    Returns:
        dict with empathy_score, solution_score, appropriateness_score, resolution_alignment
    """
    model = _get_model()
    
    resp_embedding = model.encode(response, convert_to_tensor=True)
    
    # 1. Empathy score — how close to empathetic language
    empathy_embeddings = model.encode(EMPATHY_ANCHORS, convert_to_tensor=True)
    empathy_sims = util.cos_sim(resp_embedding, empathy_embeddings)[0]
    empathy_score = float(empathy_sims.max())
    
    # 2. Solution score — how close to solution language
    solution_embeddings = model.encode(SOLUTION_ANCHORS, convert_to_tensor=True)
    solution_sims = util.cos_sim(resp_embedding, solution_embeddings)[0]
    solution_score = float(solution_sims.max())
    
    # 3. Harmfulness check — penalize responses similar to harmful examples
    harmful_embeddings = model.encode(HARMFUL_ANCHORS, convert_to_tensor=True)
    harmful_sims = util.cos_sim(resp_embedding, harmful_embeddings)[0]
    harmful_score = float(harmful_sims.max())
    
    # 4. Resolution alignment — how relevant to the expected resolution
    if expected_resolution:
        resolution_embedding = model.encode(expected_resolution, convert_to_tensor=True)
        resolution_alignment = float(util.cos_sim(resp_embedding, resolution_embedding)[0][0])
    else:
        resolution_alignment = 0.5
    
    # Weight empathy higher for angry customers
    if customer_sentiment < -0.5:
        empathy_weight = 0.4
        solution_weight = 0.3
    else:
        empathy_weight = 0.25
        solution_weight = 0.4
    
    # Composite score
    composite = (
        empathy_score * empathy_weight +
        solution_score * solution_weight +
        resolution_alignment * 0.2 +
        (1.0 - harmful_score) * 0.15  # Penalize harmful similarity
    )
    
    return {
        "empathy_score": round(empathy_score, 4),
        "solution_score": round(solution_score, 4),
        "harmful_score": round(harmful_score, 4),
        "resolution_alignment": round(resolution_alignment, 4),
        "composite": round(min(1.0, max(0.0, composite)), 4),
    }
```

**Then update `graders.py` `_grade_responses()`** to use semantic scoring as a component:

```python
from server.semantic_scorer import score_response_semantic

def _grade_responses(self, action_history, difficulty, expected_resolution="", customer_sentiment=0.0):
    responses = [a for a in action_history if a.get("type") == "respond"]
    if not responses:
        return 0.0

    total_score = 0.0
    for response in responses:
        content = response.get("content", "")

        # Keyword score (existing logic, keep as fallback)
        keyword_score = self._keyword_response_score(content)

        # Semantic score (NEW)
        try:
            semantic = score_response_semantic(content, expected_resolution, customer_sentiment)
            semantic_score = semantic["composite"]
        except Exception:
            semantic_score = keyword_score  # Fallback if model fails

        # Blend: 60% semantic, 40% keyword
        blended = semantic_score * 0.6 + keyword_score * 0.4
        total_score += max(0.0, min(1.0, blended))

    avg_score = total_score / len(responses)

    # Difficulty scaling
    if difficulty == "hard":
        avg_score *= 0.65
    elif difficulty == "medium":
        avg_score *= 0.80

    return min(1.0, avg_score)
```

**Why this matters**: Now keyword stuffing gives ~40% of the score at best. The agent must write genuinely empathetic, solution-oriented, contextually relevant responses. This is the difference between a toy grader and one that Meta engineers will respect.

---

### Fix 2.3 — Add Grader Anti-Gaming: Resolution Content Must Match Context

**Problem**: Resolution grading uses stopword-filtered set intersection with expected resolution. Agent can stuff random matching words.

**Fix — In `graders.py`, enhance `_grade_resolution()`**:

```python
def _grade_resolution(self, is_resolved, action_history, expected_resolution, task_difficulty="easy"):
    if not is_resolved:
        escalations = [a for a in action_history if a.get("type") == "escalate"]
        if escalations:
            return 0.3
        return 0.1

    resolutions = [a for a in action_history if a.get("type") == "resolve"]
    if not resolutions:
        return 0.15

    resolution_content = resolutions[-1].get("content", "").lower()

    # Minimum length check — resolution must be substantive
    word_count = len(resolution_content.split())
    if word_count < 8:
        return 0.2  # Too short to be meaningful

    # Semantic similarity check (if available)
    try:
        from server.semantic_scorer import score_response_semantic
        sem = score_response_semantic(resolution_content, expected_resolution, 0.0)
        semantic_score = sem["resolution_alignment"]
    except Exception:
        semantic_score = None

    # Keyword overlap (existing logic)
    stopwords = {"the", "a", "an", "is", "are", "was", "were", ...(keep existing)}
    expected_terms = {w for w in expected_resolution.lower().split() if w not in stopwords and len(w) > 2}
    resolution_terms = {w for w in resolution_content.split() if w not in stopwords and len(w) > 2}

    if expected_terms:
        overlap_ratio = len(expected_terms & resolution_terms) / len(expected_terms)
    else:
        overlap_ratio = 0.5

    action_words = {"processed", "resolved", "fixed", "updated", "refunded", "cancelled", "escalated", "investigated", "completed", "sent"}
    has_action_word = any(w in resolution_content for w in action_words)

    # Blend scores
    if semantic_score is not None:
        base_score = semantic_score * 0.5 + overlap_ratio * 0.3 + (0.2 if has_action_word else 0.0)
    else:
        base_score = overlap_ratio * 0.7 + (0.3 if has_action_word else 0.0)

    return min(1.0, base_score)
```

---

### Fix 2.4 — Pass `expected_resolution` and `customer_sentiment` to Response Grading

**Problem**: The grader's `_grade_responses()` never receives `expected_resolution` or `customer_sentiment`, so it can't do context-aware scoring.

**Fix — In `grade_episode()`**, update the call:

```python
response_score = self._grade_responses(
    action_history, task_difficulty,
    expected_resolution=expected_resolution,     # ADD
    customer_sentiment=customer_sentiment         # ADD (need to pass through)
)
```

Also add `customer_sentiment` as a parameter to `grade_episode()` and propagate from `environment.py`.

---

## 🟢 PHASE 3 — Environment Design Polish (+4.6 points)

---

### Fix 3.1 — Use the `confidence` Field or Remove It

**Option A (Recommended): Use it in reward computation.**

In `server/reward.py`, modify `compute_reward()`:

```python
def compute_reward(self, ..., confidence: float = None, ...):
    # ... existing logic ...
    
    # Confidence calibration bonus/penalty
    if confidence is not None and action_type == "classify":
        if breakdown.classification_reward > 0:  # Correct
            if confidence > 0.8:
                breakdown.total += 0.05  # Rewarded for high confidence when right
            elif confidence < 0.3:
                breakdown.total += 0.02  # Modest reward for honest low confidence
        else:  # Wrong
            if confidence > 0.8:
                breakdown.penalty -= 0.10  # Extra penalty for overconfident AND wrong
            elif confidence < 0.3:
                breakdown.penalty += 0.05  # Less penalty for honest uncertainty
```

**Why**: This teaches agents calibration — a real-world RL objective. Judges will love this.

---

### Fix 3.2 — Add Knowledge Base Lookup Action

**The single highest-impact creativity feature you can add.**

In `models.py`:
```python
class SupportAction(Action):
    action_type: Literal["classify", "respond", "escalate", "request_info", "resolve", "lookup_kb"]
    content: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
```

In `server/environment.py`, add a knowledge base and handler:

```python
KNOWLEDGE_BASE = {
    "password_reset": "Go to Settings > Security > Reset Password. Link expires in 24h.",
    "refund_policy": "Full refund within 30 days. Partial refund 31-60 days. No refund after 60 days.",
    "billing_dispute": "Submit dispute form at billing.example.com/dispute. Include order # and screenshots.",
    "two_factor": "Backup codes available at Settings > Security > 2FA > Backup Codes. 10 codes generated.",
    "data_export": "GDPR export: Settings > Privacy > Export Data. Ready in 24-48 hours.",
    "account_deletion": "Submit deletion request at privacy.example.com/delete. 30-day grace period.",
    "subscription_tiers": "Basic: $9.99/mo, Pro: $29.99/mo, Enterprise: $99.99/mo. Annual = 20% discount.",
    "shipping_policy": "Standard: 5-7 days. Express: 2-3 days. Next-day: $14.99 extra.",
}

def _handle_lookup_kb(self, query: str) -> str:
    """Handle knowledge base lookup."""
    query_lower = query.lower()
    best_match = None
    best_score = 0

    for key, value in KNOWLEDGE_BASE.items():
        # Simple keyword overlap scoring
        key_words = set(key.replace("_", " ").split())
        query_words = set(query_lower.split())
        overlap = len(key_words & query_words)
        if overlap > best_score:
            best_score = overlap
            best_match = (key, value)

    if best_match and best_score > 0:
        self._interaction_history.append({
            "role": "system",
            "content": f"KB Result [{best_match[0]}]: {best_match[1]}"
        })
        return f"Knowledge base result found: {best_match[1]}"
    else:
        self._interaction_history.append({
            "role": "system",
            "content": "KB: No relevant articles found."
        })
        return "No relevant knowledge base articles found for this query."
```

In `reward.py`, add reward for appropriate KB usage:
```python
elif action_type == "lookup_kb":
    if step_count <= 2 and task_difficulty in ["medium", "hard"]:
        breakdown.response_reward = 0.12  # Smart information gathering
        breakdown.reason += "Knowledge base lookup before responding. "
    else:
        breakdown.penalty += -0.05
        breakdown.reason += "Late KB lookup. "
```

**Why this matters**: Judges explicitly ask "clever mechanics that make the environment engaging." A KB lookup action simulates real support tools and adds a strategic dimension — the agent must decide WHEN to look up information vs when to respond from context.

---

### Fix 3.3 — Add Cumulative Reward to Observation

In `models.py`, add to `SupportObservation`:

```python
    cumulative_reward: float = 0.0  # Running total reward in this episode
```

In `environment.py` `step()`, populate it:

```python
return SupportObservation(
    ...
    cumulative_reward=self._state.total_reward,
    ...
)
```

---

### Fix 3.4 — Dynamic Customer Replies That Depend on Agent Content

**Problem**: Customer replies are formulaic — they don't react to what the agent specifically says.

**Fix — Enhance `_generate_customer_reply()`** in `environment.py`:

```python
def _generate_customer_reply(self, response: str) -> str:
    """Dynamic customer reply based on ticket sentiment, personality, and agent response content."""
    sentiment = self._current_ticket["sentiment"]
    personality = self._current_ticket.get("personality", "neutral")
    category = self._current_ticket.get("category", "general")

    response_lower = response.lower()
    has_empathy = any(kw in response_lower for kw in ["understand", "sorry", "apologize", "help", "thank", "frustrating"])
    has_solution = any(kw in response_lower for kw in ["here's", "you can", "resolved", "fixed", "processed", "please try", "steps"])
    has_question = "?" in response
    mentions_refund = any(w in response_lower for w in ["refund", "credit", "reimburse", "compensation"])
    mentions_timeline = any(w in response_lower for w in ["days", "hours", "shortly", "soon", "immediately"])

    # Adjust sentiment
    if has_empathy and has_solution:
        sentiment += 0.3
    elif has_empathy:
        sentiment += 0.15
    elif has_solution:
        sentiment += 0.1
    elif not has_solution and not has_empathy:
        sentiment -= 0.25

    self._current_ticket["sentiment"] = max(-1.0, min(1.0, sentiment))

    # Context-aware replies
    if sentiment < -0.5:
        if personality == "aggressive":
            if mentions_refund:
                return "I don't just want a refund, I want an explanation! How did this happen in the first place?"
            return "This is unacceptable. I need a real solution IMMEDIATELY or I'm escalating this."
        elif personality == "anxious":
            if mentions_timeline:
                return "You say it'll be fixed soon but how long exactly? I can't afford to wait!"
            return "I'm panicking! I really need this fixed, what's taking so long?"
        if has_question:
            return "I already told you everything. Stop asking questions and just fix it!"
        return "I am still very unhappy with this. Please fix it now."
    elif sentiment < 0:
        if has_question:
            return "Fine, I'll answer your question. But please hurry up with the resolution."
        if mentions_timeline:
            return "Alright, I can wait a few days. But please make sure it actually gets done this time."
        return "Okay, I'm waiting for the resolution. Please hurry."
    elif sentiment < 0.5:
        if has_solution:
            return "That sounds like it might work. I'll try what you suggested and let you know."
        return "Okay, I understand. Let's see if this works."
    else:
        if personality == "friendly":
            if mentions_refund:
                return "Oh wonderful, thank you so much! That refund will be a huge relief!"
            return "Oh perfect! Thank you so much for your wonderful help!"
        return "Thank you for your help. That resolves my issue."
```

---

## 🔵 PHASE 4 — Code Quality & Compliance (+3.5 points)

---

### Fix 4.1 — Proper Python Packaging (Kill `sys.path` hack)

**Create `__init__.py` at project root:**

```python
# d:\SupportEnv\__init__.py
"""SupportEnv — Customer Support RL Environment for OpenEnv."""
```

**Update `pyproject.toml`:**

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["server*", "baseline*", "frontend*", "models*", "client*", "config*"]
```

**Remove `sys.path.insert` from `server/app.py` (line 31) and `baseline/run_baseline.py` (line 21).**

Use relative imports or install the package in editable mode: `pip install -e .`

---

### Fix 4.2 — Fix Unfilled Template Placeholders

**In `ticket_generator.py`, add missing replacements to `_fill_template()`:**

```python
def _fill_template(self, template: str) -> str:
    replacements = {
        # ... existing replacements ...
        "{product}": self._rng.choice(["Wireless Headphones", "Smart Watch", "Laptop Stand", "USB-C Hub"]),
        "{personal_info}": self._rng.choice(["SSN, email, and home address", "credit card numbers and email", "full name, DOB, and phone number"]),
        "{patient_id}": f"PAT-{self._rng.randint(100000, 999999)}",
        "{device}": self._rng.choice(["iPhone 14", "Samsung S23", "Pixel 7", "iPad Pro"]),
        "{personal_detail}": self._rng.choice(["I have a family to support.", "I've been loyal for years.", "Nobody will listen to me."]),
        "{phone}": f"+1-{self._rng.randint(200,999)}-{self._rng.randint(100,999)}-{self._rng.randint(1000,9999)}",
        "{error_code}": f"ERR-{self._rng.randint(1000, 9999)}",
    }
    # ... rest of method
```

---

### Fix 4.3 — Add Missing Tests

**Create `tests/test_reward.py`:**

```python
import pytest
from server.reward import RewardEngine

class TestRewardEngine:
    def test_correct_classification_reward(self):
        engine = RewardEngine()
        result = engine.compute_reward("classify", "billing", "billing", False, 0.0, 1, 10, False, "easy")
        assert result.classification_reward == 0.25

    def test_wrong_classification_penalty(self):
        engine = RewardEngine()
        result = engine.compute_reward("classify", "technical", "billing", False, 0.0, 1, 10, False, "easy")
        assert result.classification_reward < 0

    def test_repeated_action_penalty(self):
        engine = RewardEngine()
        engine.compute_reward("classify", "billing", "billing", False, 0.0, 1, 10, False, "easy")
        result = engine.compute_reward("classify", "billing", "billing", False, 0.0, 2, 10, False, "easy")
        assert result.penalty < 0

    def test_harmful_response(self):
        engine = RewardEngine()
        result = engine.compute_reward("respond", "It's your fault, stupid", "billing", False, 0.0, 1, 10, False, "easy")
        assert result.response_reward < 0

    def test_empathetic_response_to_angry_customer(self):
        engine = RewardEngine()
        result = engine.compute_reward("respond", "I understand your frustration. I'm sorry for the inconvenience. Here's how we can fix this.", "billing", False, -0.8, 1, 10, False, "hard")
        assert result.tone_reward > 0

    def test_reset_clears_history(self):
        engine = RewardEngine()
        engine.compute_reward("classify", "billing", "billing", False, 0.0, 1, 10, False, "easy")
        engine.reset()
        assert len(engine.action_history) == 0

    def test_episode_final_reward(self):
        engine = RewardEngine()
        reward = engine.compute_episode_final_reward(True, True, True, 3, 10)
        assert reward > 0

    def test_episode_final_reward_failure(self):
        engine = RewardEngine()
        reward = engine.compute_episode_final_reward(False, False, False, 10, 10)
        assert reward < 0
```

**Create `tests/test_concurrent.py`:**

```python
import pytest
import asyncio
from server.environment import SupportEnvironment
from models import SupportAction

def test_concurrent_sessions():
    """Multiple environment instances should not interfere."""
    env1 = SupportEnvironment()
    env2 = SupportEnvironment()

    obs1 = env1.reset(seed=42, difficulty="easy")
    obs2 = env2.reset(seed=99, difficulty="hard")

    # They should have different tickets
    assert obs1.ticket_text != obs2.ticket_text
    assert obs1.task_difficulty != obs2.task_difficulty

    # Step one should not affect the other
    env1.step(SupportAction(action_type="classify", content="billing"))
    assert env2.state.step_count == 0  # env2 untouched
    assert env1.state.step_count == 1
```

**Create `tests/test_determinism.py`:**

```python
import pytest
from server.graders import SupportGrader

def test_grader_100_runs_deterministic():
    """Grader must produce identical scores on repeated runs."""
    grader = SupportGrader()
    kwargs = {
        "action_history": [
            {"type": "classify", "content": "billing", "step": 1},
            {"type": "respond", "content": "I understand and I'm sorry. Here's how we can fix your billing issue. I've processed the refund.", "step": 2},
            {"type": "resolve", "content": "Refund processed and billing error corrected.", "step": 3},
        ],
        "target_category": "billing",
        "requires_escalation": False,
        "expected_resolution": "Refund processed and billing corrected.",
        "task_difficulty": "easy",
        "is_resolved": True,
        "total_steps": 3,
        "max_steps": 5,
    }

    scores = [grader.grade_episode(**kwargs).score for _ in range(100)]
    assert len(set(scores)) == 1, f"Grader is non-deterministic: {set(scores)}"
```

---

### Fix 4.4 — Fix `test_baseline_endpoint` (Currently Broken)

**In `tests/test_api.py`**, the baseline endpoint is `GET` not `POST`:

```python
def test_baseline_endpoint():
    """Test the baseline endpoint returns valid results."""
    response = client.get("/baseline")  # GET, not POST
    assert response.status_code == 200
    data = response.json()
    assert "baseline_results" in data
    assert "summary" in data
    assert data["summary"]["average_score"] > 0
```

---

## 🟣 PHASE 5 — Creativity & Novelty (+3.0 points)

---

### Fix 5.1 — SLA Timer Mechanic

Add a simulated SLA timer that creates urgency:

In `models.py`, add to `SupportObservation`:
```python
    sla_remaining_pct: float = 1.0  # 1.0 = full SLA, 0.0 = SLA breached
    priority_level: Literal["low", "normal", "high", "critical"] = "normal"
```

In `environment.py`, compute SLA:
```python
# In step(), compute SLA based on remaining steps
sla_pct = max(0.0, (self._state.max_steps - self._state.step_count) / self._state.max_steps)

# Priority based on sentiment + ticket category
if self._current_ticket["sentiment"] < -0.7:
    priority = "critical"
elif self._current_ticket["sentiment"] < -0.3:
    priority = "high"
elif self._state.task_difficulty == "hard":
    priority = "high"
else:
    priority = "normal"
```

In `reward.py`, add SLA breach penalty:
```python
# Bonus for resolving before SLA breach (< 50% steps used)
if step_count < max_steps * 0.5 and is_resolved:
    breakdown.efficiency_reward += 0.15
    breakdown.reason += "Resolved within SLA. "
```

---

### Fix 5.2 — Multi-Issue Tickets (2 Problems in 1 Ticket)

Add 2-3 medium templates with dual issues:

```python
TicketTemplate(
    category="billing",  # Primary category
    subject="Double Charge AND Missing Order",
    body="""Two problems: First, I was charged twice for order #{order_id}.
    Second, the order never arrived! It's been 2 weeks past the delivery date.
    I need both a refund for the duplicate charge AND either the product
    delivered or a full refund. This is very frustrating.""",
    sentiment=-0.5,
    expected_resolution="Duplicate charge refunded. Missing order investigated and reshipped or refunded.",
    requires_escalation=False,
    difficulty="medium",
    keywords=["charged", "twice", "missing", "delivery", "refund", "both"]
),
```

In `graders.py`, for multi-issue tickets, check that the resolution addresses BOTH issues:

```python
# In _grade_resolution, check for multi-issue coverage
if "both" in expected_lower or "and" in expected_lower:
    # Split expected into parts and check coverage of each
    parts = expected_lower.split(" and ")
    covered = sum(1 for part in parts if any(
        w in resolution_content for w in part.split() if w not in stopwords and len(w) > 2
    ))
    multi_issue_bonus = covered / len(parts) * 0.2
    base_score += multi_issue_bonus
```

---

### Fix 5.3 — Customer Personality System (Expand from 4 → 8 Types)

```python
PERSONALITY_TYPES = [
    "neutral",
    "aggressive",
    "friendly",
    "anxious",
    "sarcastic",      # NEW: Responds with sarcasm, hard to gauge satisfaction
    "technical",      # NEW: Gives overly technical details, expects technical responses
    "elderly",        # NEW: Needs simple language, patient explanations
    "corporate",      # NEW: Formal tone, expects professionalism
]
```

Each personality type produces different customer replies, making the environment richer and less predictable.

---

## 📋 Implementation Priority Checklist

Execute in this exact order for maximum point gain per hour of work:

### Day 1 — Critical Fixes (12 points)
- [ ] **1.1** Fix difficulty inversion (graders.py escalation + efficiency changes)
- [ ] **1.2** Hide target info from state endpoint
- [ ] **1.3** Fix inference.py to print grader scores
- [ ] **1.4** Either USE or REMOVE sentence_transformers from Dockerfile
- [ ] Re-run baseline → verify Easy > Medium > Hard score order
- [ ] Commit + test

### Day 2 — Grader Overhaul (6.5 points)
- [ ] **2.1** Add 3+ ambiguous hard tickets (angry but NOT needing escalation)
- [ ] **2.2** Implement semantic response scoring
- [ ] **2.3** Enhance resolution grading with semantic scoring
- [ ] **2.4** Pass context (expected_resolution, sentiment) to response grader
- [ ] Re-run baseline → verify scores make sense
- [ ] Run all tests → fix any regressions

### Day 3 — Environment Design (4.6 points)
- [ ] **3.1** Use confidence field in reward computation
- [ ] **3.2** Add knowledge base lookup action
- [ ] **3.3** Add cumulative_reward to observation
- [ ] **3.4** Enhance customer replies to be context-aware
- [ ] Update README with new action type + KB docs
- [ ] Run all tests

### Day 4 — Code Quality (3.5 points)
- [ ] **4.1** Fix Python packaging (remove sys.path hack)
- [ ] **4.2** Fix unfilled template placeholders
- [ ] **4.3** Add reward, concurrent, determinism tests
- [ ] **4.4** Fix broken test_baseline_endpoint
- [ ] Run `pytest tests/ -v` → all green
- [ ] Run `openenv validate` → all pass

### Day 5 — Creativity Features (3.0 points)
- [ ] **5.1** Add SLA timer mechanic
- [ ] **5.2** Add multi-issue ticket templates
- [ ] **5.3** Expand personality system
- [ ] Update openenv.yaml with new features
- [ ] Update README with all new mechanics
- [ ] Final baseline run + Docker build test

---

## 🎯 Target Score After All Fixes

| Parameter | Weight | Current | After Fixes | Gain |
|---|---|---|---|---|
| Real-world utility | 30% | 23.4 | 28.5 | +5.1 |
| Task & grader quality | 25% | 17.0 | 23.5 | +6.5 |
| Environment design | 20% | 14.4 | 19.0 | +4.6 |
| Code quality & spec | 15% | 10.5 | 14.0 | +3.5 |
| Creativity & novelty | 10% | 6.5 | 9.5 | +3.0 |
| **TOTAL** | **100%** | **71.8** | **94.5** | **+22.7** |

The **single most impactful change** is Fix 2.1 (ambiguous hard tickets) + Fix 1.1 (difficulty inversion fix). Together they fix the core calibration problem AND make the environment genuinely challenging for frontier models. That alone moves you from "mid-tier" to "contender."

The **second most impactful** is Fix 2.2 (semantic grading). This transforms the grader from a keyword counter that any student could game into a system that Meta engineers would actually respect.

Everything else is polish that accumulates into the 90+ range.

**Do Phase 1 and Phase 2 first. They account for +18.5 points out of the +22.7 total.**
