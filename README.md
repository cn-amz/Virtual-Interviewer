# Virtual Interviewer

Realtime virtual interviewer for the Southeast University AI+ Innovation Application Competition.

Chinese usage guide: [README_CN.md](README_CN.md).

The current project is a local-first interview practice app:

- Frontend: React + Vite interview UI.
- Backend: FastAPI WebSocket service.
- Audio path: browser microphone -> 16 kHz PCM -> backend -> Alibaba Bailian Qwen-Omni-Realtime.
- Text path: configurable local interviewer or Alibaba Bailian text model.
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
- Alibaba Cloud Bailian / DashScope API key

## Backend Setup

```powershell
cd <project-root>\services\api
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
```

Create local config:

```powershell
Copy-Item .env.example .env
notepad .env
```

Required `.env` values:

```env
DASHSCOPE_API_KEY=your-bailian-api-key
REALTIME_MODE=bailian
BAILIAN_REALTIME_MODEL=qwen3.5-omni-plus-realtime
BAILIAN_REALTIME_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime
TEXT_MODE=bailian_text
BAILIAN_TEXT_MODEL=qwen3.6plus
BAILIAN_TEXT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

Use `REALTIME_MODE=mock` for offline development. Use `TEXT_MODE=local` when typed practice should avoid Alibaba text model cost.

Start backend:

```powershell
cd <project-root>\services\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

## Frontend Setup

```powershell
cd <project-root>\apps\web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173/`.

## How To Use

1. Open `http://127.0.0.1:5173/`.
2. Click `开始面试`.
3. Click `连接面试官`.
4. Text mode:
   - Type an answer in the textarea.
   - Click `发送模拟回答`.
   - With `TEXT_MODE=bailian_text`, typed answers are sent to Alibaba Bailian text chat completions.
   - With `TEXT_MODE=local`, typed answers use the local low-cost interviewer.
5. Audio mode:
   - Click `开始麦克风`.
   - Browser asks for microphone permission.
   - Audio is captured as 16 kHz PCM and streamed to the backend.
   - Backend forwards PCM chunks to Bailian Qwen-Omni-Realtime.
6. Click `结束并生成报告` to view the report prototype and ability tree.

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

## Privacy Notes

- Do not commit `services/api/.env`.
- Do not commit real API keys.
- Do not commit private resume/profile files unless they are intentionally sanitized.
- Local private profile data under `data/profiles/` is ignored by Git.
