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
