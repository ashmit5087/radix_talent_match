# RADIX Platform — Windows Developer Setup Script
# Run this once to install all dependencies for all services and the frontend.
# Usage:  .\scripts\setup.ps1
# Requires: Python >= 3.11, Node >= 20, pip, npm

param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }

Write-Host "`nRADIX Platform Setup" -ForegroundColor Magenta
Write-Host "Root: $Root`n"

# ─── Backend services ───────────────────────────────────────────────────────
if (-not $SkipBackend) {

    $services = @(
        @{ Name = "role-1-jd-analytics";    Dir = "services\role-1-jd-analytics";    Entry = "app.main:app" },
        @{ Name = "role-2-resume-parsing";   Dir = "services\role-2-resume-parsing";   Entry = "api_server:app" },
        @{ Name = "role-3-profile-builder";  Dir = "services\role-3-profile-builder";  Entry = "main:app" },
        @{ Name = "role-4-talent-check";     Dir = "services\role-4-talent-check";     Entry = "" },
        @{ Name = "role-5-skill-matching";   Dir = "services\role-5-skill-matching";   Entry = "" }
    )

    foreach ($svc in $services) {
        Write-Step "Setting up $($svc.Name)..."
        $svcPath = Join-Path $Root $svc.Dir

        if (-not (Test-Path $svcPath)) {
            Write-Warn "Directory not found: $svcPath — skipping"
            continue
        }

        $venvPath = Join-Path $svcPath ".venv"
        if (-not (Test-Path $venvPath)) {
            Write-Host "    Creating venv in $venvPath..."
            python -m venv $venvPath
        }

        $pip = Join-Path $venvPath "Scripts\pip.exe"
        $reqFile = Join-Path $svcPath "requirements.txt"
        $pyprojectFile = Join-Path $svcPath "pyproject.toml"

        if (Test-Path $reqFile) {
            & $pip install -r $reqFile --quiet
            if ($LASTEXITCODE -ne 0) {
                throw "pip install failed for $($svc.Name)"
            }
            Write-Ok "pip install complete for $($svc.Name)"
        } elseif (Test-Path $pyprojectFile) {
            $python = Join-Path $venvPath "Scripts\python.exe"
            Push-Location $svcPath
            try {
                $extras = if ($svc.Name -eq "role-5-skill-matching") { ".[dev,llm]" } else { ".[dev]" }
                & $python -m pip install -e $extras --quiet
                if ($LASTEXITCODE -ne 0) {
                    throw "pip editable install failed for $($svc.Name)"
                }
            } finally {
                Pop-Location
            }
            Write-Ok "pip install (editable) complete for $($svc.Name)"
        } else {
            Write-Warn "No requirements.txt or pyproject.toml in $svcPath"
        }
    }

    # Copy env templates if no .env exists
    Write-Step "Checking .env files..."
    foreach ($svc in $services) {
        $svcPath = Join-Path $Root $svc.Dir
        $envExample = Join-Path $svcPath ".env.example"
        $envFile    = Join-Path $svcPath ".env"
        if ((Test-Path $envExample) -and (-not (Test-Path $envFile))) {
            Copy-Item $envExample $envFile
            Write-Warn "Copied .env.example → .env for $($svc.Name) — edit before starting"
        }
    }
}

# ─── Frontend ────────────────────────────────────────────────────────────────
if (-not $SkipFrontend) {
    Write-Step "Setting up frontend..."
    $frontendPath = Join-Path $Root "frontend"

    if (-not (Test-Path $frontendPath)) {
        Write-Warn "frontend/ directory not found — skipping"
    } else {
        Push-Location $frontendPath
        npm install
        Pop-Location
        Write-Ok "npm install complete for frontend"

        # Copy .env if not present
        $envExample = Join-Path $frontendPath ".env.example"
        $envFile    = Join-Path $frontendPath ".env"
        if ((Test-Path $envExample) -and (-not (Test-Path $envFile))) {
            Copy-Item $envExample $envFile
            Write-Warn "Copied .env.example → .env for frontend — edit service URLs before starting"
        }
    }
}

Write-Host "`nSetup complete. Run .\scripts\dev.ps1 to start all services." -ForegroundColor Green
