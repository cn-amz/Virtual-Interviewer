# Current Unresolved Issues

Updated: 2026-09-05

This file tracks currently open work. Resolved problems and their final fixes belong in `docs/issues.md`.

## P0 - Competition Credibility And Demo Stability

### 0. Runtime Storage Directory Must Be Explicit In Deployment

- Status: Resolved for local MVP; deployment configuration remains open
- Severity: High
- Area: Runtime data and privacy
- Current state: The local default resolves relative to `config.py`, while `APP_STORAGE_DIR` can explicitly select a deployment volume.
- Gap: Public deployment still needs an absolute storage path and startup validation.
- Impact: A misconfigured working directory could read or write the wrong user's data.
- Next action: Set and document an absolute `APP_STORAGE_DIR` in the deployment runbook.

### 1. Report And Ability Tree Need Evidence-Based Model Scoring

- Status: Resolved for local MVP; rubric depth remains open
- Severity: High
- Area: Post-interview report, scoring, ability tree
- Current state: Reports use the saved transcript, call Bailian `qwen3.6-plus` for structured summary/gaps when configured, and retain deterministic scoring as a fallback.
- Gap: The next iteration should add per-dimension quoted evidence and explicit score reasons.
- Impact: The product can look like a chat demo instead of a credible interview training Agent.
- Next action: Add per-dimension evidence quotes and `AbilityTreeChange` records from transcript spans.

### 2. Realtime Interview Events Need Persistent Evidence Storage

- Status: Resolved for local MVP; transactional scaling remains open
- Severity: High
- Area: Realtime WebSocket, reporting
- Current state: Each session writes a JSON ledger with normalized client/server/provider events and a complete text transcript; base64 audio is retained only as byte metadata.
- Gap: High-volume deployment should use append-only transactional storage and immutable source versions.
- Impact: Reports and ability-tree updates cannot be audited.
- Next action: Move the local ledger to a transactional event store when public multi-user deployment begins.

### 3. Voice Turn Policy Needs To Match The Current UI

- Status: Open
- Severity: High
- Area: Realtime audio
- Current state: The frontend still presents a start/stop microphone interaction, while the realtime session uses server VAD behavior.
- Gap: Stopping local capture does not necessarily mean the model has committed the turn and created a response.
- Impact: In some live microphone sessions, the model may transcribe speech but fail to answer reliably.
- Next action: For the current button UI, switch to a Manual turn policy: commit the input audio buffer and create a response on `audio.stop`. Track continuous VAD full-duplex as a later mode.

### 4. Public Demo Deployment Is Not Done

- Status: Open
- Severity: High
- Area: Competition deliverable
- Current state: Local development works at `127.0.0.1`; public endpoint ideas are documented but not executed.
- Gap: No stable public HTTPS URL, domain, or tested tunnel workflow is finalized.
- Impact: Competition deliverables require an online app link, and microphone behavior must be tested over a real browser-accessible deployment.
- Next action: Choose one deployment path and write a runnable runbook: temporary tunnel for early demo or Aliyun/ECS/SAE/Function Compute for final submission.

### 17. Voice Endpointing Treats Hesitation Or Breath As A Completed Answer

- Status: Open
- Severity: High
- Area: Realtime audio, VAD, turn taking
- Current state: Real microphone sessions can close a candidate turn during a short hesitation and let the interviewer continue, while breath noise can occasionally become candidate speech evidence.
- Gap: Acoustic VAD boundaries are not checked against minimum voiced duration, ASR confidence, or semantic answer completeness before the next question begins.
- Impact: The interviewer can interrupt an unfinished answer, score noise as evidence, and create an unnatural conversation rhythm.
- Next action: Capture representative audio traces, calibrate VAD thresholds and silence duration, add a short semantic grace window, and reject low-information ASR turns before triggering follow-up generation.
- Acceptance: Short pauses inside a sentence do not end the turn, breath-only input creates no transcript or score evidence, and normal answers still receive a response within the agreed latency budget.

## P1 - Product Loop

### 5. Resume/JD Retrieval Is Still Lightweight

- Status: Open
- Severity: Medium
- Area: RAG and personalization
- Current state: The local interviewer uses profile summary, project names, skills, and JD title.
- Gap: It does not yet perform deep retrieval from full resume documents, `qa_bank.md`, or a Bailian knowledge base.
- Impact: Follow-up questions can be role-aware, but may miss detailed resume evidence.
- Next action: Add structured retrieval over profile/JD/QA material, then expose retrieved evidence to both text and voice interview planning.

### 6. Dynamic Profile/JD Session Wiring Is Incomplete

- Status: Open
- Severity: Medium
- Area: Interview setup
- Current state: The backend still has default profile and JD identifiers for the realtime path.
- Gap: The interview configuration page is not yet the single source of truth for profile, JD, mode, intensity, and duration.
- Impact: The product still feels like a fixed demo instead of a reusable interview trainer.
- Next action: Create interview sessions from setup choices and pass the selected context into realtime and report generation.

### 7. Ability Tree Changes Need An Audit Trail

- Status: Resolved for local evidence browsing; change history remains open
- Severity: Medium
- Area: Ability tree
- Current state: Ability nodes now expand to persisted questions, answers, and related knowledge points; JSON and Obsidian-style Markdown are both available.
- Gap: Users still need first-class change records with evidence snippets, score deltas, and change reasons.
- Impact: Long-term growth claims are less convincing.
- Next action: Add `AbilityTreeChange` records and show growth/decline deltas in the history detail page.

### 8. Historical Reports Need A Real List And Detail Flow

- Status: Resolved for local MVP; multi-user ownership remains open
- Severity: Medium
- Area: Reports
- Current state: The dashboard opens a filtered history list backed by `data/interviews/*.json`; only non-empty `iv_` sessions are shown, and each item opens the stored report detail without a new model call.
- Gap: The local MVP does not yet persist and enforce a complete account-to-profile ownership relation.
- Impact: Suitable for the single-user competition demo, but not yet ready for public multi-user history privacy.
- Next action: Add owner IDs and filter history by account/profile before public deployment.

### 13. Ability Tree Semantic Grouping Needs Human Review

- Status: Partially resolved for local MVP
- Severity: Medium
- Area: Ability tree / text model
- Current state: The tree is organized as type branch -> canonical question -> all preserved answers. Exact repeated questions merge locally; the optional Bailian text action can merge paraphrases and validates evidence coverage.
- Gap: A model may choose an imperfect canonical wording or type for a semantically ambiguous question.
- Impact: Incorrect grouping could make a report look cleaner while hiding distinctions between different interview intents.
- Next action: Add a user-confirmation diff and an undoable `AbilityTreeChange` record before using semantic grouping in a public multi-user deployment.

### 14. Obsidian Protocol Opening Depends On Desktop Registration

- Status: Resolved for local MVP with fallback
- Severity: Low
- Area: Obsidian integration
- Current state: The page sends an encoded `obsidian://open?path=...` URI and exposes the absolute `index.md` path for copy/open-file fallback.
- Gap: Browser containers may suppress custom URI navigation and cannot report whether Obsidian accepted the request.
- Impact: A user may need one manual step to open the generated vault.
- Next action: Add optional vault registration and a local helper/deep-link handshake only if the competition demo environment needs one-click opening.

### 18. Interview Coverage Overweights Project Depth And Engineering Detail

- Status: Open
- Severity: High
- Area: Interview orchestration, JD grounding
- Current state: Follow-up depth and engineering investigation are useful, but sessions ask too few foundation questions and too few direct questions about JD fit.
- Gap: The interviewer has no explicit competency coverage ledger or stage quota balancing fundamentals, role requirements, project depth, engineering practice, and behavioral evidence.
- Impact: A technically deep interview can still produce an incomplete assessment of basic knowledge and actual position fit.
- Next action: Derive a competency matrix from the JD, assign duration-aware question budgets, and let follow-ups consume a bounded budget rather than the whole session.
- Acceptance: Every completed interview reports which competency dimensions were covered, and a normal-length session includes both foundation and JD-fit evidence without sacrificing targeted project follow-ups.

### 19. Historical Reports And Ability Branches Contain Unstable Or Boilerplate Conclusions

- Status: Open
- Severity: High
- Area: Reporting, scoring, ability tree
- Current state: Some historical ability branches appear incorrect, while several phrases remain present regardless of interview quality.
- Gap: Deterministic fallback copy, model-generated conclusions, and evidence-backed ability updates are not separated clearly enough; some nodes can be created without a strong transcript citation.
- Impact: Reports can look plausible while failing to distinguish strong, weak, repeated, or empty interviews.
- Next action: Trace each report field and tree mutation to source turns, remove unconditional assessment copy, and add contrast tests for empty, weak, repeated, and strong answer sets.
- Acceptance: Every evaluative branch cites interview evidence, materially different interviews produce materially different conclusions, and empty or repeated content cannot receive generic positive growth text.

### 20. Persisted JD Analysis Is Not Discoverable After The Initial Action

- Status: Open
- Severity: Medium
- Area: JD analysis, data-management UX
- Current state: Clicking `AI 分析面试重点` shows the result immediately and persists a `*.analysis.json`, but returning to the page only shows that analysis exists and offers no clear way to reopen it.
- Gap: The frontend does not load or expose the existing analysis artifact as a first-class detail view.
- Impact: Users cannot inspect, compare, or trust the exact interview focus that will be injected later.
- Next action: Add `查看分析` and `重新分析` actions, load persisted analysis on demand, and display analysis mode, source, update time, focus points, question strategy, and opening prompt.
- Acceptance: Reloading the application preserves a visible path to the saved analysis without making another model call.

### 21. Ability Tree Information Architecture Does Not Explain Growth Clearly

- Status: Open
- Severity: High
- Area: Ability tree UX and domain model
- Current state: Ability types, canonical questions, answer evidence, knowledge points, strengths, and target skills coexist, but the hierarchy and the meaning of “待提升” remain difficult to understand.
- Gap: Observed evidence, assessed capability, knowledge gaps, and recommended next actions are not visually and semantically separated.
- Impact: Users cannot quickly answer what was tested, what evidence supports the assessment, what is missing, or what to practice next.
- Next action: Redesign the tree around stable competency domains with separate evidence and growth-plan views, explicit node status, evidence count, confidence, and next action.
- Acceptance: A first-time user can trace any conclusion back to an answer and identify the next practice action without reading raw JSON or internal terminology.

### 22. A Fresh Clone Cannot Bootstrap A Complete Interview Profile From The UI

- Status: Open
- Severity: High
- Area: Open-source onboarding, profile management
- Current state: Private profile data is correctly excluded from Git, and uploading a resume creates `profile.json`, but realtime context loading also requires `prompt.txt` and `qa_bank.md`.
- Gap: The UI and backend do not create safe defaults or explain the missing files before session creation.
- Impact: A new open-source user can configure the API and upload a resume yet still fail to start the first interview.
- Next action: Add a sanitized starter profile or generate minimal prompt and QA files during profile creation, then validate completeness in the setup page.
- Acceptance: A fresh clone can reach a working first interview using only documented setup and UI actions, with no private files or manual directory repair.

## P2 - Polish And Expansion

### 9. Realtime Relay Errors Need Clear Surfacing

- Status: Resolved for local MVP; provider close metadata remains open
- Severity: Medium
- Area: Realtime reliability
- Current state: Provider relay exceptions are converted into a safe `realtime.error` event and persisted in the session ledger.
- Gap: Provider-specific close codes and completion markers are not yet normalized.
- Impact: Debugging live demos is harder.
- Next action: Add provider close code/reason and `response.done` timing to the ledger after protocol validation.

### 10. Text Model Latency Can Be Reduced

- Status: Open
- Severity: Low
- Area: Text interview mode
- Current state: Text calls work, but the text client creates a fresh HTTP client per request.
- Gap: Connection reuse is not implemented.
- Impact: Typed replies can feel slower than necessary.
- Next action: Reuse an async HTTP client or app-level client while preserving test injection.

### 11. Frontend Visual Polish Remains MVP-Level

- Status: Open
- Severity: Low
- Area: Frontend UX
- Current state: Functional MVP pages exist for login, dashboard, setup, interview, ability tree, and report.
- Gap: Visual design is not yet competition-polished.
- Impact: Usability is acceptable, but presentation may undersell the project.
- Next action: Use an external UI design pass or frontend-specific generation tool, then have Codex review integration quality.

### 12. GitHub Collaboration Model Needs Final Decision

- Status: Open
- Severity: Low
- Area: Collaboration
- Current state: Repository is currently under a personal GitHub account.
- Gap: Personal repositories can invite collaborators, but true teams require moving to or creating a GitHub Organization.
- Next action: Decide whether to keep personal repo with trusted collaborators or transfer to an Organization for team-based permissions.

### 15. Job Research Provider Is Curated, Not Live

- Status: Partially resolved for local MVP
- Severity: Medium
- Area: JD analysis /联网搜索
- Current state: Each JD can call Bailian text analysis with a curated public岗位样本 context; the generated direction, focus points, prompt, and source links are persisted per JD.
- Gap: The application does not yet call a live search provider at analysis time.
- Impact: Company-specific wording and rapidly changing requirements may not be reflected automatically.
- Next action: Add a configurable search provider interface and API key, then persist query, timestamp, snippets, and source URLs for each analysis.

### 16. JD Analysis Text Call Timed Out In Local Environment

- Status: Open
- Severity: Medium
- Area: Bailian text analysis
- Current state: Per-JD analysis, persistence, and deterministic fallback work. The current local call to `qwen3.6-plus` timed out after 30 seconds, so the existing JD is marked as fallback analysis.
- Gap: The cause may be endpoint/model availability, network path, or request latency; it needs the same console/API verification as the interview text path.
- Impact: The app can generate focus points but cannot yet guarantee model-specific semantic analysis.
- Next action: verify the DashScope endpoint and model name in the Alibaba console, then add request timing and a configurable analysis timeout.
