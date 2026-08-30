# Phase 3 Evidence Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace silent deterministic fallback with validated, JD-grounded, turn-cited scoring that reports 70%岗位胜任度 and 30%本场表现, exposes coverage/confidence, and can be retried safely.

**Architecture:** A deterministic cleaner converts authoritative final transcript rows into stable question-answer pairs and quality warnings. Bailian analyzes only those pairs against a strict schema; backend code validates evidence IDs and computes weighted totals. Failed analysis is stored as retryable status and never updates the ability tree.

**Tech Stack:** FastAPI, Pydantic, httpx, Python 3.11, React 18, TypeScript, pytest, Vitest.

**Spec:** `docs/superpowers/specs/2026-08-29-interview-reliability-and-evidence-design.md`

## Global Constraints

- JD-grounded dimensions carry 70 points; interview-performance dimensions carry 30.
- Every scored dimension cites existing `turn_id` values.
- `not_covered` is not scored as zero; coverage is displayed separately.
- Coverage below 60% produces a provisional result.
- A timeout or invalid model response produces no official score and no ability-tree mutation.
- Existing failed/fallback reports remain readable historical data but are not reused for new analysis.

---

### Task 1: Transcript Cleaning And Question-Answer Pairing

**Files:**
- Create: `services/api/app/report_evidence.py`
- Create: `services/api/tests/test_report_evidence.py`

**Interfaces:**
- Produces Pydantic models `EvidenceTurn(turn_id, question, answer, source, warnings)` and `CleanTranscript(turns, warnings, candidate_turn_count, covered_turn_count)`.
- Consumes Phase 1 transcript rows with `speaker`, `text`, `turn_id`, `source`.

- [ ] **Step 1: Write failing pairing tests**

Use this compact regression fixture:

```python
transcript = [
    {"speaker": "assistant", "text": "你如何用MCAP定位轨迹拼接？", "turn_id": "a1", "source": "application"},
    {"speaker": "candidate", "text": "呃。", "turn_id": "u1", "source": "provider_asr"},
    {"speaker": "assistant", "text": "请从预测轨迹和执行轨迹的差异说起。", "turn_id": "a2", "source": "provider"},
    {"speaker": "candidate", "text": "我对比模型预测和实机执行轨迹，发现段间时间戳回退。", "turn_id": "u2", "source": "provider_asr"},
    {"speaker": "candidate", "text": "整场浏览器重复内容", "turn_id": "b1", "source": "browser_asr"},
]
clean = clean_transcript(transcript, authoritative_asr="provider_asr")
assert [turn.turn_id for turn in clean.turns] == ["u1", "u2"]
assert clean.turns[0].warnings == ("low_information",)
assert clean.turns[1].question == "请从预测轨迹和执行轨迹的差异说起。"
```

- [ ] **Step 2: Add contamination and duplicate tests**

Assert non-authoritative ASR is excluded, exact duplicate final answers collapse by `turn_id`, and a candidate answer longer than 300 characters containing an earlier interviewer question gets `suspected_role_contamination`.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_report_evidence.py -v`

- [ ] **Step 4: Implement deterministic cleaning**

Pair each candidate final with the most recent unmatched assistant final. Keep `不知道`, `没有考虑`, and safety admissions as evidence; only mark pure filler such as `呃`, `嗯`, and punctuation as low information.

- [ ] **Step 5: Run tests and commit**

Commit: `feat: clean authoritative interview evidence`

---

### Task 2: Strict Report Analysis Schema

**Files:**
- Modify: `services/api/app/reporting.py`
- Modify: `services/api/tests/test_reporting.py`

**Interfaces:**
- Produces Pydantic models `DimensionAnalysis`, `ReportAnalysis`, `PracticeAction`.
- Produces `_parse_report_analysis(content, valid_turn_ids) -> ReportAnalysis`.

- [ ] **Step 1: Write failing schema tests**

Define seven exact dimension keys and maxima:

```python
DIMENSION_MAX = {
    "job_relevance": 20,
    "technical_depth": 20,
    "engineering_evidence": 15,
    "problem_solving_and_safety": 15,
    "answer_structure": 10,
    "communication_clarity": 10,
    "honesty_and_reflection": 10,
}
```

Assert parsing rejects an unknown dimension, score above max, duplicate dimension, missing dimension, and an evidence ID not present in `valid_turn_ids`.

- [ ] **Step 2: Add valid-response parsing test**

Use all seven dimensions, evidence `u2`, strengths, gaps, `not_covered`, and practice actions. Assert the parsed object preserves evidence IDs and numeric scores.

- [ ] **Step 3: Run tests and confirm failure**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_reporting.py -k schema -v`

- [ ] **Step 4: Implement strict Pydantic validation**

Use `Literal` dimension names, `extra="forbid"`, and one post-validation function that compares returned dimension keys to `DIMENSION_MAX` and evidence IDs to the cleaned turn set.

- [ ] **Step 5: Run tests and commit**

Commit: `feat: validate evidence report schema`

---

### Task 3: JD-Grounded Prompt And Text Client Deadline

**Files:**
- Modify: `services/api/app/reporting.py`
- Modify: `services/api/app/integrations/bailian/text_client.py`
- Modify: `services/api/tests/test_reporting.py`
- Modify: `services/api/tests/test_bailian_text_client.py`

**Interfaces:**
- Changes `generate_analyzed_report(..., context, text_client)` to consume JD focus and cleaned evidence.
- Adds per-operation timeout support to `BailianTextClient._complete`.

- [ ] **Step 1: Write a failing prompt test**

Capture the prompt passed to a fake text client and assert it includes target role, role direction, JD focus points, seven dimensions/maxima, cleaned turn IDs, and the instruction `没有证据时写入not_covered，不得编造或按零分处理`.

- [ ] **Step 2: Write a failing timeout propagation test**

Assert `analyze_report` passes `httpx.Timeout(connect=10, read=120, write=30, pool=10)` while `next_question` retains its current short interactive deadline.

- [ ] **Step 3: Run focused tests and confirm failure**

- [ ] **Step 4: Build the analysis prompt from structured JSON**

Serialize only:

```python
{
    "target_role": context.target_role,
    "role_direction": context.role_direction,
    "focus_points": list(context.interview_focus),
    "dimensions": DIMENSION_MAX,
    "turns": [turn.model_dump() for turn in clean.turns],
    "quality_warnings": list(clean.warnings),
}
```

Do not send transport events, raw audio metrics, full resume text, or ability-tree history.

- [ ] **Step 5: Implement the report-specific timeout and commit**

Commit: `fix: bound and ground report analysis requests`

---

### Task 4: Deterministic Aggregation, Coverage, And Confidence

**Files:**
- Modify: `services/api/app/reporting.py`
- Modify: `services/api/tests/test_reporting.py`

**Interfaces:**
- Produces report fields `score`, `coverage`, `confidence`, `provisional`, `dimensions`.
- Backend computes totals; model cannot return final total.

- [ ] **Step 1: Write failing aggregation tests**

For covered dimensions totaling 45/60, assert:

```python
summary = aggregate_analysis(analysis)
assert summary["score"] == {"earned": 75.0, "max": 100}
assert summary["coverage"] == 60.0
assert summary["provisional"] is False
```

For 25% coverage, assert `provisional is True` and that uncovered dimensions do not add zero to the numerator.

- [ ] **Step 2: Write confidence tests**

Confidence is `low` if transcript has `suspected_role_contamination`, `medium` if any scored dimension has fewer than two evidence turns, otherwise `high`. The report preserves per-dimension model confidence but backend chooses overall confidence by the conservative rule.

- [ ] **Step 3: Run focused tests and confirm failure**

- [ ] **Step 4: Implement aggregation from validated dimensions**

Calculate `earned_percent = round(sum(score) / sum(covered max_score) * 100, 1)` and `coverage = round(sum(covered max_score) / 100 * 100, 1)`. Set `provisional = coverage < 60`.

- [ ] **Step 5: Run tests and commit**

Commit: `feat: compute transparent interview scores`

---

### Task 5: Retryable Analysis Endpoint And Ability-Tree Safety

**Files:**
- Modify: `services/api/app/routers/interviews.py`
- Modify: `services/api/app/storage.py`
- Modify: `services/api/tests/test_interviews.py`

**Interfaces:**
- `POST /api/interviews/{id}/analyze` returns successful report or HTTP 502/504 with retryable detail.
- Stores `analysis = { status, error_type, message, attempted_at }` separately from `report`.
- Accepts query `retry=true` to rerun a failed analysis; successful reports remain idempotent.

- [ ] **Step 1: Write failing ReadTimeout behavior test**

Inject a text client raising `httpx.ReadTimeout` and assert status 504, stored `analysis.status == "failed"`, no `report`, and no ability-tree write.

- [ ] **Step 2: Write failing invalid-model-output test**

Return JSON with an unknown evidence ID and assert status 502 with `error_type="invalid_analysis"`.

- [ ] **Step 3: Write successful retry test**

First attempt fails, second request with `retry=true` succeeds, writes one report, and updates the ability tree exactly once.

- [ ] **Step 4: Run focused tests and confirm failure**

- [ ] **Step 5: Remove silent fallback from `generate_analyzed_report`**

Raise typed `ReportAnalysisTimeout` and `InvalidReportAnalysis`. The route maps them to 504/502 and stores failure metadata. Keep `generate_report` only for explicit mock-report tests; never call it from a real interview analysis failure.

- [ ] **Step 6: Run tests and commit**

Commit: `fix: make report analysis failure retryable`

---

### Task 6: Report UI With Evidence, Coverage, And Retry

**Files:**
- Modify: `apps/web/src/api/client.ts`
- Modify: `apps/web/src/pages/ReportPage.tsx`
- Modify: `apps/web/src/styles.css`
- Create: `apps/web/src/pages/reportView.test.ts`
- Create: `apps/web/src/pages/reportView.ts`

**Interfaces:**
- Produces pure `buildReportSections(report)` for testable display projection.
- Consumes HTTP 502/504 JSON detail and retries with `retry=true`.

- [ ] **Step 1: Write failing report projection tests**

Assert the projection includes `75.0/100`, `覆盖率 60%`, `阶段性评分` when provisional, each dimension/max pair, and evidence links keyed by turn ID.

- [ ] **Step 2: Write failing retry-state tests**

Extract a reducer with `saving | analyzing | complete | failed`; assert failed analysis retains the interview ID and transitions back to analyzing on retry.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `npm test -- --run src/pages/reportView.test.ts`

- [ ] **Step 4: Implement truthful generation states**

ReportPage starts in analyzing only after Phase 1 persistence. On 502/504, show backend detail and a `重新分析` button. Do not create a mock report when a real interview ID is missing; show a navigation error instead.

- [ ] **Step 5: Render evidence and transcript anchors**

Give transcript rows IDs `turn-${turn_id}`. Evidence buttons scroll to those rows. Display total/max, coverage, confidence, dimensions, strengths, gaps, actions, and transcript in that order.

- [ ] **Step 6: Run tests/build and commit**

Commit: `feat: show retryable evidence-based reports`

---

### Task 7: Real Interview Regression Fixture

**Files:**
- Create: `services/api/tests/fixtures/long_bailian_transcript.json`
- Modify: `services/api/tests/test_reporting.py`

**Interfaces:** Fixture contains no raw audio, credentials, full resume, or personal contact information.

- [ ] **Step 1: Create a compact 12-turn fixture from the verified interview themes**

Include MCAP prediction/execution comparison, timestamp filtering, 25-to-32-point buffering, quintic spline, Slerp, pure-inference latency, missing safety constraints, joint-limit reliance on estop, and Sim2Real filtering. Paraphrase personal/company identifiers while preserving technical evidence.

- [ ] **Step 2: Add a deterministic prompt/validation regression**

Use a fake model response and assert strengths cite the MCAP/spline/Slerp turns, gaps cite missing quantitative validation/end-to-end latency/safety constraints, and every cited ID exists.

- [ ] **Step 3: Assert no generic fixed gaps remain**

Verify the output does not inject `MoveIt规划链路` or `控制器参数整定` unless those gaps are present in the fake model response with evidence.

- [ ] **Step 4: Run tests and commit**

Commit: `test: cover long evidence-based interview report`

---

### Task 8: Phase 3 Verification And Documentation

**Files:**
- Modify: `docs/issues.md`
- Modify: `knowledge-graph/04-概念卡/面试评分体系.md` if present; otherwise modify the existing scoring concept card.
- Modify: `knowledge-graph/02-面试问答/` report-related note.

**Interfaces:** None.

- [ ] **Step 1: Run full automated verification**

Run full pytest, Vitest, and production build.

- [ ] **Step 2: Reanalyze a copied clean version of the latest long interview**

Do not overwrite the historical fallback report. Create a new test session payload containing its cleaned authoritative turns, run real Bailian analysis once, and verify all evidence links, 70/30 maxima, coverage, confidence, and retry behavior.

- [ ] **Step 3: Failure smoke**

Force a text-client timeout and verify the UI shows failure/retry, storage has no official report, and the ability tree is unchanged.

- [ ] **Step 4: Append issue resolutions and commit**

Commit: `docs: record evidence reporting verification`
