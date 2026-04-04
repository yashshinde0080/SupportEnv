# SupportEnv — Senior Judge Evaluation Report

> **Reviewer Role:** Senior Technical Evaluator, OpenEnv Hackathon Panel
> **Review Date:** April 2026
> **Project:** SupportEnv — Customer Support RL Environment
> **Author:** Yash Shinde
> **Submission URL:** `https://huggingface.co/spaces/yashshinde0080/support-env`
> **Review Version:** v2 (Post-Remediation Audit)

---

## Executive Summary

SupportEnv is one of the most practically-grounded submissions in this cohort. It tackles a $400B+ real-world domain — customer service operations — with genuine depth: nuanced ticket templates, a 6-action multi-step workflow, semantic response grading, and a carefully designed escalation decision framework. The environment would be genuinely useful for training or benchmarking production support agents.

The codebase is well-structured, the models are strongly typed, the grading is deterministic, and the test suite is comprehensive (40 tests, 100% pass rate). There are meaningful design decisions throughout that indicate a serious approach to the problem, not a weekend hack.

That said, there are notable issues that prevent a perfect score: the grading system has internal inconsistencies between the step-level `RewardEngine` and the episode-level `SupportGrader`, the semantic scorer applies a potentially disqualifying difficulty multiplier, and the WebSocket interface has a few rough edges. These are fixable, but a judge cannot award top marks without verified end-to-end correctness.

**Final Score: 84 / 100**

---

## Score Breakdown

| Parameter | Weight | Raw Score | Weighted Score |
|---|---|---|---|
| Real-world utility | 30% | 27/30 | **27.0** |
| Task & grader quality | 25% | 20/25 | **20.0** |
| Environment design | 20% | 17/20 | **17.0** |
| Code quality & spec compliance | 15% | 12/15 | **12.0** |
| Creativity & novelty | 10% | 8/10 | **8.0** |
| **TOTAL** | **100%** | | **84 / 100** |

---

## 1. Real-World Utility — 27 / 30

### Rationale

Customer support AI is not a synthetic benchmark. It is a domain with billions of dollars in active deployment and a growing need for rigorous agent evaluation. SupportEnv fills a genuine gap: there is no established RL environment for customer support workflows in the OpenEnv ecosystem.

The domain modeling is excellent. Tickets span four meaningful categories (billing, technical, account, general) with realistic sentiment gradients from -1.0 (suicidal crisis) to +1.0 (satisfied customer). The hard task set is particularly impressive — the `Suicide Threat` and `Medical Device Failure` scenarios are not just technically hard, they are ethically hard, forcing agents to recognize crisis signals and route correctly. This is exactly the kind of high-stakes decision-making that separates a research quality environment from a toy.

### What Works Extremely Well

- **Domain Authenticity**: Ticket templates read like real support tickets, not synthetic filler. They include missing order IDs (`#{order_id}`), specific sentiment signals ("I'm contacting my bank and lawyer"), and escalation trigger phrases that reflect actual support policies.
- **Ambiguous Hard Cases**: The inclusion of deliberately non-escalation hard tickets (angry customer demanding a manager who *doesn't* need escalation — just de-escalation) is sophisticated. This tests that agents reason, not pattern-match.
- **Multi-dimensional Evaluation**: The environment models the fact that good support work is multi-step: classify → investigate → respond → de-escalate → resolve. This matches industry service desk SOP.
- **LLM-powered Generation**: The `TicketGenerator` supports both template-based and LLM-based ticket generation via `litellm`. This is significant — it means the environment can scale indefinitely and avoid agent overfitting to a fixed template pool.
- **Knowledge Base Action**: The `lookup_kb` action adds a retrieval dimension that matches how real agents operate (consulting policy documents before responding). The KB contains 10 meaningful policy entries covering refunds, identity theft, medical device malfunctions, and privacy (GDPR/CCPA).

### Deductions

**-2 pts: Sentiment simulation is weak.** `_update_sentiment()` in `environment.py` uses keyword heuristics to update the customer's sentiment, but the dynamics are too coarse. A response containing "refund" unconditionally adds +0.4 to sentiment regardless of whether the response is appropriate. Real customer sentiment is contextual — "I won't be giving you a refund" contains "refund" but should tank sentiment. The binary keyword matching in a continuous sentiment field is a well-known failure mode.

**-1 pt: Customer reply generation is simplistic.** `_generate_customer_reply()` branches on three sentiment ranges with 3-4 static responses each, making it easy for agents to learn fixed reply patterns rather than genuine response quality. A more realistic simulation would tie reply generation to what the agent actually said.

---

## 2. Task & Grader Quality — 20 / 25

### Rationale

The three-tier difficulty structure is well-executed and the graders are deterministic and reproducible. The 40-test suite confirms reliability. There are, however, some grading design issues that a judge must flag.

### What Works

- **3 Well-Differentiated Tasks**: Easy (5 steps, FAQ-style), Medium (8 steps, multi-step investigation), Hard (12 steps, high-stakes escalation). The step budget, scoring weights, and ticket complexity scale coherently.
- **Deterministic Grading**: All 10 tests for `SupportGrader` pass deterministically. Same action history → same score. This is a hard requirement and it's correctly implemented.
- **Anti-Gaming Measures**: The keyword density stuffing detector in `_grade_responses()` is well-implemented. Responses with > 30% keyword density are penalized with up to -0.5, preventing naive agents from jamming keywords to game the score.
- **Action Ordering Enforcement**: The `-0.25` penalty for resolving/escalating before classifying correctly enforces a meaningful prerequisite. This prevents "instant escalate" gaming.
- **Escalation Quality Grading**: The escalation grader doesn't just check if escalation happened — it checks the *quality of the escalation reason*. An escalation with a 10+-word reason containing keywords like "severity" or "immediate" scores 1.0. A bare escalation scores 0.7. This is good.
- **Score Range**: Verified `GradeResult.score` is clamped to `[0.0, 1.0]` via `max(0.0, min(1.0, total_score))`.

### Issues

**-3 pts: Response difficulty multipliers are mechanically broken and cause score inversion.**

```python
# graders.py – _grade_responses()
if difficulty == "hard":
    avg_score *= 0.55  # Requires almost perfect response to get a 0.5+ score
elif difficulty == "medium":
    avg_score *= 0.75
```

This is the most serious grading defect. Consider what happens when an agent provides an objectively excellent response on a hard ticket:

- A near-perfect response might compute an `avg_score` of 0.85 before the multiplier.
- After the 0.55 multiplier: `0.85 × 0.55 = 0.467`.
- The agent scores 0.467 on `response_quality` for an excellent response on a hard task.

This makes hard tasks structurally impossible to score well on the `response_quality` component, which carries 25% of the total hard-task grade. The intent — "harder tasks should require better responses" — is correct. The implementation is wrong. The multiplier should be applied differently: raise the threshold for what counts as "good," not suppress the raw score.

The correct approach is to require higher semantic similarity for hard tasks rather than penalizing the absolute score. For example:
- Easy: baseline threshold for `A`-grade response = 0.65 similarity
- Medium: threshold = 0.75 similarity
- Hard: threshold = 0.85 similarity

**-1 pt: Grading weight inconsistency between openenv.yaml and graders.py.**

```yaml
# openenv.yaml
hard:
  response_quality: 0.25
  escalation: 0.35
```

```python
# graders.py – _get_weights() for hard
"response_quality": 0.25,
"escalation_decision": 0.35,
```

These match, but the `medium` weights differ. `openenv.yaml` declares `response_quality: 0.35, escalation: 0.15` for medium, while `graders.py` uses `response_quality: 0.30, escalation: 0.10`. The manifest is the contract — these must match.

**-1 pt: Escalation de-escalation check is fragile.**

The de-escalation requirement for `hard` difficulty checks:
```python
if should_escalate and any(a.get("task_difficulty") == "hard" for a in action_history):
```

Actions in `action_history` are not stored with a `task_difficulty` field (confirmed by inspecting `environment.py`). This condition will never be true, silently bypassing the de-escalation penalty entirely, making the hard escalation check easier than documented.

---

## 3. Environment Design — 17 / 20

### Rationale

The environment architecture is clean and well-organized. The OpenEnv interface is correctly implemented, concurrent sessions are supported, and the episode lifecycle is sensible. The design decisions are defensible. There are a few areas that need attention.

### What Works

- **Clean State Management**: `SupportState` and `PublicSupportState` are properly separated. The `target_category`, `target_resolution`, and `requires_escalation` fields are marked `exclude=True` in `SupportState`, preventing information leaks through the `/api/state` endpoint. This is correctly implemented.
- **Concurrent Sessions**: `SUPPORTS_CONCURRENT_SESSIONS = True` and the `environments` dict with TTL (`SESSION_TTL_SECONDS = 3600`) enable multiple simultaneous users. Session cleanup on reset is implemented.
- **Isolated RNG**: Each environment instance and `TicketGenerator` uses `random.Random(seed)` rather than the global `random` module. This is the correct approach for reproducibility — global state leakage between episodes is avoided.
- **Dense Rewards**: The `RewardEngine` provides rewards at every step for classification, responses, escalation, and KB lookups. This is correct — sparse rewards (only at episode end) would make learning significantly harder.
- **Episode Boundaries**: Episodes terminate at `max_steps`, on `resolve`, or on `escalate`. The `done` flag is properly set and returned in observations.
- **6-Action Space**: `classify | respond | escalate | request_info | resolve | lookup_kb` is well-designed. Each action has a clear purpose, and the KB action adds a meaningful information-retrieval dimension.
- **Curriculum Mode**: The `/curriculum` endpoint exposes adaptive difficulty thresholds (`easy_to_medium: 0.65`, `medium_to_hard: 0.85`). This is a thoughtful addition for training agents progressively.

### Issues

**-2 pts: RewardEngine and SupportGrader are misaligned.**

Both compute response quality independently using completely different methodologies. The `RewardEngine` uses keyword counting with a stuffing penalty. The `SupportGrader` uses keyword counting + 60%-weighted semantic similarity from sentence-transformers. An agent could receive a high reward-per-step from the `RewardEngine` but a low episode grade from the `SupportGrader` through identical behavior. This breaks the expected property of RL environments: rewards should be predictive of episode outcome.

**-1 pt: `lookup_kb` action does not emit a proper observation message.**

When an agent calls `lookup_kb`, the environment returns the KB content in `observation.message`. However, this message is not reliably propagated into `interaction_history`. An agent using the KB cannot easily see what it learned in subsequent steps. The KB result should be appended to `interaction_history` as a `{"role": "system", "content": kb_result}` entry.

---

## 4. Code Quality & Spec Compliance — 12 / 15

### Rationale

This is a well-engineered codebase. Models are Pydantic-typed, endpoints are documented, tests cover the critical paths, and the Dockerfile is production-ready. Some spec compliance gaps remain.

### What Works

- **Typed Models**: `SupportAction`, `SupportObservation`, `SupportState`, `PublicSupportState` are all Pydantic models with field-level validation (`ge`, `le`, `Field`). The `Literal` type constraint on `action_type` means invalid actions are rejected at model validation time, before any application code runs.
- **Test Suite**: 40 tests across 5 test files. Coverage spans environment basics, action handling, grader determinism, API endpoints, baseline reproducibility, concurrency, and the reward engine. A 100% pass rate is verified.
- **Dockerfile**: The Dockerfile correctly pre-downloads the `all-MiniLM-L6-v2` model during build:
  ```dockerfile
  RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
  ```
  This prevents cold-start latency on HuggingFace Spaces and means the model is always available without network dependency at runtime.
- **Session TTL**: Sessions expire after 1 hour and are cleaned up on reset, preventing memory leaks in long-running deployments.
- **CORS**: Wildcard CORS is appropriate for an evaluation environment. Not appropriate for production but correct here.
- **Metrics Tracking**: The `METRICS` dict and `_update_metrics()` function provide basic observability. A `/metrics` endpoint would complete this nicely.
- **Models docstrings**: Every model class and field has meaningful documentation. The `SupportAction` docstring explicitly specifies what `content` should contain for each `action_type`. Rare and valued.

### Issues

**-2 pts: `openenv validate` cannot be confirmed.**

The manifest `openenv.yaml` exists and is well-structured, but the submission does not include evidence of a passing `openenv validate` run. Judges must assume it passes based on structural inspection, but this requirement is explicitly in the rubric.

**-1 pt: `models.py` SupportAction missing `lookup_kb` in docstring.** 

The `action_type` docstring lists five actions but omits `lookup_kb`. The `Literal` type correctly includes it, but the documentation is incomplete:
```python
# models.py - line 17
# Missing: "lookup_kb": search the knowledge base for policy/information
```

Also, the `available_actions` default in `SupportObservation` does not include `lookup_kb`:
```python
available_actions: List[str] = Field(default_factory=lambda: [
    "classify", "respond", "escalate", "request_info", "resolve"
    # "lookup_kb" is missing here
])
```

Agents receiving observations will not see `lookup_kb` listed as available, creating a discoverability gap.

---

## 5. Creativity & Novelty — 8 / 10

### Rationale

Customer support is not a domain we've seen in OpenEnv, and the mechanics are genuinely interesting. Several design choices show original thinking.

### What Works

- **Mental Health Crisis Scenario**: Including a suicide-threat ticket template (sentiment -1.0, mandatory escalation) is not just creative — it's practically important. Any real support agent AI needs to handle this correctly. Including it in an RL environment is novel and valuable.
- **De-escalation Before Escalation**: The hard task design requires agents to attempt empathetic de-escalation *before* routing to a human. This is a real operational constraint in customer service — it prevents agents from simply dumping all difficult customers. The mechanic is elegant.
- **Hybrid Semantic Grading**: The 60/40 (semantic/keyword) blend in `_grade_responses()` is a thoughtful design. Sentence-transformer cosine similarity against `expected_resolution` captures whether the agent actually addressed the issue, not just whether it said the right words.
- **Customer Personality System**: `_generate_with_llm()` assigns personalities (`neutral`, `aggressive`, `friendly`, `anxious`). This adds variability to customer simulation that purely template-based environments lack.
- **Ambiguous Escalation Tests**: Two hard tickets (`ANGRY: Product completely broken`, `You ruined my weekend plan!!!`) have angry customers demanding escalation but `requires_escalation: False`. An agent must recognize that anger alone ≠ warranted escalation. This is genuinely clever.
- **LLM Ticket Generation**: The `litellm` integration enables on-demand ticket generation from any configured model. The environment can self-extend its training set without manual template creation.

### Deductions

**-2 pts: KB mechanics are underdeveloped.** The `lookup_kb` action is one of the most interesting design choices, but the KB itself is thin (10 entries, simple keyword matching). There's no retrieval quality scoring — an agent that looks up the wrong thing gets the same neutral signal as one that doesn't look up at all. A version where KB query relevance affects the score would elevate this significantly.

---

## Detailed Technical Findings

### Finding 1: Escalation Task Difficulty Check Bug

**File:** `server/graders.py`, line 313

```python
# Current (WRONG) - action_history contains {"type": ..., "content": ...}, not "task_difficulty"
if should_escalate and any(a.get("task_difficulty") == "hard" for a in action_history):
    if not had_respond or not had_empathy:
        return 0.4  # Never actually triggered
```

**Expected behavior:** Hard tasks require de-escalation attempt before escalation.
**Actual behavior:** Condition never evaluates to True; all escalations on hard tasks score full credit regardless of de-escalation attempt.

**Fix:**
```python
# Pass task_difficulty as parameter instead of checking action fields
def _grade_escalation(self, action_history, should_escalate, task_difficulty="easy"):
    ...
    if should_escalate and task_difficulty == "hard":
        if not had_respond or not had_empathy:
            return 0.4
```

---

### Finding 2: Response Difficulty Multiplier Causes Score Suppression

**File:** `server/graders.py`, lines 282-285

```python
if difficulty == "hard":
    avg_score *= 0.55
elif difficulty == "medium":
    avg_score *= 0.75
```

**Impact:** A semantically excellent hard response (avg_score = 0.90) produces `response_quality = 0.495`. This component then contributes `0.495 × 0.25 (weight) = 0.12` to the total score — less than in easy mode where the same response would contribute `0.90 × 0.40 = 0.36`. Hard tasks are rewarded *less* for excellent responses than easy tasks, not more.

**Correct approach:**
```python
# Require higher minimum semantic similarity for harder tasks
DIFFICULTY_THRESHOLDS = {"easy": 0.55, "medium": 0.70, "hard": 0.80}
threshold = DIFFICULTY_THRESHOLDS.get(difficulty, 0.55)
# Scale score relative to this threshold
normalized = (avg_score - threshold) / (1.0 - threshold)
avg_score = max(0.0, min(1.0, normalized))
```

---

### Finding 3: `lookup_kb` Not Listed in Available Actions

**File:** `models.py`, line 66-68

```python
available_actions: List[str] = Field(default_factory=lambda: [
    "classify", "respond", "escalate", "request_info", "resolve"
    # Missing: "lookup_kb"
])
```

An agent receiving observations from the environment has no way to discover `lookup_kb` exists unless it reads external documentation. The action schema in `/tasks` correctly includes it, but the per-step observation does not.

---

### Finding 4: Semantic Scorer `overall` Weighting is Resolution-Heavy

**File:** `server/semantic_scorer.py`, line 63

```python
overall = (empathy_score * 0.2) + (solution_score * 0.2) + (resolution_score * 0.6)
```

`resolution_score` measures similarity between the agent's *response* (not the resolution action) and the `expected_resolution`. For a mid-episode respond action, the agent hasn't resolved anything yet — it's trying to gather info or de-escalate. Scoring a `respond` action against the final resolution target inflates the baseline for all intermediate responses and reduces the predictive accuracy of the semantic score for responses vs. resolution steps.

**Recommendation:** Use separate scoring pipelines for `respond` actions (empathy + solution) and `resolve` actions (resolution alignment). The current uniform weighting blurs this distinction.

---

### Finding 5: Sentiment Heuristic Rewards "refund" Keyword Unconditionally

**File:** `server/environment.py`, lines 298-311

```python
has_refund = "refund" in response_lower
if has_refund:
    sentiment += 0.4
```

A response saying "I'm sorry but we cannot process your refund request at this time" contains "refund" and would improve customer sentiment by +0.4. This is backwards. Refusal/unavailability of a refund should generally decrease sentiment. The heuristic matches the presence of the *topic*, not the *resolution* of the topic.

---

## Passing Tests — Verified

```bash
$ pytest tests/ -v
# Result: 40 passed in 25.88s
```

| Test File | Tests | Result |
|---|---|---|
| `test_api.py` | 5 | ✅ All Passed |
| `test_baseline.py` | 2 | ✅ All Passed |
| `test_concurrency.py` | 1 | ✅ Passed |
| `test_environment.py` | 18 | ✅ All Passed |
| `test_graders.py` | 10 | ✅ All Passed |
| `test_reward.py` | 4 | ✅ All Passed |

---

## Required Fixes (Blocking for 90+ Score)

| Priority | Issue | File | Impact |
|---|---|---|---|
| 🔴 Critical | Response difficulty multiplier causes score suppression | `graders.py:282` | -3 pts |
| 🔴 Critical | Escalation de-escalation check never triggers | `graders.py:313` | -2 pts |
| 🟡 High | `lookup_kb` not in `available_actions` default | `models.py:66` | -1 pt |
| 🟡 High | `openenv validate` output not included | submission | -2 pts |
| 🟡 High | RewardEngine and SupportGrader misaligned | `reward.py`, `graders.py` | -2 pts |
| 🟠 Medium | Sentiment "refund" keyword is unconditional | `environment.py:298` | -1 pt |
| 🟠 Medium | Semantic scorer resolution weighting for mid-episode responses | `semantic_scorer.py:63` | -1 pt |
| 🟢 Low | `SupportAction` docstring missing `lookup_kb` | `models.py:17` | -0.5 pt |
| 🟢 Low | openenv.yaml medium weights don't match graders.py | `openenv.yaml:89` | -1 pt |

---

## Recommended Improvements (Non-blocking)

1. **Add `/metrics` endpoint** — expose the `METRICS` dict as a public endpoint. Useful for operators monitoring the environment in production.

2. **Contextual sentiment simulation** — use semantic similarity (already available via sentence-transformers) to determine if a response actually *helps* before adjusting sentiment, rather than keyword matching.

3. **KB retrieval quality scoring** — add a relevance score to KB lookups. An agent that looks up "refund policy" on a password reset ticket should receive less credit than one that looks up "account access."

4. **Add `lookup_kb` to interaction_history** — KB results should be visible in subsequent observation steps so agents can reason over what they learned.

5. **Telemetry for hard tasks** — add structured logging for cases where an agent misses escalation on a hard ticket. This makes post-training analysis easier and demonstrates environment thoughtfulness.

---

## Final Verdict

SupportEnv is a high-quality, practically motivated environment with strong fundamentals. The domain is novel for OpenEnv, the grading is mostly correct and deterministic, the action space is well-designed, and the ticket templates are genuinely realistic. The 40-test suite with 100% pass rate shows engineering rigor.

The five bugs identified — particularly the response difficulty multiplier and the broken escalation de-escalation check — are not trivial. They mean the environment grades differently than documented, which undermines trust in the scores. These are fixable in a few hours of work.

With those fixes applied, this environment comfortably deserves a 90+ score. As submitted, 84/100.

---

**Score: 84 / 100**

```
Real-world utility    ████████████████████████████░░  27/30
Task & grader quality ████████████████████░░░░░░░░░░  20/25
Environment design    █████████████████░░░░░░░░░░░░░  17/20
Code quality & spec   ████████████░░░░░░░░░░░░░░░░░░  12/15
Creativity & novelty  ████████░░░░░░░░░░░░░░░░░░░░░░  8/10
─────────────────────────────────────────────────────
TOTAL                 ████████████████████████████░░  84/100
```

---

*This review was conducted by examining all source files, running the test suite, and cross-referencing the implementation against the official scoring rubric. All code citations reference the current repository state as of April 2026.*
