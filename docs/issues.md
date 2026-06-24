# Issue Log

This file records user-discovered and Codex-discovered issues that may become material for the final competition report. Keep entries concise, but always converge them with diagnosis, solution, verification, and remaining risk.

## 2026-06-24 - Mock Interviewer Sounded Like A General AI Assistant

- Discovered by: User
- Severity: Medium
- Initial state: The mock interviewer replied with helper-style wording such as "我会结合你的项目继续追问。请具体说明..." This sounded like a general AI assistant instead of a real technical interviewer.
- Impact: The core demo experience weakened the "virtual interviewer" positioning and made the product feel less credible for an AI Agent interview scenario.
- Diagnosis: Interviewer identity and response constraints were not centralized. The mock response was a fixed assistant-style sentence, and the future Bailian adapter did not yet share a system-level interviewer persona.
- Decision: Add a central interviewer persona module and make both mock mode and the Bailian adapter depend on it.
- Solution: Added `services/api/app/interviewer_persona.py` with system prompt guardrails, assistant-style phrase blacklist, and short stage-based interviewer questions. Updated `MockRealtimeSession` to use persona-generated questions and exposed the shared system prompt on `BailianRealtimeAdapter`.
- Verification: Backend `pytest -q` passed with 35 tests. Frontend `npm run build` succeeded. Added tests preventing assistant-style phrases from reappearing in mock interviewer replies.
- Remaining risk: Mock questions are still deterministic templates. Real adaptive behavior depends on wiring Qwen-Omni-Realtime with this system prompt and later evaluating live responses.

## 2026-06-24 - Bailian API Key Configuration File Was Missing

- Discovered by: User
- Severity: Low
- Initial state: The backend supported `DASHSCOPE_API_KEY` through `.env`, but `services/api/.env` did not exist locally, so it was unclear where to paste the Bailian API key.
- Impact: API setup was easy to misunderstand, especially during live demo preparation.
- Diagnosis: Configuration loading existed in `services/api/app/config.py`, and `.env` was safely ignored by Git, but the local file and example template had not been created.
- Decision: Create a local ignored `.env` for the user to fill and a safe `.env.example` template for future setup reference.
- Solution: Added local `services/api/.env` with an empty `DASHSCOPE_API_KEY=` slot and live-mode Bailian defaults. Added `services/api/.env.example` without secrets.
- Verification: Confirmed `services/api/.env` is ignored by Git and therefore will not be pushed. The user only needs to paste the API key after `DASHSCOPE_API_KEY=` and restart the backend.
- Remaining risk: Real Bailian realtime protocol mapping is still pending, so live mode may return the adapter readiness/implementation message until that integration is completed.

## 2026-06-24 - Backend Restart Was Unclear After Editing `.env`

- Discovered by: User
- Severity: Low
- Initial state: After editing the Bailian API configuration, the backend restart appeared to fail and it was unclear whether port `8000` was using the old process or a fresh process.
- Impact: The user could not confidently verify whether `.env` changes had taken effect.
- Diagnosis: Port `8000` was already occupied by a Python backend process. Restart needs to stop the process owning the listening port before launching Uvicorn again.
- Decision: Treat backend restart as an explicit operational step: inspect port `8000`, stop the owning process, start Uvicorn from `services/api`, and verify `/api/health`.
- Solution: Restarted the backend on `127.0.0.1:8000`; health check returned `{"status":"ok"}`. Confirmed frontend port `5173` remained active.
- Verification: `Get-NetTCPConnection` showed Python listening on `8000` and Node/Vite listening on `5173`.
- Remaining risk: If `REALTIME_MODE=bailian` is enabled, WebSocket interview startup may still return the adapter implementation message until the real Bailian realtime protocol is wired.

## 2026-06-24 - Bailian Realtime Adapter Still Returned Protocol Mapping Placeholder

- Discovered by: User
- Severity: High
- Initial state: With `REALTIME_MODE=bailian` and a configured `DASHSCOPE_API_KEY`, the browser received `realtime.error: Bailian live audio protocol mapping is not wired yet`.
- Impact: The app proved configuration was reaching the backend, but live mode could not establish a usable Qwen-Omni-Realtime session.
- Diagnosis: `BailianRealtimeAdapter.connect()` still raised `NotImplementedError`. Official Alibaba Cloud documentation requires a WebSocket URL with `?model=...`, `Authorization: Bearer DASHSCOPE_API_KEY`, a `session.update` event, `input_audio_buffer.append` for audio, and server event mapping for `response.audio_transcript.delta` / `response.audio.delta`.
- Decision: Replace the placeholder with a minimal real WebSocket protocol adapter, while explicitly blocking unsupported browser audio formats.
- Solution: Implemented WebSocket connection, `session.update`, `input_audio_buffer.append`, `session.finish`, server event mapping, and a backend relay task. Added `websockets` as an explicit backend dependency.
- Verification: Backend `pytest -q` passed with 37 tests. Adapter tests verify URL construction, Bearer auth, session update payload, audio append, session finish, and server event mapping.
- Remaining risk: Alibaba requires 16 kHz PCM input, but the frontend currently captures `audio/webm;codecs=opus` through `MediaRecorder`. Live connection should no longer fail with the mapping placeholder, but microphone audio still needs an AudioWorklet PCM16 capture path before full realtime speech works.

## 2026-06-24 - Local `.env` Leaked Bailian Mode Into Tests

- Discovered by: Codex
- Severity: Medium
- Initial state: After setting `REALTIME_MODE=bailian` in local `.env`, a mock WebSocket test unexpectedly entered the Bailian path.
- Impact: Tests became environment-dependent and could accidentally call external services or fail differently on another machine.
- Diagnosis: `Settings` loads `services/api/.env`, and the test suite did not isolate realtime mode from local developer configuration.
- Decision: Force tests to run in deterministic mock mode unless a test explicitly constructs a Bailian adapter.
- Solution: Added an autouse pytest fixture that sets `REALTIME_MODE=mock` and clears the settings cache before and after each test.
- Verification: Full backend suite now passes with `37 passed`.
- Remaining risk: Future integration tests that intentionally hit Bailian should opt in explicitly and be marked separately so they never run in normal offline test suites.
