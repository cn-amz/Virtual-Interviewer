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

## 2026-07-03 - Partial Transcript Cards Repeated In Frontend Event Stream

- Discovered by: User
- Severity: Medium
- Initial state: During microphone input, every `transcript.partial` event was rendered as a new card, so the event stream showed many near-duplicate candidate utterances while ASR was still updating the same sentence. Several UI section eyebrow labels also remained in English, such as `Realtime Interview`, `Dashboard`, and `Ability Tree`.
- Impact: The interview page looked noisy and hard to read, especially during live speech. English labels made the competition demo feel unfinished for a Chinese audience.
- Root cause: `useInterviewSession.ts` appended every WebSocket event with `setEvents((prev) => [...prev, event])`. Streaming ASR partials are incremental updates, not separate final transcript items. `InterviewPage.tsx` also rendered raw event type strings directly.
- Solution: Add `appendRealtimeEvent()` so consecutive `transcript.partial` events update the latest partial card, and a final candidate `transcript.item` replaces the latest partial. Localize event labels and page eyebrow labels to Chinese.
- Verification: Added Vitest coverage for partial transcript replacement and final transcript replacement. Frontend `npm run test` passed with 2 tests. Frontend `npm run build` passed. `rg` found no remaining visible eyebrow strings for `Realtime Interview`, `Interview Setup`, `Post Interview Report`, `Ability Tree`, or `Virtual Interviewer`.
- Remaining risk: Future event types may still need explicit Chinese labels as more provider events are surfaced.

## 2026-07-03 - Assistant Audio Chunks Repeated And Were Not Audible

- Discovered by: User
- Severity: High
- Initial state: After Qwen-Omni-Realtime began replying, every `assistant.audio.chunk` was rendered as a separate event card, and the user could not hear the model's spoken response.
- Impact: The model was producing audio data, but the demo looked noisy and failed the core virtual interviewer expectation of audible speech.
- Root cause: The frontend treated `assistant.audio.chunk` as a display-only event. It did not aggregate streaming audio chunks and did not decode or play the base64 PCM payload. The backend also did not include the output sample rate in the mapped event, even though Bailian realtime output PCM is 24 kHz.
- Solution: Added a small Web Audio PCM16 player that decodes base64 little-endian PCM16 and schedules chunks through `AudioContext`. Resume the audio context from user actions such as connect, text send, and microphone start. Collapse consecutive `assistant.audio.chunk` events into one visible card and display `正在播放模型语音...`. Include `sample_rate: 24000` in backend `assistant.audio.chunk` events.
- Verification: Frontend `npm run test` passed with 4 tests covering PCM decode, partial transcript collapse, final transcript replacement, and assistant audio chunk collapse. Frontend `npm run build` passed. Backend `pytest tests/test_bailian_adapter.py -q` passed with 14 tests.
- Remaining risk: Browser autoplay policies can still block audio if no prior user gesture resumes `AudioContext`; the current implementation attempts to resume audio output during user-triggered connect/text/microphone actions and surfaces playback failures as `audio.error`.

## 2026-07-03 - Assistant Text Was Split And ASR Partial Accuracy Was Confusing

- Discovered by: User
- Severity: Medium
- Initial state: After realtime audio began working, the model's spoken reply could still appear as several visible text fragments, and microphone recognition looked inaccurate because interim ASR updates were shown like stable final content.
- Impact: The live interview page still felt noisy and uncertain: users could not easily distinguish temporary recognition from final transcript, and interviewer replies did not read like one coherent sentence.
- Root cause: `assistant.text.delta` events were appended as independent visible cards even when they belonged to the same streamed reply. `transcript.partial` labels did not make the temporary nature obvious. The AudioWorklet downsampler also used nearest-neighbor sampling, which is minimal but can add avoidable distortion before ASR.
- Solution: Merge assistant text deltas into the latest visible interviewer reply until a conversation boundary is reached, rename ASR labels to `实时转写（临时）` and `最终识别`, and replace nearest-neighbor downsampling with simple window averaging for speech input.
- Verification: Frontend `npm run test` passed with 5 tests covering transcript collapse, final transcript replacement, assistant audio chunk collapse, and assistant text delta merging. Frontend `npm run build` passed.
- Remaining risk: ASR quality still depends on microphone hardware, noise, speaking pace, and Bailian's realtime recognizer. A later calibration pass can add noise checks, gain/level display, and user-side confirmation before sending low-confidence speech to the interviewer.

## 2026-07-07 - Report And Ability Tree Were Still Prototype-Level

- Discovered by: Codex architecture audit with Claude Code adversarial review
- Severity: High
- Initial state: `services/api/app/scoring.py` scored answers with deterministic heuristics such as answer length, numbers, and mechanism words. `services/api/app/reporting.py` produced mostly template-like summary, target gaps, and practice suggestions.
- Impact: The final demo could look like a working interview page but lose credibility at the most important moment: the post-interview report. If scoring and ability-tree changes do not cite real transcript evidence, the project does not fully prove the Agent closed loop required by the competition.
- Diagnosis: The deterministic scoring/reporting path was intentionally useful for MVP verification, but it has outlived its role as the default final-demo path.
- Proposed solution: Keep deterministic scoring as an offline fallback only. Add a model-assisted report path that sends transcript, JD, profile context, and rubric to a Bailian text model, returns strict JSON, cites answer snippets, and feeds evidence-backed changes into the ability tree.
- Verification: Pending.
- Remaining risk: Model-scored reports need schema validation and graceful local fallback so a provider failure does not break the demo.

## 2026-07-07 - Realtime Interview Events Were Not Persisted As Evidence

- Discovered by: Codex architecture audit with Claude Code adversarial review
- Severity: High
- Initial state: The realtime WebSocket path sent transcript and assistant events to the browser, but did not persist every interview event to an evidence ledger before report generation.
- Impact: Browser refreshes, WebSocket disconnects, or manual report generation can lose the actual interview evidence. Reports and ability-tree updates then cannot be audited.
- Diagnosis: The MVP optimized for visible event streaming first. Storage currently writes mock reports, not the full live event stream.
- Proposed solution: Add append-only JSONL event storage per `interview_id`, recording candidate transcript, assistant questions, tool outputs, model errors, timing, and fallback mode. Generate reports from the stored event stream.
- Verification: Pending.
- Remaining risk: Event persistence must avoid writing raw audio or secrets; store transcript and metadata by default.

## 2026-07-07 - Realtime Relay Errors Were Not Surfaced Reliably

- Discovered by: Codex architecture audit with Claude Code adversarial review
- Severity: Medium
- Initial state: `relay_realtime_events()` loops over `session.receive_events()` and sends events to the browser. If the upstream Bailian WebSocket raises unexpectedly, the relay task can fail without sending a clear frontend event.
- Impact: The user may see a silent interview page and cannot distinguish provider disconnect, network failure, or a local UI issue.
- Diagnosis: The relay task lacks a provider-error boundary and user-visible failure event.
- Proposed solution: Catch upstream receive/send exceptions, emit a `realtime.error` event with a safe message, record the failure in the event ledger, and close or downgrade the session predictably.
- Verification: Pending.
- Remaining risk: Some disconnects can happen while the browser socket is already closed; those should still be logged server-side.

## 2026-07-07 - Text Model Client Recreated HTTP Connections Per Request

- Discovered by: Codex architecture audit with Claude Code adversarial review
- Severity: Low
- Initial state: `BailianTextClient._post()` creates a new `httpx.AsyncClient` for each request when no injected test client is provided.
- Impact: Text-mode replies may pay avoidable connection setup cost, making the user think the model is stuck.
- Diagnosis: The client was written for a small MVP and testability. It does not yet reuse an async HTTP client across a session.
- Proposed solution: Reuse an `httpx.AsyncClient` owned by the text client or application lifecycle, while preserving the injected `http_post` hook for tests.
- Verification: Pending.
- Remaining risk: Client lifecycle must be closed cleanly during app shutdown or session end.

## 2026-07-07 - Public Demo Deployment Was Still A Planning Item

- Discovered by: Codex architecture audit with Claude Code adversarial review
- Severity: High
- Initial state: Documentation reserves deployment concepts, but the project does not yet provide a stable public HTTPS URL or a tested tunnel/cloud deployment workflow.
- Impact: Competition deliverables require an online app link. Local `127.0.0.1` verification is not enough for submission or remote judging.
- Diagnosis: The architecture correctly kept deployment separate from business logic, but the implementation priority should now move from abstract provider design to one working deployment path.
- Proposed solution: Pick one path first: temporary tunnel for early external testing, or lightweight Aliyun/ECS/SAE/Function Compute deployment for final submission. Document the exact runbook and HTTPS behavior.
- Verification: Pending.
- Remaining risk: Browser microphone behavior differs between localhost and public HTTPS; the deployed site needs a real microphone smoke test.

## 2026-08-17 - MiniCPM-o Local Full-Duplex Demo Did Not Reach A Ready Session

- Discovered by: User local smoke test and Codex deployment investigation.
- Severity: High.
- Initial state: The MiniCPM-o Docker gateway accepted the browser WebSocket and served HTTPS, but Audio Duplex requests stayed queued. The demo repeatedly played its queue chime and never consumed microphone audio.
- Root cause: The initial `main` demo used a C++ runtime combination that stalled during full-duplex session prefill. The official `Comni` branch specifies a matching `llama.cpp-omni@feat/web-demo` engine, but its first Docker build is currently blocked in the CUDA image system-dependency layer on this Docker Desktop environment. This is a local deployment blocker, not an Alibaba/Bailian API regression or a browser microphone-permission failure.
- Current mitigation: Stopped the unusable demo containers so the browser no longer creates queue requests or plays the repeating chime. Prepared an isolated `<minicpm-workdir>` Docker configuration that mounts the downloaded GGUF model read-only and uses the official C++ backend pairing; project application code remains unchanged.
- Verification: Confirmed the original gateway HTTPS health endpoint and WebSocket handshake. Confirmed queue entries in gateway logs and C++ prefill without a corresponding ready session. Confirmed the Docker container proxy can reach Ubuntu, PyPI, and NVIDIA endpoints individually.
- Remaining risk: Do not route the virtual interviewer to MiniCPM-o until the `Comni` container finishes building and a real audio session creates, accepts microphone chunks, and returns audible PCM output. Keep Bailian as the production provider during this validation.

## 2026-08-17 - Docker Desktop Build Exhausted The System Drive

- Discovered by: Codex local deployment inspection.
- Severity: High.
- Initial state: Docker Desktop stored its WSL virtual disk on C:, leaving only 4.23GB free while the MiniCPM-o image build needed additional space.
- Impact: The C++ demo image could fail during dependency download or compilation and risk exhausting the system drive.
- Root cause: Docker Desktop's `docker_data.vhdx` resided under the default local-app-data path on C: and had grown to 27.72GB from existing images and build cache.
- Resolution: Stopped Docker Desktop, moved the data directory to `<docker-data-dir>`, and created a directory junction at the original Docker path. Restarted Docker Desktop and verified Docker Engine 27.5.1 responds normally.
- Verified outcome: C: free space increased from 4.23GB to 39.97GB; the data drive now carries the Docker virtual disk. No project files or GGUF model weights were moved.
- Remaining risk: Docker images and caches will continue to grow on the data drive, so capacity should be reviewed before large model builds.

## 2026-08-17 - C++ Omni Engine Was Missing CUDA Driver Stub Symbols At Build Time

- Discovered by: MiniCPM-o `Comni` Docker build.
- Severity: High.
- Initial state: `llama-server` compilation failed with unresolved CUDA Driver API symbols including `cuGetErrorString`, `cuMemCreate`, and `cuMemAddressReserve`.
- Root cause: Docker build containers do not receive the host NVIDIA driver. The CUDA Toolkit image contained `/usr/local/cuda/lib64/stubs/libcuda.so`, but the linker command did not include it.
- Resolution: Added the CUDA stub directory and `-lcuda` to the `llama-server` executable linker flags in the isolated Comni Dockerfile. The runtime container will still receive the real NVIDIA driver from the NVIDIA Container Runtime.
- Verification: Confirmed the CUDA 12.8 base image contains the required `libcuda.so` stub. Rebuild pending.

## 2026-08-17 - Alibaba Workbench Reported 400 ClientDisconnect After A Successful Conversation

- Discovered by: User's Alibaba Model Studio workbench observation after a local voice conversation that produced a model reply.
- Severity: Medium.
- Initial state: The workbench showed `首包延迟 -`, `总耗时 155.42s`, `状态码 400`, and `错误原因 ClientDisconnect`, while the browser had already received a successful interviewer response.
- Diagnosis: The current end flow sends `session.end` from the browser, closes the browser WebSocket immediately, and the FastAPI `finally` block then closes the upstream Bailian WebSocket. Alibaba documents the realtime API as a WebSocket session and exposes `response.done` as the response completion marker; a client-side close before the provider records its terminal response can therefore be reported as `ClientDisconnect`. This is consistent with a client-initiated session teardown, but the current logs do not prove whether the last response had completed before teardown.
- Proposed solution: Add an upstream lifecycle ledger containing connection time, normalized provider events, `response.done`, close code/reason, and whether the browser or provider initiated shutdown. Make the end flow wait for the active response to finish, or explicitly cancel it and label the session as intentionally interrupted. Do not classify a client-initiated close as a model inference failure in the UI or competition report.
- Verification: Official Alibaba realtime documentation confirms WebSocket session semantics and `response.done` completion events. Local backend logs confirm the browser WebSocket is accepted and later closed without an application exception. End-to-end close timing and provider close metadata are still pending.
- Remaining risk: If the user closes the tab, loses network, or ends the interview during audio generation, Alibaba may continue to report `ClientDisconnect`; this should be distinguished from an `error` event or HTTP/authentication failure.

## 2026-08-17 - Realtime Interview Was Presented As Technical Event Cards

- Discovered by: User experience review during a successful voice/text interview.
- Severity: Medium.
- Initial state: The page rendered ASR partials, assistant deltas, audio chunks, VAD events, and response lifecycle events as separate cards. Even after partial-card merging, the interface still looked like a transport monitor rather than an interview conversation.
- Root cause: The UI rendered the raw `RealtimeEvent[]` directly. Transport events and user-facing turns had no separate presentation model.
- Solution: Added `deriveMessages()` to build a chat projection from realtime events. Candidate partial/final transcripts collapse into one user message; assistant text deltas collapse into one assistant message per response; audio chunks, waiting state, VAD, response completion, and provider debug events stay out of the chat transcript. Errors remain visible in a dedicated error area. Replaced the event cards with responsive user/assistant chat bubbles.
- Verification: Frontend Vitest passed with 10 tests; `npm run build` passed. Browser smoke test showed one initial interviewer bubble, one candidate answer bubble, and one interviewer follow-up bubble. No `.event-item` cards remained in the page.
- Remaining risk: The chat projection intentionally omits low-level lifecycle details. Those events still remain in React state for future debug/evidence logging and should later be persisted server-side as part of the interview ledger.

## 2026-08-17 - Resume Optimization Database Was Mixed With Interview Runtime Data

- Discovered by: User's data-boundary review.
- Severity: High.
- Initial state: The project runtime read `data/profiles/豆瓣酱` and `data/job_descriptions/...` directly. The profile directory also contained resume optimization notes, fine-tuning datasets, model packages, backups, and other research artifacts.
- Impact: The interview agent could treat an evolving training database as the candidate's actual resume, causing stale, duplicated, or unintended information to enter interview prompts and reports. It also increased the risk of exposing private training material.
- Root cause: The first MVP used one local `data/` layout for both source research data and interview input snapshots.
- Solution: Created `data/interview_profiles/豆瓣酱` and `data/interview_job_descriptions/`. The interview profile contains only the current profile snapshot and interview context files; the fine-tuning database remains under `data/profiles/` and is no longer read by `ProfileLoader`. Both interview data directories remain Git-ignored.
- Verification: Updated `ProfileLoader` and its tests; backend test suite passed with 61 tests. `git check-ignore` confirms both source and interview private files are ignored. Documentation and privacy notes now describe the separation.
- Remaining risk: The copied interview snapshot must be deliberately refreshed when the user submits a new resume. Future UI should make snapshot version and active JD explicit before an interview starts.

## 2026-08-17 - Interview Setup Could Not Show Multiple Resume Versions

- Discovered by: User added two resume documents to the interview profile directory and noticed the setup flow had no way to inspect them.
- Severity: Medium.
- Initial state: `SetupPage` displayed only a fixed candidate/JD sentence and immediately started the interview. The backend loader only exposed the structured profile summary, not the PDF/DOCX documents in the interview folder.
- Root cause: Resume metadata and user-facing document preview were not modeled as a separate capability from the interview profile summary.
- Solution: Added a safe resume listing endpoint and inline file endpoint. The setup page now lists available PDF/DOC/DOCX files with format and size and provides a `查看简历` action. Internal files such as `profile.json`, `prompt.txt`, `qa_bank.md`, and fine-tuning artifacts are excluded from the list.
- Verification: The API returns exactly `东南大学豆瓣酱简历.pdf` and `豆瓣酱_AI应用岗简历_MiniCPM-o.docx`; backend tests pass with 62 tests and frontend tests/build pass. The frontend and backend remain available on ports 5173 and 8000.
- Remaining risk: PDF can render inline in the browser; DOCX behavior depends on the browser/OS and may download instead. Selecting which version becomes the active interview snapshot is a separate follow-up.

## 2026-08-17 - Interview Setup Could Not Show The Active Job Description

- Discovered by: User requested the same viewable-resource flow for the job description.
- Severity: Medium.
- Initial state: The setup page showed a fixed job title but did not expose the actual JD file or an API for listing/viewing prepared interview JDs.
- Root cause: JD loading existed only as an internal profile-loader operation used to build session context; it had no user-facing document resource contract.
- Solution: Added `/api/job-descriptions` for metadata and `/api/job-descriptions/{jd_id}/file` for inline Markdown viewing. The setup page now lists the prepared JD and provides `查看 JD`. Generated a dedicated mechanical-arm motion-control training JD with responsibilities, requirements, interview focus, and ability-tree gaps.
- Verification: The API returns `机械臂运控算法工程师`; the file endpoint returns HTTP 200 with `text/markdown; charset=utf-8`; backend tests pass with 63 tests and frontend tests/build pass.
- Remaining risk: The current JD is a generated training JD, not a company-specific recruitment notice. Selecting a different JD as the active interview context remains a separate follow-up.

## 2026-08-17 - Dashboard Management And History Entrances Were Disabled

- Discovered by: User noticed the workbench already had management and history cards, but both were marked as future-stage placeholders.
- Severity: Medium.
- Initial state: Dashboard cards for `历史报告` and `管理简历与岗位` were disabled. Reports could be generated, but there was no list/detail archive; prepared resumes and JDs could only be inspected from the one-session setup page.
- Root cause: The MVP implemented storage and resource endpoints before wiring them into the product navigation.
- Solution: Added a management page that lists all interview profiles and JDs, reuses view endpoints, and supports authenticated PDF/DOC/DOCX resume uploads and Markdown JD uploads. Added history list/detail endpoints backed by `data/interviews/*.json`, a history page, and report detail loading without regenerating the report.
- Verification: Demonstrated authenticated history retrieval with 65 local records; backend tests pass with 64 tests and frontend tests/build pass. Dashboard cards are now enabled.
- Remaining risk: History currently returns the authenticated local user's report view over the local report store without a complete account-to-profile ownership model. Before public multi-user deployment, persist owner IDs and filter records per account.

## 2026-08-17 - Historical Reports Did Not Preserve The Real Interview

- Discovered by: User review of the history/report flow.
- Severity: High.
- Initial state: The realtime WebSocket only forwarded normalized events to the browser. Ending an interview did not persist its transcript, and the report page used a fixed sample transcript when no stored report was available.
- Root cause: Transport events, user-facing transcript turns, and report generation had no durable session ledger or shared interview ID contract.
- Solution: Added `InterviewLedger`, which stores session metadata, client/server/provider events, complete candidate/interviewer text, end status, and close reason under `data/interviews/{interview_id}.json`. Raw base64 audio is deliberately reduced to byte metadata. The frontend carries `session_id` into the report page, which waits briefly for persistence and calls the authenticated analyze endpoint.
- Verification: Realtime persistence and analyze endpoint tests pass; backend suite passes with 68 tests. The saved report contains the original transcript rather than the canned sample.
- Remaining risk: The current ledger is one JSON document per session. A high-volume deployment should move append-only event writes and report data to a transactional store, and should attach immutable resume/JD versions.

## 2026-08-17 - Report Analysis And Ability Tree Were Deterministic Prototypes

- Discovered by: Product review against the competition requirement for an AI Agent with explainable growth.
- Severity: High.
- Initial state: Reports had fixed summaries and gaps, and the ability tree existed only as a JSON update structure. There was no readable node-level learning artifact.
- Root cause: The first MVP optimized for an end-to-end screen demo before wiring report analysis and long-term learning records to the real transcript.
- Solution: Added optional Bailian `qwen3.6-plus` structured report analysis from the saved transcript. Invalid responses, missing keys, or provider errors fall back to deterministic scoring without losing the transcript. Ability trees remain canonical JSON for the app and are also materialized into ignored `data/ability_graphs/{user_id}/` Markdown notes with Obsidian wikilinks for skills, evidence, targets, and an index page.
- Verification: Structured analyzer, fallback, Markdown-link, report persistence, and ability-tree tests pass; frontend ability-tree page loads JSON nodes and can open an authenticated Markdown export.
- Remaining risk: The MVP still needs finer-grained score dimensions and explicit `AbilityTreeChange` records with quoted evidence and score deltas before public multi-user use.

## 2026-08-17 - Upstream Realtime Relay Failures Were Not Surfaced

- Discovered by: Review of the provider relay task while adding the interview ledger.
- Severity: Medium.
- Initial state: An exception in the upstream receive loop could terminate the relay task without a clear browser event.
- Root cause: `relay_realtime_events()` had no exception boundary separate from normal client disconnect cancellation.
- Solution: Catch provider relay failures, append a safe `realtime.error` event to the ledger, and attempt to send the same diagnostic to the browser while preserving cancellation semantics.
- Verification: Backend suite passes with 68 tests.
- Remaining risk: Provider-specific close codes and response completion markers should be added to the ledger when the official realtime protocol mapping is finalized.

## 2026-08-17 - Service Startup Could Resolve Runtime Data Outside The Repository

- Discovered by: Post-restart data-directory smoke test.
- Severity: High.
- Initial state: The default `../../data` path was resolved from the process working directory. Starting Uvicorn in `services/api` therefore selected `<incorrect-data-dir>`, while the project runtime data and interview snapshots live under `<project-root>\data`.
- Root cause: A relative Pydantic default was coupled to the shell's current directory instead of the configuration module location.
- Solution: Resolve the default storage directory from the repository path derived from `config.py`; an explicit `APP_STORAGE_DIR` environment variable still overrides it for tests/deployment.
- Verification: Restart smoke now targets the project `data` directory, and the backend suite passes with 68 tests.
- Remaining risk: Public deployment should set an explicit absolute `APP_STORAGE_DIR` and validate it at startup.

## 2026-08-17 - Existing Ability Trees Had No Markdown Export

- Discovered by: Post-restart Markdown endpoint smoke test against the existing local history.
- Severity: Medium.
- Initial state: Existing JSON ability trees were readable, but the new Markdown index endpoint returned 404 because those records predated Markdown materialization.
- Root cause: The exporter ran only when a new report updated a tree.
- Solution: The Markdown endpoint now lazily materializes the ignored Obsidian-style vault from an existing JSON tree when its index is missing.
- Verification: The existing `demo` tree now serves a Markdown index after one authenticated request; backend suite remains green.
- Remaining risk: A future migration command may be useful for bulk export, but lazy generation is sufficient for the local MVP.

## 2026-08-18 - Ability Tree Markdown Was Flat And Was Reported As Garbled

- Discovered by: User review of the ability-tree Markdown and page interaction.
- Severity: High.
- Initial state: The generated index was a flat list of skill names and evidence IDs. It did not expose the original question, candidate answer, or related knowledge point. Windows tools could also guess the UTF-8 file as an ANSI document because the file had no BOM.
- Root cause: The first exporter modeled evidence as string IDs only, and the frontend rendered `skills`, `target_skills`, and `evidence` as three unrelated lists.
- Solution: Added backward-compatible `evidence_details` records with skill, interview ID, exact question, exact answer, and structured knowledge points. Legacy trees are hydrated from stored reports. The Markdown exporter now writes UTF-8 BOM files with nested Obsidian links for `skills -> evidence -> knowledge`, and the frontend renders a clickable tree with a detail panel and report jump.
- Verification: The authenticated `demo` tree now returns 18 evidence details; each includes question, answer, and knowledge points. Markdown returns HTTP 200 with `text/markdown; charset=utf-8` and UTF-8 BOM. Backend tests pass with 69 tests and frontend tests pass with 10 tests.
- Remaining risk: Obsidian wikilinks to the main `knowledge-graph/` resolve only when the project knowledge graph is opened as a compatible vault or the note is opened from the project context; the main vault remains intentionally isolated.

## 2026-08-18 - History Was Polluted By Test And Empty Records

- Discovered by: User review of the historical report page.
- Severity: Medium.
- Initial state: Local test runs created `int_` mock reports and disconnected/empty realtime ledgers. The backend history list treated every report payload as a user-facing historical record.
- Root cause: Storage had no distinction between displayable interview sessions and test/demo report artifacts, and it did not require a non-empty candidate answer.
- Solution: History now displays only `iv_` session records with a report containing at least one non-empty candidate answer. Existing test files remain on disk for debugging and are hidden from the product list.
- Verification: The current local smoke shows zero visible test reports, while the ability tree still retains 18 evidence details. Added backend coverage for mock and empty-report filtering.
- Remaining risk: A future database should store an explicit `source`/`environment` field instead of inferring test records from the ID prefix.

## 2026-08-18 - Ability Tree Needed A Direct Obsidian Entry Point

- Discovered by: User request to place the per-user tree in its own folder and open it in Obsidian.
- Severity: Medium.
- Initial state: Markdown was generated under the user folder, but the web page only opened a browser Blob URL. There was no direct desktop-app jump.
- Root cause: The API returned Markdown content but not the absolute note path or an Obsidian URI.
- Solution: The ability-tree API now returns the per-user `markdown_path` and an encoded `obsidian://open?path=...` URI. The page adds `跳转 Obsidian`; the generated folder remains private and Git-ignored.
- Verification: Authenticated API smoke returns `obsidian://open?path=<encoded-project-data-path>`, and the file exists.
- Remaining risk: Obsidian must be installed and have registered its URI protocol; URI behavior follows the official desktop integration documented by Obsidian.

## 2026-08-18 - Ability Tree Repeated Questions And Unreliable Obsidian Jump

- Discovered by: User review of the ability-tree interaction.
- Severity: High.
- Initial state: The tree had no type branch or canonical question layer. One interview question could appear repeatedly once it produced evidence for multiple skills or multiple sessions. The page used a plain custom-protocol link, which could be ignored by an in-app browser without giving the user a usable fallback.
- Root cause: The JSON model stopped at `skills -> evidence`, and semantic question grouping had not been modeled. Obsidian opening depends on desktop protocol registration and cannot be guaranteed by a normal HTTP page.
- Solution: Added `type_branches -> question_groups -> evidence_details` to the canonical tree. Local normalization merges repeated questions without a network call; an explicit `AI 整理问题` action sends only evidence metadata to Bailian `qwen3.6-plus` for semantic merging, validates that every evidence ID is preserved exactly once, and falls back to the local grouping on any error. Markdown now adds `types/` and `questions/` notes with wikilinks. The page opens the URI through a button and exposes the absolute Markdown path with a copy fallback.
- Verification: Backend suite passes with 77 tests; frontend suite passes with 10 tests; production build succeeds. Endpoint tests verify type/question layers, persistence, and the encoded Obsidian URI.
- Remaining risk: Model grouping quality depends on the text model and prompt; users should review a newly merged canonical question before treating it as an assessment fact. Obsidian still needs to be installed and registered on the desktop system.

## 2026-08-18 - Restart Smoke Check Used The Wrong Health Route

- Discovered by: Codex post-change restart verification.
- Severity: Low (verification process only).
- Initial state: The first smoke script requested `/health` and reported a false startup failure.
- Root cause: The project health router is intentionally mounted at `/api/health`; the verification command had assumed a root-level health endpoint.
- Solution: Corrected the smoke check to `/api/health` and verified the restarted backend, frontend, ability-tree endpoint, and Markdown endpoint.
- Verification: Backend returned `ok`, frontend returned HTTP 200, the tree returned two type branches, one merged question group, and 18 evidence details.
- Remaining risk: None in the local runtime; deployment checks should continue to use the API prefix.

## 2026-08-18 - Job Description Required A File Upload

- Discovered by: User request to paste a JD directly in the management page.
- Severity: Medium.
- Initial state: The management page accepted only an existing Markdown file, which made quick JD collection inconvenient.
- Root cause: The backend exposed only multipart file upload even though the storage layer already treated Markdown as the canonical JD format.
- Solution: Added an authenticated text endpoint and a paste form with an optional title. The backend sanitizes the generated filename, adds a Markdown H1 when needed, and saves UTF-8 Markdown into `data/interview_job_descriptions/`; file upload remains available.
- Verification: Backend suite passes with 81 tests; frontend suite passes with 10 tests; production build succeeds. Loader and API coverage verify successful save and empty-content rejection.
- Remaining risk: Same-title saves intentionally replace the existing Markdown file; versioning can be added later when JD history is needed.

## 2026-08-18 - Pasted JD Could Mistake A Second-Level Heading For A Title

- Discovered by: Codex regression test for the pasted JD path.
- Severity: Low.
- Initial state: Content beginning with `## 任职要求` was treated as already having a title, so the requested岗位名称 was not added as the Markdown H1.
- Root cause: Heading detection checked only whether the first line started with `#`.
- Solution: Only a line beginning with `# ` is treated as an existing一级标题; `##` and deeper headings now receive the generated岗位 H1.
- Verification: Backend suite passes with 81 tests, including the `##` case.
- Remaining risk: Markdown with an unusual leading HTML block may still need manual title review.

## 2026-08-18 - Similar JD Titles Could Produce The Wrong Interview Focus

- Discovered by: User requirement and public岗位样本对比。
- Severity: High.
- Initial state: The realtime adapter used the JD title `机械臂运控算法工程师` and a fixed system prompt. It could not distinguish a mechanical-arm MoveIt role from an industrial servo/FOC role or a humanoid whole-body control role when titles were similar.
- Root cause: No per-JD analysis artifact or role-direction field existed; interview context was hard-coded in `interviews.py` and `interviewer_persona.py`.
- Solution: Added per-JD analysis via Bailian `qwen3.6-plus`, with deterministic keyword fallback, curated public岗位样本 references, focus points, question strategy, and an initial interviewer prompt. The result is saved beside the JD as `*.analysis.json`; overwriting the JD invalidates stale analysis. The realtime system prompt now consumes the saved direction and focus points.
- Verification: Backend suite passes with 87 tests; frontend suite passes with 10 tests; production build succeeds. API coverage verifies direction classification, model JSON handling, fallback, persistence, and analysis status.
- Remaining risk: The current industry research context is curated at build time. A production version should add a configurable web-search provider and show source freshness before relying on rapidly changing company-specific details.

## 2026-08-18 - Generic Learning Keywords Could Override A Mechanical-Arm Direction

- Discovered by: Post-generation review of the first analysis for the local mechanical-arm JD.
- Severity: Medium.
- Initial state: The fallback classified the JD as “人形与异构机器人规划控制” because it contained “强化学习/VLA”, even though its primary evidence was mechanical-arm MoveIt, hand-eye calibration, and grasping.
- Root cause: The deterministic classifier checked generic humanoid/learning keywords before concrete manipulator workflow terms.
- Solution: Give concrete mechanical-arm terms priority unless explicit humanoid whole-body terms are present; add a mixed-keyword regression test and regenerate the saved analysis.
- Verification: The classifier test and full backend suite pass; the saved local JD analysis now resolves to “机械臂规划、控制与操作”.
- Remaining risk: Ambiguous cross-domain JD still benefits from human review of the generated focus points.

## 2026-08-18 - JD AI Analysis Timed Out And Used The Fallback

- Discovered by: Post-restart generation of the existing mechanical-arm JD analysis.
- Severity: Medium.
- Initial state: The analysis endpoint waited for the Bailian text call, then saved `analysis_mode=deterministic_fallback` with `ReadTimeout`; the result was valid but was not produced by the model.
- Root cause: The configured text-model request did not return within the current 30-second HTTP timeout. This is separate from the deterministic classifier and must not be hidden as a successful AI analysis.
- Solution: Preserve the usable local analysis, persist the mode and error type, and expose the mode in the management page. The endpoint remains ready to use Bailian when the text API responds.
- Verification: The saved JD now has the correct mechanical-arm direction; backend and frontend verification remain green.
- Remaining risk: The text API/network path still needs diagnosis before relying on model-generated company-specific distinctions. Live web-search integration is also still a planned extension.

## 2026-08-23 - MiniCPM-o Duplex Documentation Drifted From The Running Comni Endpoint

- Discovered by: Codex during the first local MiniCPM-o provider integration test.
- Severity: High.
- Initial state: The official duplex document described `prefix_system_prompt`, `audio`, and generic audio session IDs. The running Comni worker accepts `system_prompt`, requires `audio_base64`, and selects audio-only duplex only when the session ID starts with `adx_`.
- Root cause: The documentation and the Comni branch implementation evolved independently.
- Solution: Added a dedicated `minicpm` realtime provider that follows the running endpoint contract, converts browser PCM16 to MiniCPM Float32 PCM and converts model Float32 audio back to the frontend PCM16 contract. Provider selection remains independent from the existing Bailian adapter.
- Verification: Direct MiniCPM smoke returned `queue_done -> prepared -> stopped`; the project adapter prepared a real local session, submitted 1 second of 16 kHz PCM16, and received a MiniCPM turn-completion event. Adapter tests pass (4 tests), provider-selection test passes, and frontend realtime tests pass (10 tests).
- Remaining risk: MiniCPM-o duplex events currently do not expose candidate ASR text, so voice-only sessions do not yet provide a complete candidate transcript for report scoring. Text-input fallback remains available.

## 2026-08-23 - MiniCPM-o Fully Reloads The Model After Every Duplex Session

- Discovered by: Codex while closing failed and successful local duplex smoke sessions.
- Severity: High.
- Initial state: A disconnected or stopped duplex session sets the worker to loading and runs `full_reinit`, which restarts llama-server and reloads the model/TTS state before it can accept another session.
- Root cause: The upstream Comni C++ backend prioritizes a clean KV/TTS context over low reconnect latency.
- Solution: The project provider keeps the MiniCPM session prepared when the user only stops microphone capture; it releases the model only on `session.end` or browser disconnect. The frontend/backend test procedure waits for the worker health status to return to `idle` before opening a new session.
- Verification: Worker logs show the expected `full_reinit` lifecycle and healthy idle state after reload; the provider's `audio.stop` unit path does not send upstream `stop`.
- Remaining risk: The current single-GPU demo has several minutes of post-call downtime. Production use needs an upstream backend mode that resets session state without reloading all model weights, or multiple warm workers.

## 2026-08-24 - MiniCPM-o Audio And Chinese Interview Instructions Were Lost At The Provider Boundary

- Discovered by: User during local MiniCPM-o interview testing.
- Severity: High.
- Initial state: The interview could show text but did not play MiniCPM-o voice, responded in English, and did not react reliably to microphone speech.
- Evidence: The upstream worker emits synthesized audio as `audio_only.audio_data`, while the project provider only maps `result.audio_data`. Browser AudioWorklet output is roughly 8 ms per message, while MiniCPM-o's duplex worker requires 1-second chunks and retains only two queued chunks. The upstream C++ duplex initialization uses a fixed English prompt and intentionally skips per-session prompt updates.
- Root cause: The new provider was validated for WebSocket lifecycle and PCM conversion, but not against the upstream's separate WAV-poll audio event, one-second input cadence, or immutable duplex initialization prompt.
- Initial resolution plan: Map `audio_only` to the existing frontend PCM event, buffer browser PCM16 into one-second MiniCPM chunks, configure the upstream duplex initialization in Chinese, then perform a real microphone and speaker round-trip test.

## 2026-08-24 - Repeated Candidate Text Artificially Increased Deterministic Interview Scores

- Discovered by: User during report testing.
- Severity: High.
- Initial state: Re-entering the same textual answer could improve the displayed score.
- Evidence: The deterministic report generator concatenates every candidate answer before scoring; the scorer uses answer length and keyword presence, without novelty or duplicate handling.
- Root cause: The MVP scorer measures aggregate surface features, not distinct answer evidence.
- Initial resolution plan: Normalize exact repeated answers before deterministic scoring and skill-evidence extraction, add a regression test proving duplicates do not increase the score, and retain original transcript rows for auditability.

- Resolution: The deterministic report path now normalizes and de-duplicates exact candidate answers before scoring and evidence extraction, while retaining every original transcript row for auditability.
- Verification: The duplicate-answer regression test passes; the focused MiniCPM/report suite passes 13 tests and the full backend suite passes 100 tests.
- Remaining risk: Paraphrased repetition is still treated as distinct evidence. Semantic novelty scoring belongs in the later model-backed evaluator.

## 2026-08-24 - MiniCPM-o Comni Runtime Never Entered Speak State In Local End-to-End Tests

- Discovered by: Codex after implementing the provider-boundary fixes and repeating the local end-to-end audio test.
- Severity: High.
- Initial state: Browser-sized 8 ms PCM packets overflowed the Comni worker's two-item queue, and listener ticks caused turn-completion notifications. Synthesized `audio_only` messages were not mapped to the application audio contract.
- Resolution: The MiniCPM provider now maps `audio_only` to frontend PCM16 audio, batches browser input into one-second units, serializes upstream submission until each result is received, ignores listener-only turn completion, and sends two silent units after microphone stop for full-duplex turn detection. The Comni C++ initialization prompt was changed to Chinese. Bailian code paths were not changed.
- Verification: Adapter/report tests pass (13 focused tests), the full backend suite passes (100 tests), frontend tests pass (11 tests), and the production frontend build passes. A real 12-second audio test now reports `processed=12, dropped=0`; a six-second utterance plus two seconds of silence reports `processed=8, dropped=0`.
- Remaining blocker: In both real tests the upstream C++ runtime logged `LLM->TTS: text=''` for every processed unit and emitted no WAV/audio-only event. This prevents a live speaker round-trip despite correct project-side transport. It is an upstream `Comni + llama.cpp-omni` speech-decision/runtime issue, not an Alibaba/Bailian regression. Keep Bailian as the working default and investigate the matched upstream runtime/model build before treating MiniCPM full duplex as demo-ready.

## 2026-08-24 - Interview Setup Was Display-Only And Hard-Coded To One Candidate

- Discovered by: User while trying to begin a local interview.
- Severity: High.
- Initial state: The setup page listed resumes and job descriptions but offered no selection. The app hard-coded one profile/JD and the backend selected `REALTIME_MODE` globally, so a session could not choose Bailian versus MiniCPM or use a different candidate's resume as context.
- Resolution plan: Add explicit provider/profile/resume/JD session selection, pass it through the WebSocket handshake, validate and persist it server-side, and extract the selected PDF/DOCX text into the interviewer prompt.

- Resolution: Replaced display-only setup with required provider, candidate, resume, and JD selectors. The selection is URL-encoded into the realtime WebSocket handshake, validated against local profile/JD files, persisted to the interview ledger, and used to construct the Bailian system prompt. PDF text is extracted with `pypdf`; DOCX text is extracted from its standard document XML. Unsupported legacy `.doc` files now fail clearly instead of silently omitting context. MiniCPM retains the selection in the ledger, but the current upstream Comni runtime ignores dynamic per-session prompts, so the UI labels this limitation and directs complete context-based interviews to Bailian.
- Verification: Added context extraction and WebSocket selection persistence tests. Full backend suite passes with 103 tests; frontend suite passes with 12 tests; production frontend build passes.
- Remaining risk: Resume text is capped at 12,000 characters and does not yet include OCR for scanned PDFs. MiniCPM dynamic context requires an upstream Comni runtime that honors its existing `system_prompt` field.

## 2026-08-24 - MiniCPM Voice Turns Had No Candidate Transcript And Split Replies Into Fragments

- Discovered by: User after the MiniCPM speaker path began producing audio.
- Severity: High.
- Initial state: Spoken candidate answers appeared neither in the chat nor the durable interview transcript. One natural model response was shown as many small assistant bubbles.
- Root cause: The Comni audio-duplex protocol returns only the model's generated text; it has no candidate ASR field. Its local C++ runtime additionally sets `end_of_turn=true` on each one-second speech slice, rather than only after a complete response.
- Resolution: Added Chromium's native Chinese speech recognition alongside microphone capture. It renders temporary candidate text locally, sends one final `transcript.item` for the ledger and report after recording stops, and leaves the MiniCPM audio stream untouched. The provider now suppresses the upstream per-slice `end_of_turn` signal, letting the final candidate transcript form the chat boundary.
- Verification: Added browser transcription lifecycle coverage, an audio-interleaved transcript merge regression test, and MiniCPM false-turn-boundary coverage. Full backend suite passes with 103 tests; frontend suite passes with 14 tests; production frontend build passes.
- Remaining risk: Browser speech recognition depends on Chromium support and may use the browser vendor's speech service. A production offline guarantee needs a separate local ASR provider. MiniCPM itself still does not expose candidate ASR.

## 2026-08-24 - MiniCPM Queue Looked Connected Before Its Single GPU Worker Was Ready

- Discovered by: User when Edge showed a local candidate bubble but MiniCPM never replied, while the Codex embedded browser reported `SpeechRecognition: not-allowed`.
- Severity: High.
- Initial state: The frontend marked the interview connected on WebSocket open. MiniCPM had one active duplex Worker and two queued sessions, so audio and browser-local transcription could start before the server had received upstream `queue_done` and emitted `session.ready`.
- Root cause: Browser WebSocket transport readiness was conflated with model readiness. The upstream demo has one exclusive GPU Worker and performs a long model reinitialization after a duplex session; queued connection cancellation was not visible to the app.
- Resolution: The UI now enables microphone and text controls only after `session.ready`, displays `正在等待模型` while queued, and the backend bounds realtime provider setup to 45 seconds, closes the upstream connection on failure, and translates upstream WebSocket closure into a user-visible realtime error. Cleared the stale local queue and waited for the Worker to return to `idle`.
- Verification: MiniCPM gateway status confirmed one idle Worker and zero queued tasks. Full backend suite passes with 103 tests; frontend suite passes with 14 tests; production frontend build passes.
- Remaining risk: The upstream one-Worker demo still reloads after session teardown. Parallel user testing requires warm worker pooling or a runtime that can clear duplex state without full reinitialization.

## 2026-08-29 - MiniCPM Dynamic Interview Context Was Accepted But Never Applied

- Discovered by: User after MiniCPM changed roles and answered questions on the candidate's behalf.
- Severity: High.
- Initial state: The application sent a per-session interviewer prompt, but the C++ duplex backend reused only its weak startup prompt. Candidate reverse questions could move the model into a generic answer-assistant role, and the selected resume/JD did not affect the local model.
- Root cause: `CppBackendWorker.duplex_prepare` intentionally skipped `update_session_config` because that reset path clears the prepared KV/TTS state and can crash on the first audio prefill. The existing `/v1/stream/prefill` text capability was never used by the duplex prepare flow.
- Resolution: The MiniCPM adapter now compiles a provider-specific context of at most 500 characters, preserving interviewer identity, reverse-question refusal, job focus, project/skill evidence, strategy, and a short resume excerpt. Comni prefills that context as hidden unit 0 during `prepare`; audio begins at unit 1. A failed context prefill now fails session preparation instead of reporting false readiness. The worker startup prompt independently locks the Chinese interviewer role. Bailian instructions and transport were not changed.
- Verification: Runtime logs show the selected candidate/JD/resume context reaching the worker, `/v1/stream/prefill` returning 200, and the first audio arriving as `duplex_1.wav`. The initial 580-character prompt cost about 4 seconds on first audio, so it was reduced to about 340 characters. In the shortened-prompt smoke, the context occupied about 271 KV tokens and the first audio unit completed in 175 ms. When synthetic speech asked the model to explain the full MoveIt answer instead of interviewing, MiniCPM produced seven audio chunks and replied, "这是考察运动学/逆运动学与 MoveIt。请说一下你的思考过程。" It therefore kept the interviewer role and handed the question back to the candidate. Backend passes 104 tests, frontend passes 14 tests, the production build succeeds, and Comni's three focused tests pass.
- Remaining risk: Dynamic context is a normal user-text unit rather than protected system KV and may eventually leave the sliding window in very long sessions. Duplex speech and TTS latency still varies by chunk, and the worker still performs a full model reinitialization after each ended duplex session.

## 2026-08-29 - MiniCPM Readiness And Reload Lifecycle Looks Like A Failed Startup

- Discovered by: User during repeated local MiniCPM connection attempts.
- Severity: High.
- Initial state: Docker remains up and MiniCPM can process an `audio_duplex` session, but every completed or disconnected session performs a multi-minute full model reload. The page alternates between waiting, timeout, and a stale disconnected WebSocket without showing the Worker lifecycle.
- Evidence: Gateway status showed an active duplex Worker and processed audio while the user perceived that MiniCPM had not started. Previous attempts timed out during `loading_workers=1`, then required a manual reconnect after the Worker returned to `idle_workers=1`.
- Initial resolution direction: Expose Worker states before opening the interview WebSocket, disable connect while loading, and distinguish start, queue, reload, ready, and failed states. Do not ask the user to infer Docker state from a generic connection label.

## 2026-08-29 - Ending An Interview Has No Exit Path And Races Report Persistence

- Discovered by: User after a long Bailian interview.
- Severity: High.
- Initial state: The interview screen only offers `结束并生成报告`; there is no `退出面试` action. The frontend sends `session.end`, immediately closes its WebSocket, and navigates to report analysis without waiting for the server to acknowledge and persist the ledger.
- Evidence: Recent sessions containing `session.end` were still stored as `status=disconnected` and `close_reason=browser_disconnect`. The report client retries for only about one second, while a long interview ledger can take longer to serialize.
- Initial resolution direction: Separate discard/exit from finish/analyze, add an explicit ending state, wait for a server acknowledgement or durable-session endpoint, and show report-generation progress and failure details.

## 2026-08-29 - Long Bailian Interview Silently Fell Back To Misleading Deterministic Scoring

- Discovered by: User after reviewing the latest long interview report.
- Severity: Critical.
- Initial state: An 18-minute Bailian interview with 71 transcript entries produced a generic summary, fixed gaps, and an unexplained 3.8 score.
- Root cause evidence: The stored report has `analysis_mode=deterministic_fallback` and `analysis_error=ReadTimeout`. The fallback scores the entire concatenated interview by length, punctuation, a few mechanism words, and the presence of any number. It penalizes communication whenever all answers together exceed 500 characters and does not score individual question-answer evidence. The UI also omits the score denominator.
- Initial resolution direction: Preserve the failed analysis as a visible retryable state instead of presenting fallback output as a real assessment; evaluate per question against a job-specific rubric, attach evidence quotes and confidence, and aggregate only validated dimensions.

## 2026-08-29 - Realtime Transcript Lacks Stable Turn Identity And Does Not Auto-Scroll

- Discovered by: User during the latest Bailian interview.
- Severity: High.
- Initial state: The conversation pane does not follow the latest message. Candidate and interviewer fragments can be grouped into the wrong visible bubble.
- Root cause evidence: Normalized realtime events discard upstream item/response identifiers. The frontend then infers boundaries only from event order and `response.done`; interleaved partial ASR and assistant deltas cannot be grouped reliably. The scroll container has overflow styling but no scroll-to-latest behavior.
- Initial resolution direction: Carry stable turn/item identifiers through the provider contract, project messages by identity instead of adjacency, and auto-follow only while the user has not intentionally scrolled upward.

## 2026-08-29 - Bailian Runs Two ASR Paths And Can Hear Its Own Speaker Output

- Discovered by: User when the model appeared to answer its own question and voices were merged.
- Severity: Critical.
- Initial state: Browser microphone upload continues while assistant audio plays. Browser speech recognition is also started for Bailian even though Bailian already returns authoritative input-audio transcription.
- Root cause evidence: The long interview contains 41 provider candidate transcripts plus one browser-submitted 429-character candidate transcript containing interviewer speech. The microphone track requests echo cancellation, but there is no application-level playback gate; the model produced a candidate-style answer immediately after its own question while the microphone remained open.
- Initial resolution direction: Use Bailian ASR only for Bailian and browser/local ASR only for MiniCPM. Make reliable half-duplex echo suppression the default by pausing upstream microphone submission during assistant playback; treat barge-in/full-duplex as an explicit experimental mode until acoustic echo cancellation is verified.

- Diagnostic correction: The user confirmed a headset was in use. Event-level replay of the self-answer incident shows that Bailian's upstream ASR transcribed only the candidate utterance `呃。` before the model generated a candidate-style answer; it did not transcribe the preceding interviewer question as input speech. The application also uses separate microphone and playback Web Audio graphs and does not intentionally route output into capture. Therefore this specific self-answer is better explained by interviewer-role/prompt failure after a weak candidate utterance, not proven audio loopback. The separate browser-ASR transcript did contain interviewer speech, but `transcript.item` is ledger-only and is not dispatched to either realtime model. Echo gating should remain an optional diagnostic/reliability mode, not the assumed root-cause fix.

## 2026-08-29 - Interview Has No Duration, Topic Or Stage Controller

- Discovered by: User during a long unbounded interview.
- Severity: High.
- Initial state: Setup chooses a JD but not a duration or interview topic. The realtime model can continue indefinitely and repeatedly deep-dive one area without reserving time for other competencies or closing questions.
- Initial resolution direction: Add a small set of duration choices and topic presets, derive a stage budget, display remaining time/current topic, and end or transition stages through provider-neutral session control.

## 2026-08-29 - Realtime Interviewer Still Asks Compound Questions

- Discovered by: User during Bailian voice testing.
- Severity: Medium.
- Initial state: Although the system prompt says one question per turn, the latest transcript contains repeated questions with two to four separate requests, metrics, edge cases, and implementation details in one turn.
- Root cause evidence: Prompt-only compliance is best effort, and realtime audio is already spoken before application code can post-process it. The current instruction does not impose a measurable sentence/length budget or a stage-level question objective.
- Initial resolution direction: Define one evidence objective per turn, a short utterance budget, and a question queue. Strict enforcement requires generated-question orchestration before TTS; pure realtime prompting can only provide best-effort enforcement.

## 2026-08-31 - Phase 1 Provider Readiness Resolution

- Resolves: `MiniCPM Readiness And Reload Lifecycle Looks Like A Failed Startup` and the stale-connect portion of `MiniCPM Queue Looked Connected Before Its Single GPU Worker Was Ready`.
- Root cause: The application exposed only WebSocket transport state. It did not normalize Bailian configuration or Comni Worker loading, busy, queue, idle, and offline states before connection.
- Resolution: Added `GET /api/interviews/providers/{provider}/status`, including defensive Comni response normalization. Setup and interview screens poll the selected provider and enable start/connect only when its normalized state is `idle`.
- Verification: A real browser smoke showed Bailian as `百炼服务已配置` with start enabled. With Docker intentionally stopped and no listener on port 8006, MiniCPM changed to `MiniCPM 服务不可用` and start remained disabled. Backend tests cover idle, loading, busy, queued, malformed, and unreachable status payloads.
- Remaining risk: The idle-after-reload transition was not live-smoked in this cycle because starting MiniCPM would allocate GPU memory. Its normalization and polling paths are covered by automated tests.

## 2026-08-31 - Phase 1 Durable Finish And Cancel Resolution

- Resolves: `Ending An Interview Has No Exit Path And Races Report Persistence`.
- Root cause: The browser closed immediately after `session.end`, so navigation could win the race against ledger persistence; cancel had no separate protocol or product action.
- Resolution: Added separate `退出面试` and `结束并生成报告` actions. Both enter an ending state, and the frontend waits for backend `session.persisted` before closing or navigating. The backend persists exactly once as `completed/client_session_end` or `cancelled/client_session_cancel` before acknowledging.
- Verification: WebSocket lifecycle tests assert durable acknowledgement order, stored status, close reason, and that cancel does not create a report.
- Remaining risk: Report analysis quality and retry UX are Phase 3 work; durable interview evidence is now available before that analysis starts.

## 2026-08-31 - Phase 1 Transcript Identity And Follow Resolution

- Resolves: `Realtime Transcript Lacks Stable Turn Identity And Does Not Auto-Scroll` and the fragmented-reply portion of `MiniCPM Voice Turns Had No Candidate Transcript And Split Replies Into Fragments`.
- Root cause: Provider item/response identifiers were discarded, while the UI grouped adjacent stream fragments and had no user-aware scroll policy.
- Resolution: Provider adapters now preserve or generate stable `turn_id`, `item_id`, and `response_id` values. The chat projection merges by identity and tracks finality. It follows new messages while the reader is near the bottom and exposes an accessible return-to-latest control after intentional upward scrolling.
- Verification: Adapter, ledger, and frontend projection tests cover interleaved turns, partial/final replacement, legacy events, and the 80-pixel near-bottom threshold.

## 2026-08-31 - Phase 1 ASR Ownership And Playback Gate Resolution

- Resolves: The duplicate-ASR and feedback-risk portions of `Bailian Runs Two ASR Paths And Can Hear Its Own Speaker Output`.
- Root cause: Bailian provider ASR and browser ASR could both create candidate transcript evidence. Audio upload also had no optional application-level gate during assistant playback.
- Resolution: Bailian now accepts only `provider_asr` as authoritative candidate evidence and never starts browser speech recognition. MiniCPM uses `browser_asr` until a local ASR exists. Client source labels are normalized at the trust boundary so a browser cannot claim provider authority. Bailian remains full duplex by default; users can opt into `模型说话时暂停上传麦克风`, which drops outgoing chunks only while queued model audio is playing without stopping the microphone stream.
- Verification: Authority and source-spoof regression tests pass. Frontend tests cover provider-specific ASR selection, queued playback state, and upload-gate policy.
- Remaining risk: The earlier headset incident remains more consistent with interviewer-role drift than proven acoustic loopback. The optional gate is a reliability/diagnostic mode, not a replacement for prompt and orchestration work.

## 2026-08-31 - Per-Packet Audio Events Made Long Ledgers Grow Without Bound

- Discovered by: Codex during Phase 1 long-session reliability analysis.
- Severity: High.
- Initial state: One durable event was stored for every small input and output audio packet, so a long interview could produce a large ledger without adding scoring evidence.
- Root cause: Transport telemetry and durable interview evidence shared the same append-only event path.
- Resolution: Audio packet rows are no longer persisted. The ledger keeps four counters: input/output chunks and input/output bytes; boundaries, errors, and transcripts remain durable.
- Verification: A 152,000-packet regression test produces the expected counters, no packet rows, and a serialized ledger below 1 MB.

## 2026-08-31 - Phase 1 Verification Summary

- Backend: `python.exe -m pytest -q` from `services/api` -> 121 passed.
- Frontend: `npm.cmd test -- --run` from `apps/web` -> 22 passed.
- Production build: `npm.cmd run build` -> passed.
- Repository whitespace check: `git diff --check` -> passed; existing line-ending warnings remain informational.
- Deferred by design: evidence-based report scoring, duration/topic/stage control, and strict one-objective-per-question orchestration remain Phase 2 and Phase 3 items. They are not marked resolved by this reliability phase.

## 2026-08-31 - MiniCPM Worker Times Out Just Before A Cold Model Load Completes

- Discovered by: User and Codex while starting the Docker Desktop MiniCPM image.
- Severity: High.
- Initial state: The container remained at `Waiting for Workers to load models (~30-90s)` for more than five minutes and never opened gateway port 8006.
- Root cause evidence: `/app/tmp/worker_0.log` records `RuntimeError: C++ server startup timeout (300s)`. The Python Worker then exited, while the orphaned `llama-server` finished loading shortly afterward and returned `{"status":"ok"}` on its internal port 19080. The model file is 5.03 GB on the host bind mount; the process read about 5.08 GB and spent most of startup in disk sleep. GPU memory reached about 8.6 GB only after the Worker timeout.
- Initial resolution direction: Make the C++ startup timeout configurable and longer than the observed Docker Desktop cold-load time, terminate the child server when Worker startup fails, and have the entrypoint fail immediately when a Worker process exits instead of polling its health for another ten minutes. Then rebuild/restart once and verify port 22400, gateway 8006, and normalized provider state `idle`.
- Resolution (2026-09-01): Added configurable `CPP_SERVER_STARTUP_TIMEOUT_SECONDS=900`, `OMNI_INIT_TIMEOUT_SECONDS=600`, and `WORKER_STARTUP_TIMEOUT_SECONDS=960`. C++ startup timeout now terminates its child process; `load_model` also cleans the child when Omni/TTS initialization fails. The entrypoint detects an exited Worker immediately and prints its log instead of continuing blind health polling.
- Additional root cause: After the first fix allowed the 5 GB GGUF load to pass 300 seconds, `/v1/stream/omni_init` exposed a second fixed 120-second timeout. TTS initialization exceeded that limit and caused another Worker exit. It now uses the configured 600-second timeout.
- Verification: The image rebuilt entirely from Docker cache except for the application layers. A real cold start completed without restart: gateway status reported `gateway_healthy=true`, `total_workers=1`, `idle_workers=1`, and zero loading/error/offline workers. The application readiness endpoint returned `minicpm/idle` with `模型已就绪`. Eight focused unit tests and the built-image shell syntax check pass.
- Operational note: This cold start took about seven minutes on the current Docker Desktop bind mount. The ready process uses about 13.4 GB of the 16.3 GB GPU memory; stopping the container in Docker Desktop releases it.

## 2026-09-03 - Bailian Interview Selection Does Not Guarantee JD-Grounded Questions

- Discovered by: User and Codex while tracing the latest API-only interview through the code graph and stored ledger.
- Severity: High.
- Initial state: Setup passes the selected `jd_id`, and data management offers `AI 分析面试重点`, but a selected JD without a saved analysis supplies Bailian only with its title, a generic robot-control direction, an empty focus list, and a generic instruction. The raw JD body is not present in realtime `instructions`.
- Evidence: The latest stored interview selected `校招-多模态应用工程师`, whose `analysis_ready` value is false. Its first application-generated question combined a resume project about physical robot deployment with the role title, while the first provider question deep-dived a resume VLA timing issue rather than a JD requirement. Only the mechanical-arm JD currently has an analysis; that artifact is a deterministic fallback after a Bailian text-analysis `ReadTimeout`.
- Root cause: `load_interview_context` loads the JD body but discards it after deriving `target_role`; it forwards only optional `role_direction`, `focus_points`, and `initial_prompt`. `question_strategy` is generated and persisted but has no runtime consumer. `LocalTextInterviewer.initial_question` uses the selected role title and a resume-project heuristic, not the JD body or analyzed focus.
- Initial resolution direction: For Bailian, always inject a bounded raw JD body into realtime `instructions`; treat saved analysis as an optional structured enhancement, not the sole source of JD grounding. Consume `question_strategy`, derive the opening question from JD focus, and expose or automatically perform analysis before starting while preserving a transparent deterministic fallback.
- Professional classification: This solution is named **JD-Grounded Prompt Orchestration（基于岗位描述的提示词编排）**. Its core mechanism is **JD Grounding（岗位描述约束注入）**, which means carrying selected JD evidence through application context into the provider's final prompt instead of relying on a role title alone.
- Resolution: The Bailian context now carries up to 8,000 characters of raw JD text plus optional saved `focus_points`, `initial_prompt`, and `question_strategy`. Realtime and text-model instructions receive those fields, mark JD content as non-executable factual material, require every question to map to a JD requirement, and derive the opening question from the first analyzed focus or raw JD requirement. Missing or timed-out pre-analysis no longer removes JD grounding. The MiniCPM configuration and transport path were not changed.
- Distribution resolution: Added `start-api.cmd` / `stop-api.cmd`, guarded PowerShell launchers, and `docs/bailian-api-setup.md`. The launcher validates API mode without printing the secret, installs only missing dependencies, reuses healthy services, waits for readiness, records owned process identities, and never starts Docker/MiniCPM.
- Verification: The new tests were observed failing before implementation, then passed after the data path was connected. Full backend suite: 126 passed. Frontend suite: 22 passed. Production frontend build passed. PowerShell syntax and `start-api.ps1 -Check` passed. A real startup run reused the healthy frontend, replaced the stale non-reloading backend, and returned a healthy API on port 8000.
- Remaining risk: Realtime model compliance is still probabilistic. Strict stage budgets and one-objective question queues require the separate interview-controller work already tracked in this file.

## 2026-09-03 - Successful Bailian Conversations Appear As Failed Calls In The Console

- Discovered by: User while comparing a working realtime conversation with the Alibaba Model Studio console.
- Severity: Medium.
- Initial state: Candidate ASR, assistant audio/text, and `response.done` all succeed locally with no `realtime.error`, but the provider console can classify the completed WebSocket call as failed, previously observed as `400 ClientDisconnect`.
- Root cause evidence: The application handles `session.end` and `session.cancel` locally, immediately cancels the upstream receive task, and closes the Bailian WebSocket. It never sends the provider `session.finish` event or waits for `session.finished`, so a successful inference can still have an abrupt connection-level terminal status.
- Initial resolution direction: Add a bounded Bailian shutdown handshake: send `session.finish`, keep the relay alive until `session.finished` or a timeout, then close and persist. For cancellation, cancel an in-progress response before finishing. Preserve unexpected browser/tab disconnects as genuine client disconnects.
- Billing note: A failed terminal status does not prove that generated input/output usage is free; reconcile costs against the provider usage and billing records.

## 2026-09-04 - Public Repository Sanitization

- Discovered by: User and Codex during the pre-publication repository audit.
- Severity: High.
- Initial state: Tracked source, tests, documentation, and one screenshot contained personal identifiers, an internal-only source address, and machine-specific local paths. The repository also had no explicit open-source license.
- Resolution: Replaced public-facing personal identifiers with the project pseudonym, removed the internal address, converted local paths to repository-relative instructions or neutral placeholders, removed the affected screenshot, and added the MIT License.
- Verification plan: Scan the current index and every reachable Git revision for personal identifiers, private-network addresses, machine-specific paths, credentials, private keys, and accidentally tracked private documents before rewriting and pushing the sanitized history.
