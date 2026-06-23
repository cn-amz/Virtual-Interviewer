# Virtual Interviewer Design Spec

Date: 2026-06-24

## Summary

Virtual Interviewer is a realtime AI interview practice web app for the Southeast University AI+ Innovation Application Competition, Track 1: AI Agent Application Innovation. The app uses Alibaba Cloud Model Studio / Bailian as the primary AI platform, with Qwen-Omni-Realtime as the realtime interviewer, RAG over the user's resume and target job description, Function Calling tools for interview planning and scoring, and a post-interview ability tree that grows or regresses after each session.

The first MVP is a browser-based demo with a FastAPI backend. It must produce an accessible online link and be easy to record in a demo video.

## Competition Fit

The competition requires an AI Agent application that uses LLM, RAG, Function Calling, low-code or practical development on Alibaba Cloud Bailian, and solves a concrete pain point. This project fits those requirements as follows:

- LLM: Qwen-Omni-Realtime runs the realtime interviewer.
- RAG: Resume profile, QA bank, target JD, and prior interview notes are retrieved during planning and reporting.
- Function Calling: The system exposes tools for retrieving profile context, planning follow-up questions, scoring answers, updating the ability tree, and generating reports.
- Concrete pain point: Job candidates struggle to convert resume/project experience into confident, structured technical interview answers.
- Autonomous planning: The interviewer follows a state machine and adapts questions based on answers, weak skills, and target role requirements.
- Deliverables: The app produces a public demo link, a demo video workflow, technical documentation, and a project proposal.

## Input Materials

- Competition summary: `docs/competition-requirements.md`
- User profile: `data/profiles/豆瓣酱`
- Target JD: `data/job_descriptions/mechanical-arm-motion-control-algorithm-engineer.md`
- Reference architecture: `docs/architecture-proposal.md`
- Research notes: `docs/references.md`

## MVP Goals

1. Provide a realtime mock interview experience in the browser.
2. Keep Alibaba Bailian as the primary AI path.
3. Protect `DASHSCOPE_API_KEY` on the backend.
4. Use the copied user profile and target JD for interview personalization.
5. Demonstrate RAG and Function Calling clearly enough for judges to understand.
6. Generate a post-interview report with transcript, scores, weak points, and ability tree updates.
7. Keep public deployment pluggable so local development, tunnel demo, and formal cloud deployment use the same application core.

## Non-Goals For MVP

- Production user authentication with payments or organization management.
- Graph database deployment. Ability trees use JSON storage first.
- WebRTC production path. WebSocket is the first realtime integration; WebRTC remains a documented extension.
- Perfect frontend visual polish. External UI generation tools may provide drafts, but Codex reviews integration quality.
- Large-scale multi-user concurrency. MVP targets a small number of demo sessions.
- Automated ICP filing or domain purchase. The system only tracks publication state and provides deployment extension points.

## Users And Roles

### Candidate

The candidate uploads or selects a profile, chooses a target role, starts a mock interview, speaks with the AI interviewer, and reviews the post-interview report.

### Judge / Demo Viewer

The judge opens a public link, sees a guided demo-ready interface, can watch the realtime interview, and can inspect RAG / tool / ability-tree evidence.

### Developer

The developer runs the app locally, configures Bailian keys, tests mocked realtime behavior without external API access, and switches to live Qwen-Omni-Realtime for demo.

## Product Workflow

### 1. Preparation

The user selects the existing `豆瓣酱` profile and the target JD "机械臂运控算法工程师". The backend loads:

- `profile.json`
- `prompt.txt`
- `qa_bank.md`
- target JD markdown

The backend builds a session profile containing:

- candidate identity and education summary
- project and internship highlights
- domain skills
- target role requirements
- ability focus nodes

### 2. Realtime Interview

The browser opens a session and streams audio events to the backend. The backend connects to Qwen-Omni-Realtime via WebSocket and relays:

- client audio chunks
- optional client text events
- assistant text deltas
- assistant audio chunks when available
- transcript events
- tool-call events and tool results

The UI shows:

- virtual interviewer panel
- live transcript
- current interview stage
- RAG/tool activity indicators
- session controls: start, pause, stop, end interview

### 3. Interview State Machine

The session progresses through:

```text
warmup -> resume_overview -> project_deep_dive -> fundamentals
       -> pressure_followup -> candidate_questions -> summary
```

Each stage has:

- stage goal
- allowed question style
- scoring focus
- conditions for moving to the next stage

### 4. Tool-Enhanced Reasoning

The backend provides tool functions:

```text
retrieve_profile_context(query, user_id)
plan_next_question(stage, transcript, ability_focus)
score_answer(question, answer, rubric)
search_company_context(company, role)
update_ability_tree(user_id, interview_id)
generate_interview_report(user_id, interview_id)
```

The MVP can run these tools in service-layer orchestration even if the realtime model's Function Calling event shape changes. This keeps the demo stable and still demonstrates tool calling visibly in the UI.

### 5. Post-Interview Report

When the session ends, the backend generates a report containing:

- interview summary
- transcript
- answer scores
- strongest skill evidence
- weak or vague answers
- ability tree growth
- fading or unvalidated branches
- virtual branches from the target JD
- next practice plan

## Architecture

```text
Browser Web App
  - media capture
  - realtime session UI
  - transcript and report views
        |
        | WebSocket / HTTP
        v
FastAPI Backend
  - realtime gateway
  - interview state machine
  - tool router
  - RAG/profile loaders
  - scoring and report services
  - ability tree service
  - publication provider abstraction
        |
        | WebSocket / HTTP
        v
Alibaba Cloud Bailian
  - Qwen-Omni-Realtime
  - Function Calling
  - web_search / file_search extension points
```

## Repository Structure

```text
Virtual-Interviewer/
├── apps/
│   └── web/
├── services/
│   └── api/
├── data/
│   ├── profiles/
│   ├── job_descriptions/
│   ├── interviews/
│   └── ability_graphs/
├── docs/
│   ├── competition-requirements.md
│   ├── architecture-proposal.md
│   ├── references.md
│   └── superpowers/
│       ├── specs/
│       └── plans/
└── scripts/
```

## Backend Components

### FastAPI App

Responsible for app startup, CORS for local frontend, router registration, and health checks.

### Config

Reads environment variables:

```text
DASHSCOPE_API_KEY
BAILIAN_REALTIME_MODEL
BAILIAN_REALTIME_URL
APP_STORAGE_DIR
APP_PUBLIC_BASE_URL
```

The app fails fast when live realtime mode is requested without `DASHSCOPE_API_KEY`. Mock mode works without external keys.

### Realtime Gateway

Responsible for translating frontend events into backend session events and forwarding live events to Bailian.

Frontend-to-backend event types:

```json
{"type": "session.start", "profile_id": "豆瓣酱", "jd_id": "mechanical-arm-motion-control-algorithm-engineer"}
{"type": "audio.chunk", "mime_type": "audio/webm", "data": "<base64>"}
{"type": "text.input", "text": "请开始面试"}
{"type": "session.end"}
```

Backend-to-frontend event types:

```json
{"type": "session.ready", "session_id": "iv_..."}
{"type": "assistant.text.delta", "text": "你好，我们先..."}
{"type": "assistant.audio.chunk", "mime_type": "audio/mpeg", "data": "<base64>"}
{"type": "transcript.item", "speaker": "candidate", "text": "..."}
{"type": "tool.call", "name": "retrieve_profile_context", "arguments": {}}
{"type": "tool.result", "name": "retrieve_profile_context", "summary": "..."}
{"type": "session.ended", "interview_id": "int_..."}
```

### Interview State Machine

Responsible for selecting the current stage and next action. It is deterministic enough to test without an LLM.

Stage transition signals:

- time spent in stage
- number of questions asked
- answer score
- detected weak node
- explicit candidate question

### RAG/Profile Loaders

MVP loader reads local markdown and JSON. Later adapters can call Bailian `file_search`.

### Tool Router

Owns tool registration, validation, execution, and event logging. Tool results are returned in a compact summary suitable for realtime context injection.

### Scoring

Scores each answer across:

- relevance
- technical depth
- evidence quality
- structure
- communication clarity

Scores are numeric from 0 to 5 with textual rationale.

### Ability Tree

JSON-first graph model:

```json
{
  "user_id": "豆瓣酱",
  "skills": [],
  "projects": [],
  "evidence": [],
  "target_skills": [],
  "edges": [],
  "updated_at": "2026-06-24T00:00:00+08:00"
}
```

Node categories:

- current branch: supported by strong evidence
- weak branch: mentioned but poorly supported
- fading branch: stale or recently regressed
- virtual branch: required by target JD but not yet supported

## Frontend Components

### Pages

- Home / setup page
- Interview room
- Report page
- Ability tree page

### Interview Room

Displays:

- virtual interviewer
- recording status
- live transcript
- stage indicator
- RAG/tool activity feed
- controls

### Report View

Displays:

- summary
- score cards
- transcript
- ability tree visualization
- next practice plan

## Public Access And Deployment

The competition requires an online application link. MVP therefore includes a publication abstraction:

```text
LocalOnlyProvider
FrpProvider
CloudflareTunnelProvider
AliyunProvider
```

Implementation order:

1. Local dev only.
2. Manual tunnel or ECS deployment for demo.
3. Formal Aliyun deployment with domain and HTTPS.
4. ICP filing tracking when using a China mainland server and custom domain.

## Security

- Never expose `DASHSCOPE_API_KEY` to the browser.
- Store secrets in environment variables.
- Treat imported resumes and QA banks as private user data.
- Public demo mode should provide a sample profile option and avoid exposing sensitive phone/email fields.
- Tool calls must be allowlisted by backend code.
- Web search should be opt-in per session.

## Testing Strategy

### Unit Tests

- Config loading
- Profile and JD loader
- Local RAG retrieval
- Tool router validation
- State machine transitions
- Scoring schema
- Ability tree update logic
- Publication provider interfaces

### Integration Tests

- Mock realtime session through backend WebSocket
- End interview triggers report generation
- Report includes ability tree updates
- Frontend can start and stop a mocked session

### Manual Demo Tests

- Start app locally.
- Select profile and JD.
- Start mock interview.
- Verify live transcript events.
- End session.
- Verify report and ability tree.
- Switch to Bailian live mode when credentials are configured.

## Data Privacy For Imported Profile

The copied profile contains personal information. The app must support a demo-safe display mode that masks:

- phone number
- email
- precise location

The backend can still use profile content for interview context during private local development.

## Risks And Mitigations

### Bailian Realtime API Event Shape Changes

Mitigation: isolate Bailian code inside `integrations/bailian/omni_realtime.py` and support mock realtime mode.

### WebRTC Access Constraints

Mitigation: MVP uses WebSocket; WebRTC remains a separate adapter.

### Frontend Visual Quality

Mitigation: keep frontend component contracts clear so external UI drafts can be reviewed and integrated.

### Online Link Requirement

Mitigation: include publication provider abstraction and reserve time for tunnel/ECS deployment before demo recording.

### Ability Tree Scope Creep

Mitigation: use JSON graph first with limited node and edge types.

## Acceptance Criteria

- Local app starts with one command for backend and one command for frontend.
- User can select `豆瓣酱` profile and mechanical-arm JD.
- Mock realtime interview works without external API credentials.
- Live mode refuses to start without `DASHSCOPE_API_KEY`.
- Backend exposes a WebSocket session endpoint.
- Session events are recorded into `data/interviews`.
- Ending a session creates a report JSON and ability tree JSON.
- Report page displays scores, transcript, and ability tree changes.
- Tool calls are visible in the UI activity feed.
- Docs explain competition fit and deployment options.

## Spec Self-Review

- Placeholder scan: no unresolved placeholder markers remain in this spec.
- Scope check: MVP is one coherent subsystem set for a competition demo. Public deployment is included as an interface and documented path, not a full cloud automation project.
- Consistency check: Qwen-Omni-Realtime, WebSocket-first integration, post-interview ability tree, and public demo requirement are consistently reflected across goals, architecture, and acceptance criteria.

