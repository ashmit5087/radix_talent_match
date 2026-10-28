# RADIX Platform — Dev Server Script
# Starts all five backend services + the frontend in separate terminal windows.
# Usage:  .\scripts\dev.ps1
# Run setup.ps1 first to create the virtual environments.

param(
    [switch]$FrontendOnly,
    [switch]$BackendOnly
)

$Root = Split-Path $PSScriptRoot -Parent

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

# Detect available shell (pwsh = PowerShell 7, powershell = Windows PowerShell 5)
$Shell = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell" }

$services = @(
    @{
        Name    = "Role 1 — JD Analytics (port 8001)"
        Dir     = "services\role-1-jd-analytics"
        Cmd     = ".venv\Scripts\uvicorn.exe app.main:app --reload --port 8001 --host 0.0.0.0"
    },
    @{
        Name    = "Role 2 — Resume Parsing (port 8002)"
        Dir     = "services\role-2-resume-parsing"
        Cmd     = ".venv\Scripts\uvicorn.exe api_server:app --reload --port 8002 --host 0.0.0.0"
    },
    @{
        Name    = "Role 3 — Profile Builder (port 8003)"
        Dir     = "services\role-3-profile-builder"
        Cmd     = ".venv\Scripts\uvicorn.exe main:app --reload --port 8003 --host 0.0.0.0"
    },
    @{
        # Role 4 must run from the role-4-talent-check root (not the talent_check subdir)
        Name    = "Role 4 — Talent Check (port 8004)"
        Dir     = "services\role-4-talent-check"
        Cmd     = ".venv\Scripts\uvicorn.exe talent_check.backend.api:app --reload --port 8004 --host 0.0.0.0"
    },
    @{
        Name    = "Role 5 — Skill Matching (port 8005)"
        Dir     = "services\role-5-skill-matching"
        Cmd     = ".venv\Scripts\uvicorn.exe skill_matching.api:app --reload --port 8005 --host 0.0.0.0"
    }
)

if (-not $FrontendOnly) {
    foreach ($svc in $services) {
        Write-Step "Starting $($svc.Name)..."
        $svcPath = Join-Path $Root $svc.Dir
        if (-not (Test-Path $svcPath)) {
            Write-Host "    SKIP: Directory not found: $svcPath" -ForegroundColor Yellow
            continue
        }
        Start-Process $Shell -ArgumentList "-NoExit", "-Command", "Set-Location '$svcPath'; $($svc.Cmd)" -WindowStyle Normal
    }
}

if (-not $BackendOnly) {
    Write-Step "Starting Frontend (port 5173)..."
    $frontendPath = Join-Path $Root "frontend"
    if (Test-Path $frontendPath) {
        Start-Process $Shell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontendPath'; npm run dev -- --host 0.0.0.0 --port 5173" -WindowStyle Normal
    } else {
        Write-Host "    SKIP: frontend/ not found" -ForegroundColor Yellow
    }
}

Write-Host @"

All services launched in separate windows.
Service URLs:
  Frontend          http://localhost:5173
  Role 1 JD         http://localhost:8001/docs
  Role 2 Resume     http://localhost:8002/docs
  Role 3 Profile    http://localhost:8003/docs
  Role 4 Talent     http://localhost:8004/docs
  Role 5 Skills     http://localhost:8005/docs
  Diagnostics       http://localhost:5173/developer
"@ -ForegroundColor Green
