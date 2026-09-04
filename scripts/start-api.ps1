param(
    [switch]$Check,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$BackendRoot = Join-Path $Root "services\api"
$FrontendRoot = Join-Path $Root "apps\web"
$EnvPath = Join-Path $BackendRoot ".env"
$EnvExamplePath = Join-Path $BackendRoot ".env.example"
$RuntimeRoot = Join-Path $Root ".runtime"
$LogRoot = Join-Path $Root "logs"
$StatePath = Join-Path $RuntimeRoot "api-mode.json"
$BackendHealthUrl = "http://127.0.0.1:8000/api/health"
$FrontendUrl = "http://127.0.0.1:5173/"
$StartedProcesses = @()

function Test-HttpEndpoint {
    param([string]$Uri)
    try {
        $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Test-PortInUse {
    param([int]$Port)
    return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Wait-ForEndpoint {
    param(
        [string]$Uri,
        [int]$TimeoutSeconds = 60
    )
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-HttpEndpoint $Uri) {
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Timed out waiting for $Uri. Check logs in $LogRoot."
}

function Get-DotEnvValue {
    param([string]$Name)
    $escapedName = [regex]::Escape($Name)
    $line = Get-Content -LiteralPath $EnvPath | Where-Object { $_ -match "^\s*$escapedName\s*=" } | Select-Object -First 1
    if (-not $line) {
        return ""
    }
    return (($line -split '=', 2)[1]).Trim().Trim('"').Trim("'")
}

function Assert-ApiModeConfigured {
    $apiKey = Get-DotEnvValue "DASHSCOPE_API_KEY"
    if (-not $apiKey -or $apiKey -match 'replace-with|your-bailian|你的百炼') {
        throw "Set DASHSCOPE_API_KEY in $EnvPath, then run start-api.cmd again."
    }
    if ((Get-DotEnvValue "REALTIME_MODE") -ne "bailian") {
        throw "Set REALTIME_MODE=bailian in $EnvPath for API mode."
    }
}

function Add-StartedProcess {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Name
    )
    $script:StartedProcesses += [ordered]@{
        name = $Name
        pid = $Process.Id
        started_at_utc = $Process.StartTime.ToUniversalTime().ToString("o")
    }
}

try {
    if (-not (Test-Path -LiteralPath $EnvPath)) {
        Copy-Item -LiteralPath $EnvExamplePath -Destination $EnvPath
        throw "Created $EnvPath. Add your Bailian API key, then run start-api.cmd again."
    }
    Assert-ApiModeConfigured

    $npm = Get-Command npm.cmd -ErrorAction Stop
    $VenvPython = Join-Path $BackendRoot ".venv\Scripts\python.exe"
    $NodeModules = Join-Path $FrontendRoot "node_modules"

    if ($Check) {
        if (-not (Test-Path -LiteralPath $VenvPython)) {
            throw "Backend virtual environment is missing. Run start-api.cmd once to create it."
        }
        if (-not (Test-Path -LiteralPath $NodeModules)) {
            throw "Frontend dependencies are missing. Run start-api.cmd once to install them."
        }
        & $VenvPython -c "import fastapi, uvicorn"
        if ($LASTEXITCODE -ne 0) {
            throw "Backend dependencies are incomplete. Run start-api.cmd to install them."
        }
        Write-Host "API mode configuration and dependencies are ready."
        exit 0
    }

    if (-not (Test-Path -LiteralPath $VenvPython)) {
        $systemPython = Get-Command python.exe -ErrorAction Stop
        Write-Host "Creating backend virtual environment..."
        & $systemPython.Source -m venv (Join-Path $BackendRoot ".venv")
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create the backend virtual environment."
        }
    }

    & $VenvPython -c "import fastapi, uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing backend dependencies..."
        Push-Location $BackendRoot
        try {
            & $VenvPython -m pip install -e ".[dev]"
            if ($LASTEXITCODE -ne 0) {
                throw "Backend dependency installation failed."
            }
        }
        finally {
            Pop-Location
        }
    }

    if (-not (Test-Path -LiteralPath $NodeModules)) {
        Write-Host "Installing frontend dependencies..."
        Push-Location $FrontendRoot
        try {
            & $npm.Source install
            if ($LASTEXITCODE -ne 0) {
                throw "Frontend dependency installation failed."
            }
        }
        finally {
            Pop-Location
        }
    }

    New-Item -ItemType Directory -Path $RuntimeRoot, $LogRoot -Force | Out-Null

    if (Test-HttpEndpoint $BackendHealthUrl) {
        Write-Host "Backend is already healthy on port 8000; reusing it."
    }
    else {
        if (Test-PortInUse 8000) {
            throw "Port 8000 is occupied by another service. Stop it or change the project port."
        }
        $backend = Start-Process -FilePath $VenvPython `
            -ArgumentList @("-m", "uvicorn", "app.main:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000") `
            -WorkingDirectory $BackendRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $LogRoot "backend.out.log") `
            -RedirectStandardError (Join-Path $LogRoot "backend.err.log") `
            -PassThru
        Add-StartedProcess $backend "backend"
        Wait-ForEndpoint $BackendHealthUrl
        Write-Host "Backend is ready."
    }

    if (Test-HttpEndpoint $FrontendUrl) {
        Write-Host "Frontend is already healthy on port 5173; reusing it."
    }
    else {
        if (Test-PortInUse 5173) {
            throw "Port 5173 is occupied by another service. Stop it or change the project port."
        }
        $frontend = Start-Process -FilePath $npm.Source `
            -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") `
            -WorkingDirectory $FrontendRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $LogRoot "frontend.out.log") `
            -RedirectStandardError (Join-Path $LogRoot "frontend.err.log") `
            -PassThru
        Add-StartedProcess $frontend "frontend"
        Wait-ForEndpoint $FrontendUrl
        Write-Host "Frontend is ready."
    }

    if ($StartedProcesses.Count -gt 0) {
        [ordered]@{
            root = $Root
            processes = $StartedProcesses
        } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatePath -Encoding UTF8
    }

    Write-Host "Virtual Interviewer API mode is ready: $FrontendUrl"
    if (-not $NoBrowser) {
        Start-Process $FrontendUrl
    }
}
catch {
    foreach ($entry in $StartedProcesses) {
        Stop-Process -Id $entry.pid -Force -ErrorAction SilentlyContinue
    }
    Write-Error $_
    exit 1
}
