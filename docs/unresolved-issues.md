# Current Unresolved Issues

Updated: 2026-06-30

This file tracks only currently unresolved work. Resolved problems and their final fixes belong in `docs/issues.md`.

## 1. Live Microphone Path Needs Manual Browser Verification

- Status: Open
- Severity: High
- Area: Realtime audio
- Current state: The frontend now captures microphone audio through `AudioWorklet` and sends `audio/pcm` with `sample_rate=16000`. Backend adapter accepts that format and forwards chunks to Bailian.
- Missing verification: A real browser microphone session with spoken human audio has not yet been fully validated end-to-end.
- Risk: Browser permission behavior, device sample-rate behavior, VAD thresholds, or provider response timing may still affect live demo quality.
- Next action: Run a live spoken interview test and check Alibaba console call status, frontend transcript events, and assistant response events.

## 2. Assistant Audio Playback Is Not Yet Implemented

- Status: Open
- Severity: High
- Area: Frontend realtime UX
- Current state: Backend maps Bailian `response.audio.delta` into `assistant.audio.chunk`.
- Gap: The frontend does not yet decode/play returned PCM audio chunks.
- Impact: The user may see text/event output but not hear the virtual interviewer.
- Next action: Add an audio playback queue for `assistant.audio.chunk`, decode PCM chunks, and play through Web Audio.

## 3. Text Mode Is Local, Not Cloud-Generated

- Status: Open
- Severity: Medium
- Area: Text interview mode
- Current state: Typed answers use a deterministic local low-cost interviewer path and do not call Qwen-Omni-Realtime.
- Reason: Realtime Omni is designed for audio/video realtime input and is more expensive; text-only practice should remain cheaper.
- Gap: Text mode is adaptive but not model-generated.
- Next action: Add an optional `TEXT_MODE=local|bailian_text` setting and connect a cheaper Bailian text model with RAG when richer text-only interviews are needed.

## 4. Resume/JD Retrieval Is Still Lightweight

- Status: Open
- Severity: Medium
- Area: RAG and personalization
- Current state: The local text interviewer uses profile summary, project names, skills, and JD title.
- Gap: It does not yet perform deep retrieval from the full resume documents, `qa_bank.md`, or a Bailian knowledge base.
- Impact: Follow-up questions can be role-aware, but may miss detailed resume evidence.
- Next action: Add structured retrieval over `profile.json`, `qa_bank.md`, and JD sections, then expose `retrieve_profile_context` results to both text and audio interview planning.

## 5. Report Generation Is Still Deterministic

- Status: Open
- Severity: Medium
- Area: Post-interview report
- Current state: The report and ability tree are generated with deterministic prototype scoring.
- Gap: Scoring is not yet model-assisted and does not deeply cite transcript evidence.
- Impact: Good for demo flow, but not yet strong enough for final competition evaluation.
- Next action: Add rubric-based scoring with transcript evidence, skill gaps, and growth/decay changes per interview.

## 6. Public Demo Deployment Is Not Done

- Status: Open
- Severity: High
- Area: Competition deliverable
- Current state: Local dev works at `127.0.0.1`; public endpoint providers are only reserved interfaces.
- Gap: No stable public URL, HTTPS, domain, or tunnel workflow is finalized.
- Impact: Competition deliverables require an online app link.
- Next action: Choose deployment path: temporary tunnel for early demo, or cloud deployment with HTTPS for final submission.

## 7. Frontend Visual Polish Remains MVP-Level

- Status: Open
- Severity: Low
- Area: Frontend UX
- Current state: Functional MVP page exists for setup, interview, and report.
- Gap: Visual design is not yet competition-polished.
- Impact: Usability is acceptable, but presentation may undersell the project.
- Next action: Use an external UI design pass or frontend-specific generation tool, then have Codex review integration quality.

## 8. GitHub Collaboration Model Needs Final Decision

- Status: Open
- Severity: Low
- Area: Collaboration
- Current state: Repository is currently under a personal GitHub account.
- Gap: Personal repositories can invite collaborators, but true teams require moving to or creating a GitHub Organization.
- Next action: Decide whether to keep personal repo with trusted collaborators or transfer to an Organization for team-based permissions.

