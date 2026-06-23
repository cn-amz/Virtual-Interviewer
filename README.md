# Virtual Interviewer

Realtime virtual interviewer for the Southeast University AI+ Innovation Application Competition.

## MVP

- Web frontend for interview setup, realtime mock interview, and report review.
- FastAPI backend for profile/JD loading, tool routing, scoring, reports, and ability tree updates.
- Alibaba Bailian Qwen-Omni-Realtime integration point, with mock mode for local development.

## Current Status

See [docs/progress.md](docs/progress.md).

## Local Development

Backend:

```powershell
cd services/api
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd apps/web
npm install
npm run dev
```

Open `http://localhost:5173`.

## Privacy

Private profile and resume files are kept out of Git. See [docs/data-privacy.md](docs/data-privacy.md).

