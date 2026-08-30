# Phase 2 Interview Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every interview a selected duration, topic, stage budget, current objective, visible timer, and reliable automatic close while limiting each interviewer turn to one focused question.

**Architecture:** A pure backend `InterviewPlan` computes stage deadlines and one evidence objective at a time. The realtime router owns authoritative time and sends stage events; provider adapters compile the same control state into provider-specific instructions. The frontend displays server-derived state and does not decide when the interview ends.

**Tech Stack:** FastAPI, asyncio, Python dataclasses, React 18, TypeScript, Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-08-29-interview-reliability-and-evidence-design.md`

## Global Constraints

- Duration choices are exactly 15, 30, 45, or 60 minutes; default is 30.
- Topics are exactly `comprehensive`, `project_deep_dive`, `motion_control`, or `robot_systems`.
- The server owns stage transitions and the end time.
- Bailian receives stage updates; MiniCPM stage updates are best effort and cannot reset model KV.
- One turn has one evidence objective, no more than 80 Chinese characters, and no more than one question mark.
- Pure realtime audio remains best effort; do not claim strict spoken-output post-processing.

---

### Task 1: Interview Control Types And Query Validation

**Files:**
- Create: `services/api/app/interview_control.py`
- Modify: `services/api/app/routers/interviews.py`
- Modify: `services/api/tests/test_interviews.py`
- Modify: `apps/web/src/realtime/useInterviewSession.ts`
- Modify: `apps/web/src/realtime/useInterviewSession.test.ts`

**Interfaces:**
- Produces Python `InterviewControl(duration_minutes, topic, audio_mode)`.
- Produces TypeScript selection fields `durationMinutes` and `topic`; consumes the Phase 1 `audioMode` field.

- [ ] **Step 1: Write failing backend validation tests**

```python
from app.interview_control import InterviewControl

def test_interview_control_rejects_unsupported_duration():
    with pytest.raises(ValueError, match="duration"):
        InterviewControl.from_query("20", "comprehensive", "full_duplex")

def test_interview_control_defaults_are_stable():
    assert InterviewControl.from_query(None, None, None) == InterviewControl(
        duration_minutes=30,
        topic="comprehensive",
        audio_mode="full_duplex",
    )
```

- [ ] **Step 2: Write a failing realtime URL test**

Assert `buildRealtimeUrl` includes `duration_minutes=30&topic=project_deep_dive&audio_mode=full_duplex`.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_interviews.py -k interview_control -v`

Run: `npm test -- --run src/realtime/useInterviewSession.test.ts`

- [ ] **Step 4: Implement immutable validated control types**

Use `Literal` aliases and explicit membership checks. Parse query values before creating the provider session. Return WebSocket policy error code 1008 for invalid values.

- [ ] **Step 5: Persist control fields in the Ledger constructor/payload**

Add `duration_minutes`, `topic`, and `audio_mode` to the session JSON root.

- [ ] **Step 6: Run tests and commit**

Commit: `feat: validate interview duration and topic`

---

### Task 2: Pure Stage Plan And Objective Queue

**Files:**
- Modify: `services/api/app/interview_control.py`
- Create: `services/api/tests/test_interview_control.py`

**Interfaces:**
- Produces `InterviewStage(name, starts_at_seconds, ends_at_seconds, objective)`.
- Produces `build_interview_plan(control, context) -> tuple[InterviewStage, ...]`.

- [ ] **Step 1: Write failing comprehensive-plan tests**

For 30 minutes, assert exact boundaries:

```python
plan = build_interview_plan(InterviewControl(30, "comprehensive", "full_duplex"), context)
assert [(stage.name, stage.starts_at_seconds, stage.ends_at_seconds) for stage in plan] == [
    ("warmup", 0, 180),
    ("project_deep_dive", 180, 990),
    ("job_fundamentals", 990, 1440),
    ("pressure_boundary", 1440, 1620),
    ("candidate_questions", 1620, 1800),
]
```

Assert topic interviews allocate 70% to their main stage and every stage has a non-empty objective.

- [ ] **Step 2: Write failing objective-rotation tests**

Given MoveIt, MCAP, trajectory smoothing, and Sim2Real focus points, assert `next_objective` rotates without returning the same objective twice in a row and falls back to JD focus when resume evidence is exhausted.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_interview_control.py -v`

- [ ] **Step 4: Implement deterministic stage construction**

Use integer seconds and assign rounding remainder to the main stage so the final end equals `duration_minutes * 60`. Keep topic-to-objective templates in one mapping inside `interview_control.py`.

- [ ] **Step 5: Run tests and commit**

Commit: `feat: build deterministic interview stage plans`

---

### Task 3: Measurable Interviewer Question Contract

**Files:**
- Modify: `services/api/app/interviewer_persona.py`
- Modify: `services/api/tests/test_interviewer_persona.py`
- Modify: `services/api/tests/test_bailian_adapter.py`
- Modify: `services/api/tests/test_minicpm_realtime.py`

**Interfaces:**
- Produces `build_interviewer_system_prompt(..., stage_name, question_objective, remaining_seconds)`.
- Produces `build_control_instruction(stage, objective, remaining_seconds) -> str`.

- [ ] **Step 1: Write failing prompt-contract tests**

Assert generated instructions include these exact behavioral rules:

```python
assert "只问一个问题" in prompt
assert "不超过80个汉字" in prompt
assert "最多使用一个问号" in prompt
assert "不得替候选人回答" in prompt
assert "候选人迟疑、说不知道或回答为空时，只能简化原问题或换题" in prompt
assert "当前考察目标：核验MCAP如何定位轨迹拼接错误" in prompt
```

- [ ] **Step 2: Run focused tests and confirm failure**

Expected: FAIL because the prompt has no current objective/remaining time and only a general one-question rule.

- [ ] **Step 3: Implement one canonical control instruction**

Keep identity and permanent behavior in the system prompt, then append current stage/objective/time through `build_control_instruction`. Avoid duplicating provider-specific transport text.

- [ ] **Step 4: Add weak-answer regressions**

For `LocalTextInterviewer.next_question("呃")` and `next_question("不知道")`, assert output is a shorter question and contains no explanation phrases such as `其实`, `答案是`, `可以这样回答`, or `通过TensorRT`.

- [ ] **Step 5: Run tests and commit**

Commit: `fix: constrain each interviewer turn to one objective`

---

### Task 4: Provider Stage Update Capability

**Files:**
- Modify: `services/api/app/integrations/bailian/omni_realtime.py`
- Modify: `services/api/app/integrations/minicpm/realtime.py`
- Modify: `services/api/tests/test_bailian_adapter.py`
- Modify: `services/api/tests/test_minicpm_realtime.py`

**Interfaces:**
- Produces async `update_interview_control(stage_name, objective, remaining_seconds) -> list[dict]` on both adapters.
- Bailian sends `session.update`; MiniCPM returns a local stage event without resetting the upstream session.

- [ ] **Step 1: Write a failing Bailian transport test**

Use the fake WebSocket and assert the final sent payload is:

```python
{
    "type": "session.update",
    "session": {
        "instructions": adapter.system_prompt_with_control("project_deep_dive", "核验轨迹拼接", 900)
    },
}
```

The implementation may include the unchanged audio/session fields only on initial connect; stage updates send the minimal supported session patch.

- [ ] **Step 2: Write a failing MiniCPM non-reset test**

Assert `update_interview_control` does not call upstream `stop`, `prepare`, or reconnect, and returns an `interview.stage` event with `enforcement="best_effort"`.

- [ ] **Step 3: Run focused tests and confirm failure**

- [ ] **Step 4: Implement both capabilities**

Store the current stage/objective on adapters for audit and subsequent instruction compilation. Do not mutate the base resume/JD context.

- [ ] **Step 5: Run tests and commit**

Commit: `feat: update provider interview stages`

---

### Task 5: Server-Authoritative Stage Scheduler And Timeout

**Files:**
- Modify: `services/api/app/routers/interviews.py`
- Modify: `services/api/tests/test_interviews.py`

**Interfaces:**
- Produces `interview.stage` events with `stage`, `objective`, `ends_at`, `remaining_seconds`.
- Produces automatic durable completion with reason `duration_elapsed`.

- [ ] **Step 1: Write failing scheduler tests with a short injected clock**

Extract `run_interview_schedule(session, plan, send_event, finalize, sleep)` so tests can inject a no-wait sleep. Assert stage events arrive in plan order, `update_interview_control` is called for each stage, and finalization runs once with `completed/duration_elapsed`.

- [ ] **Step 2: Write a disconnect cancellation test**

Assert cancelling the scheduler task during browser disconnect does not invoke duration finalization after the Ledger was stored as disconnected.

- [ ] **Step 3: Run focused tests and confirm failure**

- [ ] **Step 4: Implement one scheduler task per ready session**

Start it only after `session.ready`. Share the existing idempotent finalizer from Phase 1. Cancel and await the scheduler in `finally`. At each transition call the provider update first, record/send returned events, then send the normalized stage event.

- [ ] **Step 5: Run tests and commit**

Commit: `feat: enforce interview stage deadlines`

---

### Task 6: Setup Controls And Interview Timer UI

**Files:**
- Modify: `apps/web/src/pages/SetupPage.tsx`
- Modify: `apps/web/src/pages/InterviewPage.tsx`
- Modify: `apps/web/src/realtime/useInterviewSession.ts`
- Modify: `apps/web/src/realtime/useInterviewSession.test.ts`
- Modify: `apps/web/src/styles.css`

**Interfaces:**
- Consumes `interview.stage` and `session.persisted`.
- Produces selected duration/topic/audio mode in `InterviewSessionSelection`.

- [ ] **Step 1: Add pure formatting tests**

Add and test:

```ts
export function formatRemainingTime(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
}
```

Assert `formatRemainingTime(125) === "02:05"` and negative values produce `00:00`.

- [ ] **Step 2: Run tests and confirm failure**

- [ ] **Step 3: Add compact setup controls**

Use selects for duration and topic, and a checkbox for playback gate. Defaults are 30 minutes, comprehensive, full duplex. Include the values in the setup summary so the candidate sees the planned session before starting.

- [ ] **Step 4: Render current stage and countdown**

On `interview.stage`, store `ends_at` and update visible remaining time once per second using local wall time. Never use the local timer to end the session. Show `即将自动结束` under two minutes.

- [ ] **Step 5: Run tests/build and commit**

Run: `npm test -- --run`

Run: `npm run build`

Commit: `feat: configure and display interview stages`

---

### Task 7: Phase 2 Verification And Documentation

**Files:**
- Modify: `docs/issues.md`
- Modify: `knowledge-graph/04-概念卡/实时语音链路.md`
- Modify: `knowledge-graph/02-面试问答/面试评分体系.md` if present; otherwise update the closest existing interview-flow note.

**Interfaces:** None.

- [ ] **Step 1: Run full backend/frontend verification**

Run the full pytest suite, Vitest suite, and production build.

- [ ] **Step 2: Run a 15-minute accelerated schedule smoke**

Use an injected accelerated clock in backend integration tests and one real two-stage Bailian session. Verify stage updates do not reconnect, the UI countdown follows server stages, and duration finalization produces `session.persisted` once.

- [ ] **Step 3: Review a realtime transcript for compound questions**

Record question length and question-mark count for at least ten generated turns. Mark prompt enforcement as best effort if any spoken turn exceeds the contract; do not hide violations.

- [ ] **Step 4: Append issue resolutions and commit**

Commit: `docs: record interview orchestration verification`
