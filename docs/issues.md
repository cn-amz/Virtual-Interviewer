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
- Remaining risk: The later PCM16 AudioWorklet task addresses the original browser audio format mismatch. Live microphone behavior still needs manual verification on the demo machine with the real browser permission flow.

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

## 2026-06-24 - Text Input Failed In Bailian Mode

- Discovered by: User
- Severity: High
- Initial state: After switching to `REALTIME_MODE=bailian`, typing an answer produced `realtime.error: Session does not support handle_text`.
- Impact: Text-based interview practice became unavailable even though text mode is important for lower cost training and for users who cannot use a microphone.
- Diagnosis: `RealtimeGateway` dispatches `text.input` by calling `handle_text`, but `BailianRealtimeAdapter` only implemented audio realtime methods. Official realtime audio input should not be used for typed text because it is a different interaction mode and may add unnecessary cost.
- Decision: Preserve typed answers as a local low-cost interviewer path inside the Bailian session, while keeping microphone input on Qwen-Omni-Realtime.
- Solution: Added `BailianRealtimeAdapter.handle_text()` returning candidate transcript, `text.mode=local-low-cost`, and persona-based `assistant.text.delta` without sending extra events to the Bailian WebSocket.
- Verification: Added adapter tests proving typed text returns local interviewer events and does not call the realtime WebSocket. Backend `pytest -q` now passes with 39 tests.
- Remaining risk: The low-cost text path currently uses deterministic local persona questions. A later enhancement can route typed mode to a cheaper non-realtime Bailian text model if model-generated text interviews are needed.

## 2026-06-24 - Browser Microphone Captured WebM Instead Of 16 kHz PCM

- Discovered by: Codex
- Severity: High
- Initial state: The frontend microphone used `MediaRecorder` and sent `audio/webm;codecs=opus` at browser-native sample rates, while Alibaba Qwen-Omni-Realtime requires 16 kHz PCM input.
- Impact: Even after the Bailian WebSocket connected, microphone audio could not be accepted by the realtime model.
- Diagnosis: `MediaRecorder` is convenient for compressed browser audio, but the Bailian realtime API expects raw PCM frames. The capture layer had to change instead of adapting only the backend.
- Decision: Replace MediaRecorder capture with AudioWorklet-based PCM16 capture and keep the existing WebSocket event shape.
- Solution: Rewrote `apps/web/src/realtime/audioCapture.ts` to use `AudioContext` + `AudioWorklet`, added `apps/web/public/pcm16-capture-processor.js`, and changed audio chunks to `audio/pcm` with `sample_rate=16000`.
- Verification: Frontend `npm run build` succeeded. Backend accepts `audio/pcm` at `16000` in adapter tests.
- Remaining risk: Browser support and microphone permission behavior still need live manual testing on the demo machine; some browsers may ignore the requested `AudioContext` sample rate, so the worklet includes downsampling to 16 kHz.

## 2026-06-24 - Alibaba Console Showed Failed Realtime Model Calls

- Discovered by: User
- Severity: High
- Initial state: The Alibaba Cloud console showed failed model calls even though the local app could connect to the realtime WebSocket.
- Impact: Live demo credibility was affected because backend configuration looked correct locally but the provider-side invocation still failed.
- Diagnosis: Direct WebSocket reproduction showed `session.created` and `session.updated` succeeded, then the service returned `invalid_request_error` for event type `session.finish`. The adapter had invented `session.finish`, but Alibaba's client event reference does not define that event. Valid lifecycle events include `input_audio_buffer.append`, optional `input_audio_buffer.commit` in Manual mode, `response.create`, and WebSocket close.
- Decision: Remove the invalid `session.finish` event. In VAD mode, stopping the local microphone should only mark local audio as stopped; the WebSocket should be closed by normal session end.
- Solution: Changed `BailianRealtimeAdapter.send_audio_stop()` to return a local `audio.stopped` event without sending anything to Alibaba. `session.end` now closes the WebSocket through `close()`.
- Verification: Adapter tests now assert `send_audio_stop()` sends no extra realtime event. Full backend suite passes with 43 tests.
- Remaining risk: Real spoken audio still needs manual browser testing with microphone permission and a human utterance to confirm the full VAD response loop.

## 2026-06-24 - Local Text Interviewer Asked Static Questions

- Discovered by: User
- Severity: High
- Initial state: The local text fallback asked fixed questions, did not start with self-introduction, and did not use resume/JD context.
- Impact: Text interview mode felt scripted instead of like a role-specific interviewer, weakening the lower-cost training path.
- Diagnosis: `BailianRealtimeAdapter.handle_text()` always called `next_mock_interviewer_question("project_deep_dive", text)`, so it had no local interview state, no initial self-introduction question, and no resume-aware project selection.
- Decision: Add a small local text interviewer state machine for typed mode. It should ask for self-introduction first, prefer robotics/ROS/机械臂-related resume projects, then vary follow-up questions by answer content.
- Solution: Added `InterviewContext` and `LocalTextInterviewer`, wired `BailianRealtimeAdapter.start_events()` and `handle_text()` through it, and loaded profile/JD context in `create_realtime_session()`.
- Verification: Tests now cover self-introduction start, robotics project preference, adaptive follow-up changes, and typed mode preserving `local-low-cost`. Full backend suite passes with 43 tests.
- Remaining risk: This remains a deterministic local interviewer. For richer generated text interviews, the next improvement should connect typed mode to a cheaper non-realtime Bailian text model plus RAG.

## 2026-06-30 - Typed Text Was Not Sent To Bailian Text Model

- Discovered by: User
- Severity: High
- Initial state: The user expected text typed in the interview page to reach an Alibaba model, but Alibaba Console did not show successful model calls.
- Impact: It was hard to verify cloud model integration without using microphone realtime audio, and the text interview still felt too local/static for practical testing.
- Diagnosis: `BailianRealtimeAdapter.handle_text()` intentionally used the local low-cost interviewer path and did not call Qwen-Omni-Realtime. This was correct for cost control, but no separate cloud text path existed.
- Decision: Keep realtime audio on Qwen-Omni-Realtime, and add a separate text path through Alibaba DashScope OpenAI-compatible `chat/completions` using `TEXT_MODE=bailian_text` and `BAILIAN_TEXT_MODEL=qwen3.6-plus`.
- Solution: Added `BailianTextClient`, wired typed answers in Bailian mode to the text client when `TEXT_MODE=bailian_text`, preserved local fallback on cloud errors, added config entries, and fixed mojibake Chinese strings in the interviewer persona, route defaults, mock report, and frontend microphone errors.
- Verification: Added mocked HTTP tests proving text mode posts to `/chat/completions`, uses `qwen3.6-plus`, records history, falls back locally on cloud errors, and keeps text mode usable even if realtime audio connection fails. Backend `pytest -q` passed with 52 tests. Frontend `npm run build` passed. A live local WebSocket probe returned `text.mode=bailian_text` with model `qwen3.6-plus`.
- Remaining risk: Browser-side testing should confirm the UI sees the same `text.mode=bailian_text` event that the direct local WebSocket probe already produced.

## 2026-06-30 - Bailian Text Model Name Missed Hyphen

- Discovered by: User
- Severity: High
- Initial state: The user typed text in the browser, but Alibaba Console did not show a successful text model call.
- Impact: Text mode appeared to still be local-only, even after the Bailian text client was added.
- Diagnosis: A direct local WebSocket probe showed the backend entered the text cloud path, but DashScope returned `404 Not Found` for the text call. The configured model name was `qwen3.6plus`, while the available model identifier is `qwen3.6-plus`.
- Decision: Treat provider model names as exact configuration values and keep them in `.env.example`, docs, defaults, and tests.
- Solution: Updated defaults, local `.env`, docs, and tests to use `BAILIAN_TEXT_MODEL=qwen3.6-plus`.
- Verification: After backend restart, a direct local WebSocket probe returned a model-generated interviewer follow-up and `{"type":"text.mode","mode":"bailian_text","model":"qwen3.6-plus"}`. Backend `pytest -q` passed with 52 tests. Frontend `npm run build` passed.
- Remaining risk: The user should refresh the browser and run one UI text test to confirm the frontend path shows the same `bailian_text` mode.

## 2026-07-01 - Frontend Token Restore Stayed On Login Screen

- Discovered by: Codex
- Severity: Medium
- Initial state: Claude Code implemented the first frontend login slice with `localStorage` token restoration. `/api/auth/me` could return a valid user, but `App` only set `user` and did not move the screen to `dashboard`.
- Impact: Returning users with a valid token could still see the login screen instead of the post-login dashboard.
- Diagnosis: The app state uses a local `screen` enum instead of a router. Restoring `user` was not sufficient; the screen state also had to be set explicitly.
- Decision: Keep the current no-router approach for this phase and make token restore set both `user` and `screen`.
- Solution: Rewrote `apps/web/src/App.tsx` so a valid token calls `setUser(currentUser)` and `setScreen("dashboard")`; invalid tokens clear the user and keep the login view.
- Verification: Frontend `npm run build` passed.
- Remaining risk: A future router migration should replace manual screen state with route guards.

## 2026-07-01 - Frontend Phase-Two Pages Still Contained Mojibake

- Discovered by: Codex
- Severity: Medium
- Initial state: Several touched frontend pages still contained corrupted Chinese strings after Claude Code's first-pass implementation.
- Impact: The login, dashboard, setup, interview, ability-tree, and report pages were usable technically but not acceptable for a competition-facing demo.
- Diagnosis: Existing files had historical encoding corruption, and new edits preserved or copied those strings.
- Decision: Rewrite the touched UI files with clean UTF-8 Chinese rather than trying to patch corrupted byte sequences line-by-line.
- Solution: Rebuilt `LoginPage`, `DashboardPage`, `AbilityTreePage`, `SetupPage`, `InterviewPage`, `ReportPage`, `App`, and the relevant client error string with clean text.
- Verification: `rg` scan over touched frontend/auth files found no mojibake patterns. Frontend `npm run build` passed.
- Remaining risk: Older docs and non-touched backend files may still contain historical mojibake and should be cleaned opportunistically when they are next edited.

## 2026-07-01 - Text Answer Had No Waiting Feedback

- Discovered by: User
- Severity: Medium
- Initial state: When the user submitted a typed answer, the UI showed no immediate feedback while the Bailian text model was thinking.
- Impact: Users could not tell whether the app was stuck, the network was slow, or the model was generating a response.
- Diagnosis: `sendText()` sent the WebSocket event but did not add any local pending state or event to the visible event stream. Cloud text generation can take noticeable time, so silence looked like a freeze.
- Decision: Use the smallest visible feedback mechanism already supported by the page: append a local `client.pending` event immediately after a text answer is successfully sent.
- Solution: Updated `useInterviewSession.sendText()` to return send status from `sendJson()` and append `{"type":"client.pending","message":"已发送文字回答，等待模型回复..."}` on success. Also cleaned remaining microphone error mojibake in the same hook.
- Verification: Frontend `npm run build` passed. Backend `pytest -q` still passed with 61 tests.
- Remaining risk: This is event-stream feedback only. A later UI pass can add button-level loading state, timeout warnings, and latency metrics.

## 2026-07-01 - Microphone Permission Denied In In-App Browser

- Discovered by: User
- Severity: Medium
- Initial state: After connecting the interview WebSocket, clicking "开始麦克风" showed `micStatus: error` with the raw DOMException message `Permission denied` instead of clear Chinese guidance.
- Impact: Users in in-app browsers (WeChat, DingTalk, etc.) or browsers with blocked permissions could not understand why the microphone failed or how to fix it.
- Root cause: `audioCapture.ts` passed raw `DOMException.message` through to the error state without detecting `NotAllowedError` or providing actionable Chinese guidance. `useInterviewSession.ts` did not emit visible `audio.error` events for WebSocket-not-ready or capture-start failures.
- Solution: Normalize `NotAllowedError` DOMException into Chinese guidance text. Handle missing `navigator.mediaDevices.getUserMedia` with a clear Chinese message. Emit `audio.error` events when mic is started before WebSocket is open and when capture.start() fails. Add a visible connection hint near mic controls in `InterviewPage.tsx`.
- Verification: Frontend `npm run build` passed. In the in-app browser, the disconnected interview page now shows `请先连接面试官，再开启麦克风。`; after connecting and clicking `开始麦克风`, the cached permission denial now displays the Chinese guidance message and appends an `audio.error` event.
- Remaining risk: A successful real microphone capture still needs manual testing after the user grants browser/system microphone permission.

## 2026-07-03 - Realtime Audio Produced Transcripts But No Omni Reply

- Discovered by: User
- Severity: High
- Initial state: The browser event stream showed repeated `transcript.partial` entries such as `喂！我靠！`, followed by local `audio.stopped`, but no `assistant.text.delta`, `assistant.audio.chunk`, `response.created`, or `response.done` from Qwen-Omni-Realtime.
- Impact: The microphone path looked alive because speech transcription worked, but the interview did not behave as a full-duplex interviewer and did not answer spoken input.
- Diagnosis: The frontend currently captures microphone audio as 16 kHz PCM through `AudioWorklet` and streams chunks to the backend, and the backend forwards them to Bailian through `input_audio_buffer.append`. The screenshot proves this path reaches Bailian because `conversation.item.input_audio_transcription.delta` is mapped to `transcript.partial`. The missing piece is turn completion and response creation: the UI behaves like a start/stop push-to-talk flow, while the backend session is configured for server VAD. Stopping the local microphone only emits local `audio.stopped`; it does not send `input_audio_buffer.commit` or `response.create`. If the service has not detected enough trailing silence to emit `input_audio_buffer.speech_stopped` and `input_audio_buffer.committed`, no model response is created.
- Decision: Split the next fix into an explicit product choice. For the current button-based demo, use Manual mode: set `turn_detection` to `null`, send `input_audio_buffer.commit` and then `response.create` on `audio.stop`. For a true full-duplex demo, keep server VAD, include `create_response`/`interrupt_response` in turn detection, keep the microphone open continuously, and implement assistant audio playback plus interruption handling.
- Proposed solution: Implement the Manual mode path first because it matches the existing `开始麦克风`/`停止麦克风` UI and gives predictable spoken-answer replies. Track full-duplex continuous VAD as a later architecture slice.
- Verification: Pending. Need add adapter tests for `audio.stop` sending commit/create in Manual mode, then run a live browser speech test and confirm `response.created`, `response.audio_transcript.delta` or `response.audio.delta`, and `response.done` appear after stopping the microphone.
- References: Alibaba Realtime docs state that VAD mode auto-commits and auto-responds after speech stop, while Manual mode requires `input_audio_buffer.commit` and `response.create`.
