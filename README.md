# Virtual Interviewer

Realtime virtual interviewer for the Southeast University AI+ Innovation Application Competition.

The current project is a local-first interview practice app:

- Frontend: React + Vite interview UI.
- Backend: FastAPI WebSocket service.
- Realtime audio path: browser microphone -> 16 kHz PCM -> backend -> Alibaba Bailian Qwen-Omni-Realtime.
- Text path: low-cost local interviewer flow, preserved for users who cannot use microphones or do not want realtime audio cost.
- Post-interview path: mock report and ability-tree growth prototype.

## Repository Layout

```text
apps/web/                 Frontend app
services/api/             FastAPI backend
services/api/.env.example Safe Bailian config template
docs/issues.md            Historical issue log with diagnosis and fixes
docs/unresolved-issues.md Current unresolved problems and next actions
docs/progress.md          Progress report
data/job_descriptions/    Public JD placeholder
data/profiles/            Local private profile data, ignored by Git
```

## Prerequisites

- Windows PowerShell
- Python 3.11+
- Node.js 18+
- Alibaba Cloud Bailian / DashScope API key for live realtime mode

## Backend Setup

```powershell
cd <project-root>\services\api
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
```

Create local config from the example:

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill:

```env
DASHSCOPE_API_KEY=your-bailian-api-key
REALTIME_MODE=bailian
BAILIAN_REALTIME_MODEL=qwen3.5-omni-plus-realtime
BAILIAN_REALTIME_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime
```

Use `REALTIME_MODE=mock` if you want offline local development without calling Alibaba.

Start backend:

```powershell
cd <project-root>\services\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Expected:

```json
{"status":"ok"}
```

## Frontend Setup

```powershell
cd <project-root>\apps\web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173/
```

## Daily Run Commands

Terminal 1:

```powershell
cd <project-root>\services\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd <project-root>\apps\web
npm run dev -- --host 127.0.0.1 --port 5173
```

## How To Use

1. Open `http://127.0.0.1:5173/`.
2. Click `开始面试`.
3. Click `连接面试官`.
4. Text mode:
   - Type an answer in the textarea.
   - Click `发送模拟回答`.
   - The backend uses the local low-cost interviewer flow.
5. Audio mode:
   - Click `开始麦克风`.
   - Browser asks for microphone permission.
   - Audio is captured as 16 kHz PCM and streamed to the backend.
   - Backend forwards PCM chunks to Bailian Qwen-Omni-Realtime.
6. Click `结束并生成报告` to view the report prototype and ability tree.

## Current Mode Behavior

| Input | Current route | Cost profile | Notes |
| --- | --- | --- | --- |
| Text answer | Local low-cost interviewer | No Bailian realtime audio cost | Deterministic persona/state-machine follow-up. |
| Microphone | Bailian Qwen-Omni-Realtime | Uses realtime model | Needs browser microphone permission and API key. |
| Report | Local deterministic prototype | No external model call | Later can be upgraded with Bailian text model/RAG. |

## Verification

Backend:

```powershell
cd <project-root>\services\api
.\.venv\Scripts\pytest -q
```

Frontend:

```powershell
cd <project-root>\apps\web
npm run build
```

Last known verification:

- Backend: 43 tests passed.
- Frontend: production build succeeded.

## Restart Backend After `.env` Changes

If port `8000` is already occupied:

```powershell
$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $listeners) {
  $ownerPid = $conn.OwningProcess
  if ($ownerPid) { Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue }
}
cd <project-root>\services\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Privacy

Do not commit real resume/profile files or API keys.

Ignored local files include:

- `services/api/.env`
- `data/profiles/*`
- runtime reports under `data/interviews/`
- generated ability graphs under `data/ability_graphs/`

Use `services/api/.env.example` as the safe public template.

## Project Docs

- [Progress report](docs/progress.md)
- [Historical issue log](docs/issues.md)
- [Current unresolved issues](docs/unresolved-issues.md)
- [Architecture proposal](docs/architecture-proposal.md)
- [Competition requirements](docs/competition-requirements.md)

