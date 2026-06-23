param(
    [ValidateSet("backend", "frontend")]
    [string]$Target = "backend"
)

$Root = Split-Path -Parent $PSScriptRoot

if ($Target -eq "backend") {
    Set-Location "$Root\services\api"
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
    }
    .\.venv\Scripts\pip install -e ".[dev]"
    .\.venv\Scripts\uvicorn app.main:app --reload --port 8000
}

if ($Target -eq "frontend") {
    Set-Location "$Root\apps\web"
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    npm run dev
}
