# RADIX Candidate Assessment Platform

The integrated RADIX Talent Match hackathon project.

The active application is under [`radix-platform/`](radix-platform/). The unused
root-level source folder is intentionally left on disk but excluded from version
control.

## Start locally

```powershell
Set-Location .\radix-platform
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\scripts\setup.ps1
.\scripts\dev.ps1
```

Open `http://localhost:5173`.

## Documentation

See [`radix-platform/HACKATHON_MASTER_GUIDE.md`](radix-platform/HACKATHON_MASTER_GUIDE.md)
for the architecture, five-role ownership plan, API flow, database model, demo
script, and judge-facing presentation material.
