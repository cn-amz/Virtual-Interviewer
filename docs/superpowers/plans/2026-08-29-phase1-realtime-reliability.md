# Phase 1 Realtime Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make provider readiness, transcription ownership, message turns, interview exit, durable completion, and long-session storage reliable without disabling Bailian full duplex.

**Architecture:** The backend owns provider readiness and durable session completion. Provider adapters preserve stable turn identifiers and identify the authoritative ASR source. The frontend projects messages by turn identity, uses provider-specific transcription, and waits for `session.persisted` before entering the report page.

**Tech Stack:** FastAPI, Python 3.11, Pydantic settings, websockets/httpx, React 18, TypeScript, Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-08-29-interview-reliability-and-evidence-design.md`

## Global Constraints

- Bailian remains full duplex by default.
- Bailian uses provider ASR only; MiniCPM uses browser ASR until local ASR exists.
- Do not modify MiniCPM model weights or Comni reload behavior.
- Do not persist raw audio or one durable event per 8 ms audio packet.
- Preserve the existing Bailian and MiniCPM provider selection paths.
- Add no frontend dependency.

---

### Task 1: Provider Readiness Endpoint

**Files:**
- Modify: `services/api/app/routers/interviews.py`
- Modify: `services/api/app/config.py`
- Modify: `services/api/tests/test_interviews.py`
- Modify: `apps/web/src/api/client.ts`

**Interfaces:**
- Produces: `GET /api/interviews/providers/{provider}/status`
- Produces: `ProviderStatus = { provider, state, detail, queue_length }`
- Consumes: existing `MINICPM_REALTIME_URL` and Comni `/status` response.

- [ ] **Step 1: Write failing backend tests for idle, loading, offline, and Bailian status**

Add tests that inject an async status loader into a helper and assert the normalized response:

```python
def test_normalize_minicpm_status_reports_loading():
    from app.routers.interviews import normalize_minicpm_status

    assert normalize_minicpm_status({"idle_workers": 0, "loading_workers": 1, "busy_workers": 0, "queue_length": 0}) == {
        "provider": "minicpm",
        "state": "loading",
        "detail": "模型正在加载或重置",
        "queue_length": 0,
    }
```

Also assert that configured Bailian returns `idle` and an unreachable MiniCPM gateway returns `offline` without a 500 response.

- [ ] **Step 2: Run the focused backend test and confirm it fails**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_interviews.py -k provider_status -v`

Expected: FAIL because the route/helper does not exist.

- [ ] **Step 3: Implement normalized provider status**

Add a small helper with this priority: `error > loading > busy > queued > idle > offline`. Derive the Comni HTTP URL from the configured realtime URL and call `/status` with a five-second timeout. Keep TLS verification behavior consistent with the existing local MiniCPM adapter.

Return only:

```python
{
    "provider": provider,
    "state": state,
    "detail": detail,
    "queue_length": queue_length,
}
```

- [ ] **Step 4: Add the frontend API type and loader**

Add to `apps/web/src/api/client.ts`:

```ts
export type ProviderStatus = {
  provider: "bailian" | "minicpm";
  state: "offline" | "loading" | "queued" | "idle" | "busy" | "error";
  detail: string;
  queue_length: number;
};

export async function getProviderStatus(provider: ProviderStatus["provider"]): Promise<ProviderStatus> {
  const response = await fetch(`${API_BASE}/api/interviews/providers/${provider}/status`);
  if (!response.ok) throw new Error(`Failed to load provider status: ${response.status}`);
  return response.json();
}
```

- [ ] **Step 5: Run focused tests and commit**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_interviews.py -k provider_status -v`

Expected: PASS.

Commit: `feat: expose realtime provider readiness`

---

### Task 2: Authoritative ASR And Stable Turn Identity

**Files:**
- Modify: `services/api/app/integrations/bailian/omni_realtime.py`
- Modify: `services/api/app/integrations/minicpm/realtime.py`
- Modify: `services/api/app/interview_ledger.py`
- Modify: `services/api/tests/test_bailian_adapter.py`
- Modify: `services/api/tests/test_minicpm_realtime.py`
- Create: `services/api/tests/test_interview_ledger.py`

**Interfaces:**
- Produces normalized event fields: `turn_id`, `item_id`, `response_id`, `is_final`, `source`.
- Produces Ledger transcript rows: `{ speaker, text, turn_id, source }`.
- Consumes upstream Bailian event IDs when present; otherwise generates adapter-local monotonic IDs.

- [ ] **Step 1: Write failing adapter tests for event identity**

Add a Bailian mapping test using an upstream completed transcription:

```python
event = adapter.map_server_event({
    "type": "conversation.item.input_audio_transcription.completed",
    "item_id": "item_7",
    "transcript": "我负责轨迹控制。",
})[0]
assert event == {
    "type": "transcript.item",
    "speaker": "candidate",
    "text": "我负责轨迹控制。",
    "turn_id": "item_7",
    "item_id": "item_7",
    "is_final": True,
    "source": "provider_asr",
}
```

Add equivalent assertions for assistant `response.audio_transcript.delta` and MiniCPM generated `local-assistant-N` IDs.

- [ ] **Step 2: Write a failing Ledger authority test**

```python
def test_ledger_ignores_non_authoritative_browser_asr_for_bailian():
    ledger = InterviewLedger("iv_test", "demo", "demo", "jd", authoritative_asr="provider_asr")
    ledger.record("client", {"type": "transcript.item", "speaker": "candidate", "text": "混入内容", "turn_id": "b1", "source": "browser_asr"})
    ledger.record("provider", {"type": "transcript.item", "speaker": "candidate", "text": "真实回答", "turn_id": "p1", "source": "provider_asr"})
    assert ledger.payload()["transcript"] == [{"speaker": "candidate", "text": "真实回答", "turn_id": "p1", "source": "provider_asr"}]
```

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_bailian_adapter.py services/api/tests/test_minicpm_realtime.py services/api/tests/test_interview_ledger.py -v`

Expected: FAIL on missing identity and authority fields.

- [ ] **Step 4: Implement adapter IDs and Ledger source filtering**

Preserve upstream IDs where available. Add monotonic candidate/assistant counters only for events whose provider has no ID. Pass `authoritative_asr="provider_asr"` for Bailian and `"browser_asr"` for MiniCPM when constructing the Ledger.

Do not send `transcript.item` to either model; it remains a durable/UI event.

- [ ] **Step 5: Run focused tests and commit**

Expected: all focused tests PASS.

Commit: `fix: preserve authoritative realtime turns`

---

### Task 3: Aggregate Audio Telemetry Instead Of Persisting Packet Events

**Files:**
- Modify: `services/api/app/interview_ledger.py`
- Modify: `services/api/tests/test_interview_ledger.py`
- Modify: `services/api/tests/test_interviews.py`

**Interfaces:**
- Produces payload field `audio_metrics` with `input_chunks`, `input_bytes`, `output_chunks`, `output_bytes`.
- Removes per-packet `audio.chunk` and `assistant.audio.chunk` rows from durable `events`.

- [ ] **Step 1: Write a failing compact-ledger test**

Record 150,000 input audio events and 2,000 output events, then assert:

```python
payload = ledger.payload()
assert payload["audio_metrics"] == {
    "input_chunks": 150000,
    "input_bytes": 4800000,
    "output_chunks": 2000,
    "output_bytes": 640000,
}
assert not [row for row in payload["events"] if row["event"]["type"] in {"audio.chunk", "assistant.audio.chunk"}]
assert len(json.dumps(payload, ensure_ascii=False)) < 1_000_000
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_interview_ledger.py -k audio -v`

Expected: FAIL because packet events are still appended.

- [ ] **Step 3: Implement four integer counters in `InterviewLedger.record`**

For audio packet events, update counters and return before appending to `events`. Keep `audio.start`, `audio.stop`, response boundaries, errors, and transcript events.

- [ ] **Step 4: Update the existing persistence test**

Replace its assertion about sanitized packet rows with assertions against `audio_metrics`.

- [ ] **Step 5: Run tests and commit**

Commit: `perf: compact realtime interview ledgers`

---

### Task 4: Durable Finish And Explicit Cancel Protocol

**Files:**
- Modify: `services/api/app/realtime_gateway.py`
- Modify: `services/api/app/routers/interviews.py`
- Modify: `services/api/tests/test_interviews.py`

**Interfaces:**
- Consumes client `session.end` and `session.cancel`.
- Produces `session.persisted` only after `JsonStorage.write_interview` succeeds.
- Persists `completed/client_session_end` or `cancelled/client_session_cancel`.

- [ ] **Step 1: Write failing WebSocket lifecycle tests**

For finish, assert the final event and stored status:

```python
websocket.send_json({"type": "session.end"})
assert websocket.receive_json() == {"type": "session.ended", "mode": "mock"}
persisted = websocket.receive_json()
assert persisted == {"type": "session.persisted", "session_id": ready["session_id"], "status": "completed"}
assert JsonStorage(tmp_path).read_interview(ready["session_id"])["status"] == "completed"
```

Add a cancel test that receives `session.persisted` with `cancelled` and never creates a report.

- [ ] **Step 2: Run the lifecycle tests and confirm failure**

Expected: FAIL because the router closes before durable acknowledgement and does not dispatch cancel.

- [ ] **Step 3: Add `session.cancel` dispatch and centralize finalization**

Implement one router-local `persist(status, reason)` closure guarded by a boolean so `finally` cannot write twice. `RealtimeGateway` dispatches `session.cancel` to `handle_session_cancel` when available and otherwise reuses `handle_session_end`. On end/cancel: dispatch provider stop, persist the Ledger, send `session.persisted`, then close the browser socket. On browser disconnect: persist `disconnected/browser_disconnect` in `finally`.

- [ ] **Step 4: Run lifecycle tests and commit**

Commit: `fix: acknowledge durable interview completion`

---

### Task 5: Frontend Session State And Provider-Specific Browser ASR

**Files:**
- Modify: `apps/web/src/realtime/useInterviewSession.ts`
- Modify: `apps/web/src/realtime/useInterviewSession.test.ts`
- Modify: `apps/web/src/pages/InterviewPage.tsx`
- Modify: `apps/web/src/App.tsx`

**Interfaces:**
- Produces state: `idle | connecting | ready | ending | persisted | error`.
- Produces methods: `finish(): void`, `cancel(): void`.
- Produces callback: `onPersisted(interviewId, status)`.

- [ ] **Step 1: Extract and test provider ASR policy**

Add a pure helper:

```ts
export function shouldUseBrowserAsr(provider: InterviewSessionSelection["provider"]): boolean {
  return provider === "minicpm";
}
```

Assert Bailian is false and MiniCPM is true.

- [ ] **Step 2: Write failing state reducer tests**

Add a pure `reduceSessionState` and assert `ready -> ending -> persisted`, plus `connecting -> error` and `ready -> idle` on cancel persistence.

- [ ] **Step 3: Run frontend tests and confirm failure**

Run: `npm test -- --run src/realtime/useInterviewSession.test.ts`

Expected: FAIL because helpers/state do not exist.

- [ ] **Step 4: Implement stateful finish/cancel without immediate socket close**

Store the active selection in a ref. Start browser recognition only when `shouldUseBrowserAsr(provider)` is true. `finish()` sends `session.end`, stops capture, and sets `ending`; `cancel()` sends `session.cancel`. The `session.persisted` message closes the socket and invokes the page callback.

- [ ] **Step 5: Split InterviewPage commands**

Replace the current single button with `退出面试` and `结束并生成报告`. Disable both while ending. Confirm cancel with `window.confirm("退出后不会生成报告，确定退出吗？")`.

- [ ] **Step 6: Run tests/build and commit**

Run: `npm test -- --run`

Run: `npm run build`

Commit: `fix: wait for persisted interview sessions`

---

### Task 6: Turn-Based Message Projection And Auto-Follow

**Files:**
- Modify: `apps/web/src/realtime/useInterviewSession.ts`
- Modify: `apps/web/src/realtime/useInterviewSession.test.ts`
- Modify: `apps/web/src/pages/InterviewPage.tsx`
- Modify: `apps/web/src/styles.css`

**Interfaces:**
- Produces `ChatMessage = { id, role, text, isFinal }`.
- Produces pure helper `isNearBottom(scrollTop, clientHeight, scrollHeight): boolean`.

- [ ] **Step 1: Replace adjacency tests with turn-ID regression tests**

Assert interleaved events remain separate:

```ts
expect(deriveMessages([
  { type: "assistant.text.delta", turn_id: "a1", text: "第一个问题" },
  { type: "transcript.partial", speaker: "candidate", turn_id: "u1", text: "回答中" },
  { type: "assistant.text.delta", turn_id: "a1", text: "。" },
  { type: "transcript.item", speaker: "candidate", turn_id: "u1", text: "完整回答", is_final: true },
])).toEqual([
  { id: "a1", role: "assistant", text: "第一个问题。", isFinal: false },
  { id: "u1", role: "user", text: "完整回答", isFinal: true },
]);
```

- [ ] **Step 2: Add `isNearBottom` tests**

Assert `isNearBottom(900, 500, 1450)` is true and `isNearBottom(300, 500, 1450)` is false.

- [ ] **Step 3: Run tests and confirm failure**

Expected: FAIL on missing identity-based projection.

- [ ] **Step 4: Implement identity projection**

Maintain first-seen message order in an array and update text by ID. Use the current boundary inference only as a fallback for legacy events without IDs.

- [ ] **Step 5: Implement auto-follow without a DOM testing dependency**

Use a scroll container ref, an end-anchor ref, and a boolean ref updated by `onScroll`. Call `scrollIntoView({ block: "end" })` after message changes only while near bottom. Show an icon button with `aria-label="回到最新消息"` when auto-follow is paused.

- [ ] **Step 6: Run tests/build and commit**

Commit: `fix: project and follow stable interview turns`

---

### Task 7: Optional Playback Upload Gate

**Files:**
- Modify: `apps/web/src/realtime/audioPlayback.ts`
- Modify: `apps/web/src/realtime/audioPlayback.test.ts`
- Modify: `apps/web/src/realtime/useInterviewSession.ts`
- Modify: `apps/web/src/pages/SetupPage.tsx`

**Interfaces:**
- Adds selection field `audioMode: "full_duplex" | "playback_gate"` with default `full_duplex`.
- `createPcmAudioPlayer` accepts `onPlaybackStateChange(active: boolean)`.

- [ ] **Step 1: Add a failing playback-state unit test**

Use the existing fake AudioContext pattern and assert one `true` callback at scheduled playback start and one `false` callback after the final source ends.

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `npm test -- --run src/realtime/audioPlayback.test.ts`

- [ ] **Step 3: Implement queued-source accounting**

Increment an active source counter before `source.start`, decrement it in `source.onended`, and emit false only when the counter reaches zero. In playback-gate mode, drop outgoing microphone chunks while playback is active; do not stop the MediaStream.

- [ ] **Step 4: Add the non-default setup toggle**

Use a checkbox labeled `模型说话时暂停上传麦克风` and keep the choice in the active frontend selection. Phase 2 transmits and persists `audio_mode` together with duration and topic; Phase 1 does not add a partial backend control contract.

- [ ] **Step 5: Run tests/build and commit**

Commit: `feat: add optional realtime playback gate`

---

### Task 8: Phase 1 Verification And Documentation

**Files:**
- Modify: `docs/issues.md`
- Modify: `knowledge-graph/04-概念卡/实时语音链路.md`

**Interfaces:** None.

- [x] **Step 1: Run full automated verification**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests -v`

Run: `npm test -- --run`

Run: `npm run build`

Expected: all pass.

- [x] **Step 2: Run local browser/provider smoke**

Verify Bailian records only provider ASR, messages auto-follow, cancel creates no report, finish waits for persistence, and a 20-minute synthetic packet loop creates a Ledger under 1 MB. Verify MiniCPM loading disables connect and idle re-enables it without opening a stale WebSocket.

- [x] **Step 3: Append resolutions and reusable lessons**

Record root cause, implementation, commands, and observed outcomes in `docs/issues.md`. Update the realtime knowledge card with authoritative ASR, turn identity, and durable completion semantics.

- [ ] **Step 4: Commit**

Commit: `docs: record realtime reliability verification`
