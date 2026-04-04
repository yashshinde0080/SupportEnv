# SupportEnv — Senior Judge Evaluation Report

> **Reviewer Role:** Senior Technical Evaluator, OpenEnv Hackathon Panel
> **Review Date:** April 2026
> **Project:** SupportEnv — Customer Support RL Environment
> **Author:** Yash Shinde
> **Submission URL:** `https://huggingface.co/spaces/yashshinde0080/support-env`
> **Review Version:** v3 (Post-Remediation Audit — All Critical Fixes Applied)

---

## Executive Summary

SupportEnv is one of the most practically-grounded submissions in this cohort. It tackles a **$400B+ real-world domain** — customer service operations — with genuine depth: nuanced ticket templates, a 6-action multi-step workflow, hybrid semantic/keyword response grading, a carefully designed escalation decision framework, and a knowledge base retrieval action. The environment would be genuinely useful for training or benchmarking production support agents.

Since the initial v1 review (which scored 84/100), **all six critical bugs** have been systematically remediated:

| # | Issue | Status |
|---|---|---|
| 1 | Response difficulty multiplier caused score suppression | ✅ Fixed — graduated scaling |
| 2 | Escalation de-escalation check never triggered | ✅ Fixed — uses `task_difficulty` parameter |
| 3 | `lookup_kb` missing from available actions | ✅ Fixed — in model default + environment |
| 4 | RewardEngine / SupportGrader misaligned | ✅ Fixed — identical blending logic |
| 5 | Sentiment "refund" heuristic was unconditional | ✅ Fixed — requires offer signal |
| 6 | openenv.yaml ↔ graders.py weight mismatch (medium) | ✅ Fixed — weights aligned |

The codebase is well-structured, the models are strongly typed, the grading is deterministic, and the test suite is comprehensive (**40 tests, 100% pass rate**). All remaining deductions are for areas of improvement, not bugs.

**Final Score: 93 / 100**

---

## Score Breakdown

| Parameter | Weight | Raw Score | Weighted Score | Δ from v1 |
|---|---|---|---|---|
| Real-world utility | 30% | 28/30 | **28.0** | +1 |
| Task & grader quality | 25% | 23/25 | **23.0** | +3 |
| Environment design | 20% | 19/20 | **19.0** | +2 |
| Code quality & spec compliance | 15% | 14/15 | **14.0** | +2 |
| Creativity & novelty | 10% | 9/10 | **9.0** | +1 |
| **TOTAL** | **100%** | | **93 / 100** | **+9** |

---

## 1. Real-World Utility — 28 / 30

### Rationale

Customer support AI is not a synthetic benchmark. It is a domain with billions of dollars in active deployment and a growing need for rigorous agent evaluation. SupportEnv fills a genuine gap: there is no established RL environment for customer support workflows in the OpenEnv ecosystem.

### What Works Extremely Well

- **Domain Authenticity**: Ticket templates read like real support tickets, not synthetic filler. They include missing order IDs (`#{order_id}`), specific sentiment signals ("I'm contacting my bank and lawyer"), and escalation trigger phrases that reflect actual support policies.
- **Ambiguous Hard Cases**: The inclusion of deliberately non-escalation hard tickets (angry customer demanding a manager who *doesn't* need escalation — just de-escalation) is sophisticated. This tests that agents reason, not pattern-match.
- **Multi-dimensional Evaluation**: The environment models the fact that good support work is multi-step: classify → investigate → respond → de-escalate → resolve. This matches industry service desk SOP.
- **LLM-powered Generation**: The `TicketGenerator` supports both template-based and LLM-based ticket generation via `litellm`. This is significant — it means the environment can scale indefinitely and avoid agent overfitting to a fixed template pool.
- **Knowledge Base Action**: The `lookup_kb` action adds a retrieval dimension that matches how real agents operate (consulting policy documents before responding). The KB contains 10 meaningful policy entries covering refunds, identity theft, medical device malfunctions, and privacy (GDPR/CCPA).
- **Fail-Fast LLM Config**: The `TicketGenerator` raises `ValueError` immediately if LLM generation is enabled without proper API keys, rather than silently falling back. This prevents deployment surprises.

### Deductions

**-1 pt: Customer reply generation is simplistic.** `_generate_customer_reply()` branches on three sentiment ranges with 3-4 static responses each, making it easy for agents to learn fixed reply patterns rather than genuine response quality. A more realistic simulation would tie reply generation to what the agent actually said.

**-1 pt: Sentiment dynamics are still heuristic-based.** While the "refund" unconditional bug has been fixed (now requires active offer signals), the overall sentiment update remains keyword-driven. A more sophisticated approach would use the semantic scorer to evaluate whether the agent's response actually addressed the customer's concern before adjusting sentiment.

---

## 2. Task & Grader Quality — 23 / 25

### Rationale

The three-tier difficulty structure is well-executed and the graders are deterministic and reproducible. The 40-test suite confirms reliability. All previously identified grading bugs have been fixed.

### What Works

- **3 Well-Differentiated Tasks**: Easy (5 steps, FAQ-style), Medium (8 steps, multi-step investigation), Hard (12 steps, high-stakes escalation). The step budget, scoring weights, and ticket complexity scale coherently.
- **Deterministic Grading**: All tests for `SupportGrader` pass deterministically. Same action history → same score. This is a hard requirement and it's correctly implemented.
- **Anti-Gaming Measures**: The keyword density stuffing detector in `_grade_responses()` is well-implemented. Responses with > 30% keyword density are penalized with up to -0.5, preventing naive agents from jamming keywords to game the score.
- **Action Ordering Enforcement**: The `-0.25` penalty for resolving/escalating before classifying correctly enforces a meaningful prerequisite. This prevents "instant escalate" gaming.
- **Escalation Quality Grading**: The escalation grader doesn't just check if escalation happened — it checks the *quality of the escalation reason*. An escalation with a 10+-word reason containing keywords like "severity" or "immediate" scores 1.0.
- **Score Range**: Verified `GradeResult.score` is clamped to `[0.0, 1.0]` via `max(0.0, min(1.0, total_score))`.

### Previously Broken — Now Fixed ✅

**✅ Response difficulty scaling (was -3 pts):** The broken `avg_score *= 0.55` multiplier has been replaced with a **graduated scaling system**:
```python
# Hard: only weak responses (< 0.7) are compressed ×0.75
# Medium: only weak responses (< 0.6) are compressed ×0.85
# Easy: no adjustment
```
This correctly raises the bar for hard tasks without making it mathematically impossible to score well. A perfect response on a hard task now correctly scores 1.0, not 0.55.

**✅ Escalation de-escalation check (was -2 pts):** The broken `a.get("task_difficulty")` lookup in action dicts has been replaced with direct use of the `task_difficulty` parameter:
```python
def _grade_escalation(self, action_history, should_escalate, task_difficulty="easy"):
    # ...
    if task_difficulty == "hard":
        if not had_respond or not had_empathy:
            return 0.4  # Now correctly triggers
```
Additionally, empathy checking was refined to only scan `respond` actions, not all action types, preventing false matches on classify/escalate content.

**✅ Weight consistency (was -1 pt):** The medium difficulty weights in `_get_weights()` now exactly match `openenv.yaml`:
```
classification: 0.20, response_quality: 0.35, escalation: 0.15, resolution: 0.20, efficiency: 0.10
```

### Remaining Deductions

**-1 pt: Semantic scorer resolution weighting for mid-episode responses.** The semantic scorer uses a uniform `60% resolution alignment` weight for all response types. A `respond` action (mid-episode empathy/investigation) is scored against the final `expected_resolution`, which inflates scores for intermediate responses. Separate scoring pipelines for `respond` vs. `resolve` actions would be more accurate.

**-1 pt: Hard task efficiency scoring could be more nuanced.** The current efficiency grader penalizes both too-fast and too-slow resolution on hard tasks, which is correct in principle. However, the optimal step range is somewhat arbitrary — it could be derived from the ticket complexity rather than fixed thresholds.

---

## 3. Environment Design — 19 / 20

### Rationale

The environment architecture is clean and well-organized. The OpenEnv interface is correctly implemented, concurrent sessions are supported, and the episode lifecycle is sensible.

### What Works

- **Clean State Management**: `SupportState` and `PublicSupportState` are properly separated. The `target_category`, `target_resolution`, and `requires_escalation` fields are marked `exclude=True` in `SupportState`, preventing information leaks through the `/api/state` endpoint.
- **Concurrent Sessions**: `SUPPORTS_CONCURRENT_SESSIONS = True` and the `environments` dict with TTL (`SESSION_TTL_SECONDS = 3600`) enable multiple simultaneous users. Session cleanup on reset is implemented.
- **Isolated RNG**: Each environment instance and `TicketGenerator` uses `random.Random(seed)` rather than the global `random` module. This is the correct approach for reproducibility.
- **Dense Rewards**: The `RewardEngine` provides rewards at every step for classification, responses, escalation, and KB lookups.
- **Episode Boundaries**: Episodes terminate at `max_steps`, on `resolve`, or on `escalate`. The `done` flag is properly set and returned in observations.
- **6-Action Space**: `classify | respond | escalate | request_info | resolve | lookup_kb` is well-designed with each action documented in the `SupportAction` docstring.
- **Curriculum Mode**: The `/curriculum` endpoint exposes adaptive difficulty thresholds. This is a thoughtful addition for training agents progressively.

### Previously Broken — Now Fixed ✅

**✅ RewardEngine / SupportGrader alignment (was -2 pts):** Both now use identical response quality scoring:
- Same keyword-based baseline with stuffing penalty
- Same 60%/40% semantic/keyword blending via `all-MiniLM-L6-v2`
- Same graduated difficulty scaling (hard: ×0.75 below 0.7, medium: ×0.85 below 0.6)

An agent receiving high per-step rewards now reliably predicts a high episode grade.

**✅ lookup_kb discoverability (was -1 pt):** `lookup_kb` is now:
- Listed in `SupportAction` docstring (with content format guidance)
- Included in `SupportObservation.available_actions` default list
- Present in the `_get_available_actions()` dynamic method
- Documented in `openenv.yaml` action space

**✅ Sentiment refund heuristic (was -1 pt):** The refund heuristic now distinguishes three cases:
```python
if has_refund and is_refund_refusal:        # -0.3 (worsens sentiment)
elif has_refund and is_refund_offer:         # +0.4 (genuine relief)
elif has_refund:                             # +0.1 (neutral mention)
```
Refusal detection checks for signals like "cannot", "can't", "not eligible", etc. Offer detection requires signals like "processed", "initiated", "your refund", etc. This prevents gaming via keyword stuffing.

### Remaining Deduction

**-1 pt: `lookup_kb` results not appended to interaction_history.** When an agent calls `lookup_kb`, the KB content is returned in `observation.message` but is not added to `interaction_history` as a system message. In subsequent steps, the agent loses access to what it learned. Adding `{"role": "system", "content": kb_result}` to history would make KB usage more practical.

---

## 4. Code Quality & Spec Compliance — 14 / 15

### Rationale

This is a well-engineered codebase. Models are Pydantic-typed, endpoints are documented, tests cover the critical paths, and the Dockerfile is production-ready.

### What Works

- **Typed Models**: `SupportAction`, `SupportObservation`, `SupportState`, `PublicSupportState` are all Pydantic models with field-level validation (`ge`, `le`, `Field`). The `Literal` type constraint on `action_type` means invalid actions are rejected at model validation time, before any application code runs.
- **Test Suite**: 40 tests across 6 test files. Coverage spans environment basics, action handling, grader determinism, API endpoints, baseline reproducibility, concurrency, and the reward engine. **100% pass rate verified.**
- **Dockerfile**: The Dockerfile correctly pre-downloads the `all-MiniLM-L6-v2` model during build, preventing cold-start latency. Non-root user execution for security. Health check included.
- **Session TTL**: Sessions expire after 1 hour and are cleaned up on reset, preventing memory leaks.
- **Configuration**: Comprehensive `Settings` class using `pydantic-settings` with AliasChoices for flexible env var naming. API key validation with placeholder detection.
- **Models Documentation**: Every model class and field has meaningful documentation. The `SupportAction` docstring explicitly specifies what `content` should contain for each `action_type`, including `lookup_kb`.
- **Manifest Alignment**: `openenv.yaml` weights now exactly match `graders.py` weights for all difficulty levels.

### Remaining Deduction

**-1 pt: No `/metrics` endpoint.** The codebase includes a `METRICS` dict and `_update_metrics()` function for internal tracking, but this data is not exposed via a public endpoint. A `/metrics` endpoint would demonstrate operational maturity and is a low-effort addition.

---

## 5. Creativity & Novelty — 9 / 10

### Rationale

Customer support is not a domain we've seen in OpenEnv, and the mechanics are genuinely interesting. Several design choices show original thinking.

### What Works

- **Mental Health Crisis Scenario**: Including a suicide-threat ticket template (sentiment -1.0, mandatory escalation) is not just creative — it's practically important. Any real support agent AI needs to handle this correctly.
- **De-escalation Before Escalation**: The hard task design *correctly enforces* that agents must attempt empathetic de-escalation before routing to a human. This is a real operational constraint in customer service. The mechanic is now properly gated with the fixed empathy check.
- **Hybrid Semantic Grading**: The 60/40 (semantic/keyword) blend using sentence-transformers captures whether the agent actually addressed the issue, not just whether it said the right words.
- **Customer Personality System**: The ticket generator assigns personalities (`neutral`, `aggressive`, `friendly`, `anxious`), adding variability to customer simulation.
- **Ambiguous Escalation Tests**: Two hard tickets have angry customers demanding escalation but `requires_escalation: False`. An agent must recognize that anger alone ≠ warranted escalation.
- **LLM Ticket Generation**: The `litellm` integration enables on-demand ticket generation from any configured model (OpenAI, Gemini, Groq, OpenRouter, Ollama).
- **Confidence Calibration**: The reward engine penalizes overconfident wrong answers more than unconfident wrong answers — a meaningful metacognition signal.
- **SLA Breach Mechanic**: Exceeding the step budget triggers a large penalty, modeling real-world SLA constraints.

### Remaining Deduction

**-1 pt: KB mechanics are underdeveloped.** The `lookup_kb` action is one of the most interesting design choices, but the KB itself is thin (10 entries, simple keyword matching). There's no retrieval quality scoring — querying the wrong topic gets the same signal as not querying at all. Scoring KB query relevance would elevate this significantly.

---

## Detailed Technical Verification

### Fix 1: Graduated Difficulty Scaling ✅

**File:** `server/graders.py`, lines 279-293

```python
# BEFORE (broken — suppressed all hard scores)
if difficulty == "hard":
    avg_score *= 0.55  # Perfect response → 0.495

# AFTER (graduated — only weak responses penalized)
if difficulty == "hard":
    if avg_score < 0.7:
        avg_score *= 0.75      # weak response on hard task
    # else: good/great response keeps its score
elif difficulty == "medium":
    if avg_score < 0.6:
        avg_score *= 0.85      # weak response on medium task
```

**Verification:** A near-perfect response (0.90) on hard now scores 0.90, not 0.495. A weak response (0.50) on hard scores 0.375, correctly penalizing poor performance. The same scaling is applied identically in `RewardEngine._compute_response_reward()` (lines 268-277).

### Fix 2: Escalation De-escalation Check ✅

**File:** `server/graders.py`, lines 296-330

```python
# BEFORE (broken — searched action dicts for task_difficulty field)
if should_escalate and any(a.get("task_difficulty") == "hard" for a in action_history):
    # Always False — actions don't store task_difficulty

# AFTER (correct — uses parameter directly)
def _grade_escalation(self, action_history, should_escalate, task_difficulty="easy"):
    respond_actions = [a for a in action_history if a.get("type") == "respond"]
    had_respond = len(respond_actions) > 0
    had_empathy = any(...)
    if task_difficulty == "hard":
        if not had_respond or not had_empathy:
            return 0.4  # Correctly triggers
```

**Verification:** Test `test_correct_escalation` now requires a `respond` action with empathy before escalating on hard, matching the grader's enforcement. Test passes.

### Fix 3: lookup_kb Discoverability ✅

**File:** `models.py`, lines 11-33 and 68-70

- `lookup_kb` added to `SupportAction` docstring with content format description
- `lookup_kb` included in `SupportObservation.available_actions` default list
- `lookup_kb` present in `environment.py` both at reset (line 141) and in `_get_available_actions()` (line 450)

### Fix 4: Reward/Grader Alignment ✅

**File:** `server/reward.py`, lines 262-277

Both `RewardEngine` and `SupportGrader` now use identical logic:
1. Same keyword-based scoring with stuffing penalty
2. Same 60%/40% semantic/keyword blend
3. Same graduated difficulty scaling thresholds and multipliers

### Fix 5: Sentiment Heuristic ✅

**File:** `server/environment.py`, lines 301-317

Three-way classification: refund refusal (-0.3), refund offer (+0.4), neutral mention (+0.1). Prevents gaming by keyword-only detection.

### Fix 6: Weight Alignment ✅

**File:** `server/graders.py`, lines 440-447 matched to `openenv.yaml`, lines 89-94

Medium weights now match exactly:

| Component | openenv.yaml | graders.py |
|---|---|---|
| classification | 0.20 | 0.20 ✅ |
| response_quality | 0.35 | 0.35 ✅ |
| escalation_decision | 0.15 | 0.15 ✅ |
| resolution | 0.20 | 0.20 ✅ |
| efficiency | 0.10 | 0.10 ✅ |

---

## Passing Tests — Verified

```bash
$ python -m pytest tests/ -q
40 passed in 25.90s
```

| Test File | Tests | Result |
|---|---|---|
| `test_api.py` | 5 | ✅ All Passed |
| `test_baseline.py` | 2 | ✅ All Passed |
| `test_concurrency.py` | 1 | ✅ Passed |
| `test_environment.py` | 11 | ✅ All Passed |
| `test_graders.py` | 17 | ✅ All Passed |
| `test_reward.py` | 4 | ✅ All Passed |

---

## Remaining Issues (Non-blocking)

| Priority | Issue | Impact | Score Impact |
|---|---|---|---|
| 🟡 Low | KB results not in `interaction_history` | Agents lose KB context in subsequent steps | -1 pt |
| 🟡 Low | Semantic scorer uses uniform weights for respond vs resolve | Mid-episode responses scored against final resolution | -1 pt |
| 🟡 Low | Customer reply generation is simplistic | Easy to learn fixed patterns | -1 pt |
| 🟢 Info | No `/metrics` endpoint | Missing observability | -1 pt |
| 🟢 Info | Sentiment dynamics are heuristic-based | Could use semantic scoring | -1 pt |
| 🟢 Info | KB retrieval quality not scored | Query relevance not reflected in reward | -1 pt |
| 🟢 Info | Hard task optimal step range is arbitrary | Could derive from ticket complexity | Informational |

---

## Recommended Improvements (Future Work)

1. **Add `/metrics` endpoint** — expose the `METRICS` dict as a public endpoint for operational monitoring.

2. **Contextual sentiment simulation** — use semantic similarity (already available via sentence-transformers) to determine if a response actually *helps* before adjusting sentiment.

3. **KB retrieval quality scoring** — add a relevance score to KB lookups. An agent that looks up "refund policy" on a password reset ticket should receive less credit.

4. **Add `lookup_kb` to interaction_history** — KB results should be visible in subsequent steps so agents can reason over what they learned.

5. **Separate respond/resolve scoring pipelines** — use empathy + solution weights for `respond` actions and resolution alignment for `resolve` actions.

6. **Derived efficiency targets** — compute optimal step ranges from ticket metadata (escalation status, category complexity) rather than fixed thresholds.

---

## Final Verdict

SupportEnv is a **high-quality, practically motivated environment** with strong fundamentals. The domain is novel for OpenEnv, the grading is correct and deterministic, the action space is well-designed, and the ticket templates are genuinely realistic. The 40-test suite with 100% pass rate shows engineering rigor.

All six critical bugs from the v1 review have been systematically fixed:
- ✅ Response difficulty scoring now uses graduated scaling
- ✅ Escalation empathy check now correctly triggers
- ✅ `lookup_kb` is fully discoverable
- ✅ RewardEngine and SupportGrader are aligned
- ✅ Sentiment heuristic requires contextual signals
- ✅ Manifest and code weights are consistent

The remaining deductions are for **areas of sophistication**, not correctness bugs. The environment is production-ready and would serve genuine value for agent training and evaluation.

---

**Score: 93 / 100**

```
Real-world utility    ████████████████████████████░░  28/30
Task & grader quality ███████████████████████░░░░░░░  23/25
Environment design    ███████████████████░░░░░░░░░░░  19/20
Code quality & spec   ██████████████░░░░░░░░░░░░░░░░  14/15
Creativity & novelty  █████████░░░░░░░░░░░░░░░░░░░░░  9/10
─────────────────────────────────────────────────────
TOTAL                 █████████████████████████████░  93/100
```

---

## Appendix: Score Delta from v1 to v3

| Category | v1 Score | v3 Score | Delta | Key Fix |
|---|---|---|---|---|
| Real-world utility | 27/30 | 28/30 | +1 | Sentiment heuristic fixed |
| Task & grader quality | 20/25 | 23/25 | +3 | Difficulty multiplier + escalation check + weights aligned |
| Environment design | 17/20 | 19/20 | +2 | Reward/grader aligned + lookup_kb discoverable |
| Code quality & spec | 12/15 | 14/15 | +2 | Docstrings complete + manifest matches code |
| Creativity & novelty | 8/10 | 9/10 | +1 | De-escalation mechanic now works as designed |
| **Total** | **84/100** | **93/100** | **+9** | |

---

*This review was conducted by examining all source files, running the full test suite (40/40 passed), and cross-referencing the implementation against the official scoring rubric. All code citations reference the current repository state as of April 2026.*
