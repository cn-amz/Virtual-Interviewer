# Live Audio Qwen-Omni Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add browser microphone capture and a backend gateway shape that can route audio chunks to Qwen-Omni-Realtime live mode while preserving mock mode for local development.

**Architecture:** The browser captures microphone audio with `MediaRecorder` and sends `audio.start`, `audio.chunk`, and `audio.stop` events through the existing backend WebSocket. The backend introduces a mode-switching realtime gateway and a Bailian session adapter that validates configuration and owns the future Qwen-Omni-Realtime protocol mapping.

**Tech Stack:** React, TypeScript, MediaRecorder, FastAPI WebSocket, Python async classes, pytest, Vitest optional.

---

## Scope

This is Phase 2 after the current mock MVP. It prepares and partially implements live audio mode without falling back to Whisper/SenseVoice STT.

Included:

- Browser microphone permission and recording controls.
- Base64 audio chunk streaming over the existing `/api/interviews/realtime` WebSocket.
- Backend event models for audio events.
- Session backend abstraction: mock vs Bailian.
- Bailian adapter interface for sending audio chunks and receiving assistant text/audio events.
- Live-mode readiness errors when `DASHSCOPE_API_KEY` or realtime URL/model is missing.

Excluded:

- Full production WebRTC path.
- Local STT pipeline.
- Final frontend visual polish.
- Domain deployment and HTTPS automation.

## Files

```text
apps/web/src/realtime/audioCapture.ts
apps/web/src/realtime/useInterviewSession.ts
apps/web/src/pages/InterviewPage.tsx
apps/web/src/styles.css
services/api/app/realtime.py
services/api/app/realtime_gateway.py
services/api/app/integrations/bailian/omni_realtime.py
services/api/app/routers/interviews.py
services/api/tests/test_realtime_gateway.py
services/api/tests/test_bailian_adapter.py
docs/progress.md
```

## Task A: Browser Microphone Capture

**Files:**
- Create: `apps/web/src/realtime/audioCapture.ts`
- Modify: `apps/web/src/realtime/useInterviewSession.ts`
- Modify: `apps/web/src/pages/InterviewPage.tsx`

Steps:

1. Add `createAudioRecorder` using `navigator.mediaDevices.getUserMedia({ audio: true })`.
2. Use `MediaRecorder` with preferred MIME types:
   - `audio/webm;codecs=opus`
   - fallback `audio/webm`
3. Emit:
   - `audio.start`
   - `audio.chunk`
   - `audio.stop`
4. Add interview page buttons:
   - Start microphone
   - Stop microphone
5. Show microphone state and permission errors.
6. Verify `npm run build`.

## Task B: Backend Realtime Event Models

**Files:**
- Modify: `services/api/app/realtime.py`
- Create: `services/api/app/realtime_gateway.py`
- Modify: `services/api/app/routers/interviews.py`

Steps:

1. Define normalized event handling for:
   - `text.input`
   - `audio.start`
   - `audio.chunk`
   - `audio.stop`
   - `session.end`
2. Keep `MockRealtimeSession` behavior for text input.
3. For mock audio chunks, emit a visible event:

```json
{"type": "audio.received", "bytes": 1234, "mode": "mock"}
```

4. Add a `RealtimeGateway` class that accepts a session backend and forwards events.
5. Verify with pytest WebSocket or direct gateway unit tests.

## Task C: Bailian Live Session Adapter Shape

**Files:**
- Modify: `services/api/app/integrations/bailian/omni_realtime.py`
- Modify: `services/api/tests/test_bailian_adapter.py`

Steps:

1. Extend `BailianRealtimeAdapter` with async methods:

```python
async def connect(self) -> None: ...
async def send_audio_start(self, mime_type: str, sample_rate: int | None) -> None: ...
async def send_audio_chunk(self, data_base64: str, mime_type: str) -> None: ...
async def send_audio_stop(self) -> None: ...
async def close(self) -> None: ...
```

2. In this phase, `connect()` validates readiness and raises a clear `NotImplementedError` if live protocol is not wired yet.
3. Keep tests deterministic and offline.
4. Add a skipped or explicit test documenting that live protocol requires official event mapping.

## Task D: Mode Switch And Readiness

**Files:**
- Modify: `services/api/app/config.py`
- Modify: `services/api/app/routers/interviews.py`
- Modify: `services/api/tests/test_realtime_gateway.py`

Steps:

1. Use `realtime_mode: mock|bailian`.
2. If mode is `bailian`, create Bailian adapter and fail fast with a frontend-visible event when not configured:

```json
{"type": "realtime.error", "message": "DASHSCOPE_API_KEY is required for Bailian live realtime mode."}
```

3. Keep default as `mock`.
4. Verify all backend tests pass.

## Acceptance Criteria

- The frontend can request microphone permission and stream audio chunks to the backend.
- Mock mode visibly acknowledges audio chunks.
- Text mock flow remains working.
- Backend has a clear `mock|bailian` mode boundary.
- Live Bailian mode refuses to start without `DASHSCOPE_API_KEY`.
- No Whisper/SenseVoice STT is introduced in the main realtime path.
- Docs and progress file describe that Qwen-Omni-Realtime is responsible for audio understanding.
