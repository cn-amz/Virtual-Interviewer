# Virtual Interviewer

[简体中文](README_CN.md) | English

Realtime virtual interviewer for the Southeast University AI+ Innovation Application Competition.

Windows Bailian API quick start: configure `services/api/.env`, then double-click `start-api.cmd`. See [docs/bailian-api-setup.md](docs/bailian-api-setup.md) for API-key security, model configuration, startup, and troubleshooting. API mode does not require Docker or MiniCPM.

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
data/interview_job_descriptions/  Interview-only JD snapshots, ignored by Git
data/interview_profiles/          Interview-only profile snapshots, ignored by Git
data/profiles/                    Resume optimization and fine-tuning source data, not runtime resume input
```

## Prerequisites

- Windows PowerShell
- Python 3.11+
- Node.js 18+
- Alibaba Cloud Bailian / DashScope API key

## Backend Setup

```powershell
Set-Location -LiteralPath '.\services\api'
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
BAILIAN_TEXT_MODEL=qwen3.6-plus
BAILIAN_TEXT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

Use `REALTIME_MODE=mock` for offline development. Use `TEXT_MODE=local` when typed practice should avoid Alibaba text model cost.

Start backend:

```powershell
Set-Location -LiteralPath '.\services\api'
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

## Frontend Setup

```powershell
Set-Location -LiteralPath '.\apps\web'
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
Set-Location -LiteralPath '.\services\api'
.\.venv\Scripts\pytest -q
```

Frontend:

```powershell
Set-Location -LiteralPath '.\apps\web'
npm run build
```

## Privacy Notes

- Do not commit `services/api/.env`.
- Do not commit real API keys.
- Do not commit private resume/profile files unless they are intentionally sanitized.
- The interview runtime reads private snapshots from `data/interview_profiles/` and `data/interview_job_descriptions/`.
- The source database under `data/profiles/` is ignored by Git and is not used as the runtime resume.

## License

This project is licensed under the [MIT License](LICENSE).
