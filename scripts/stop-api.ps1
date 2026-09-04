$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$StatePath = Join-Path $Root ".runtime\api-mode.json"

if (-not (Test-Path -LiteralPath $StatePath)) {
    Write-Host "No API-mode process record was found. Nothing was stopped."
    exit 0
}

$state = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
foreach ($entry in $state.processes) {
    $process = Get-Process -Id $entry.pid -ErrorAction SilentlyContinue
    if (-not $process) {
        continue
    }
    $actualStart = $process.StartTime.ToUniversalTime().ToString("o")
    if ($actualStart -ne $entry.started_at_utc) {
        Write-Warning "Skipped PID $($entry.pid): it has been reused by another process."
        continue
    }
    & taskkill.exe /PID $entry.pid /T /F | Out-Null
    Write-Host "Stopped $($entry.name) (PID $($entry.pid))."
}

Remove-Item -LiteralPath $StatePath -Force
