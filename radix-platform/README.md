# RADIX Talent Match — Integrated Platform

A production-ready, fully integrated monorepo connecting five specialised backend services with the RADIX Talent Match frontend. Candidates can upload a resume, build a profile, analyse job descriptions, check company readiness, and see a detailed skill-match report — all through one unified interface.

---

## Architecture

```
radix-platform/
├── frontend/                    ← React 19 + Vite 7 + Tailwind CSS 4
│   └── src/services/            ← Typed API clients for all 5 services
├── services/
│   ├── role-1-jd-analytics/     ← FastAPI · Port 8001 · Gemini + ChromaDB
│   ├── role-2-resume-parsing/   ← FastAPI · Port 8002 · Groq LLM (NEW adapter)
│   ├── role-3-profile-builder/  ← FastAPI · Port 8003 · Supabase/in-memory
│   ├── role-4-talent-check/     ← FastAPI · Port 8004 · Deterministic scoring
│   └── role-5-skill-matching/   ← FastAPI · Port 8005 · Deterministic matching
├── contracts/                   ← Endpoint inventory and data-flow docs
├── scripts/
│   ├── setup.ps1                ← Install all dependencies
│   └── dev.ps1                  ← Launch all services in parallel
└── docker-compose.yml           ← Single-command stack
```

---

## End-to-End User Flows

### Flow 1 — Resume Upload → Profile → Skill Match
1. Navigate to **Resume** (`/app/resume`)
2. Upload a PDF or DOCX — Role 2 (Groq) extracts skills, education, projects
3. Click **Create profile from result** — Role 3 stores the profile
4. Go to **Skill Matching** — select the profile ID and an analyzed JD
5. View match score, gap analysis, and improvement plan

### Flow 2 — Manual Profile → Talent Check
1. Navigate to **Create profile** (`/app/profile/new`)
2. Fill in personal details and skills — click **Save profile to Role 3**
3. Go to **Talent Check** — search for a company, load the profile
4. Run readiness assessment — see score, critical gaps, focus areas

### Flow 3 — JD Analysis → Skill Match
1. Navigate to **JD Analytics** → **Analyze a JD**
2. Upload a PDF or DOCX job description — Role 1 extracts required skills
3. Return to **Skill Matching** — the JD appears in the dropdown
4. Select a profile and run the comparison

---

## Quick Start (Local Development)

### 1 — Prerequisites
- Python ≥ 3.11
- Node.js ≥ 20
- PowerShell 7 (pwsh)

### 2 — Install dependencies
```powershell
cd radix-platform
.\scripts\setup.ps1
```

### 3 — Configure secrets
Edit `.env` in each service directory:
| Service | Required keys |
|---------|--------------|
| `role-1-jd-analytics` | `GEMINI_API_KEY` |
| `role-2-resume-parsing` | `GROQ_API_KEY` |
| `role-3-profile-builder` | `SUPABASE_URL`, `SUPABASE_ANON_KEY` (optional — falls back to in-memory) |
| `role-4-talent-check` | none |
| `role-5-skill-matching` | none |

Also edit `frontend/.env`:
```env
VITE_JD_API_BASE_URL=http://localhost:8001
VITE_RESUME_API_BASE_URL=http://localhost:8002
VITE_PROFILE_API_BASE_URL=http://localhost:8003
VITE_TALENT_CHECK_API_BASE_URL=http://localhost:8004
VITE_SKILL_MATCH_API_BASE_URL=http://localhost:8005
VITE_PROFILE_CONTRACT_CONFIRMED=true
```

### 4 — Start all services
```powershell
.\scripts\dev.ps1
```

### 5 — Open the app
| URL | Description |
|-----|-------------|
| http://localhost:5173 | Frontend |
| http://localhost:5173/developer | Health diagnostics (all 5 services) |
| http://localhost:8001/docs | Role 1 JD Analytics API docs |
| http://localhost:8002/docs | Role 2 Resume Parsing API docs |
| http://localhost:8003/docs | Role 3 Profile Builder API docs |
| http://localhost:8004/docs | Role 4 Talent Check API docs |
| http://localhost:8005/docs | Role 5 Skill Matching API docs |

---

## Docker (Single Command)

```bash
cp .env.example .env   # fill in GEMINI_API_KEY, GROQ_API_KEY
docker-compose up --build
```

---

## Service API Summary

| Role | Service | Port | Key Endpoints |
|------|---------|------|---------------|
| 1 | JD Analytics | 8001 | `POST /api/v1/jds/analyze`, `GET /api/v1/jds`, `POST /api/v1/jds/search` |
| 2 | Resume Parsing | 8002 | `POST /api/v1/resumes/parse` (**new**), `GET /health` |
| 3 | Profile Builder | 8003 | `POST /api/v1/profiles`, `GET /api/v1/profiles/{id}`, `GET /api/v1/profiles/{id}/completeness` |
| 4 | Talent Check | 8004 | `GET /api/companies`, `POST /api/talent-check`, `POST /api/talent-check/direct` |
| 5 | Skill Matching | 8005 | `POST /api/v1/matches`, `POST /api/v1/improvement-plan` |

---

## What Was Built in This Integration

| Component | Status | Notes |
|-----------|--------|-------|
| Role 2 HTTP adapter (`api_server.py`) | ✅ New | Wraps CLI parser as FastAPI; no logic duplicated |
| Cross-role schema adapters (`adapters.ts`) | ✅ New | Role 2→3, Role 3→4, Role 3+1→5 type-safe mappings |
| Resume page — live parsing | ✅ Integrated | Calls Role 2, shows extracted skills, creates Role 3 profile |
| Profile wizard — live save | ✅ Ungated | Calls Role 3 `POST /api/v1/profiles`; shows saved ID |
| Talent Check page | ✅ Implemented | Company search, profile load, readiness score + gaps |
| Developer diagnostics | ✅ Expanded | Pings all 5 `/health` endpoints |
| Frontend `.env.example` | ✅ Complete | All 5 service URLs with correct ports |
| Setup script (`setup.ps1`) | ✅ New | Venv + npm install for all services |
| Dev launcher (`dev.ps1`) | ✅ New | Opens all services in parallel terminal windows |
| `docker-compose.yml` | ✅ New | Full stack via single command |
| Role 2 `requirements.txt` | ✅ Updated | Added `fastapi`, `uvicorn`, `python-multipart` |

---

## Integration Architecture Diagram

```
Browser (http://localhost:5173)
  │
  ├── /app/resume ──────── POST /api/v1/resumes/parse ──► Role 2 (Groq)
  │                                    │ ResumeExtract
  │                                    ▼
  │                         POST /api/v1/profiles ──────► Role 3 (Supabase)
  │
  ├── /app/jds ────────── POST /api/v1/jds/analyze ────► Role 1 (Gemini+ChromaDB)
  │
  ├── /app/talent-check ─ GET  /api/companies ──────────► Role 4 (deterministic)
  │                        POST /api/talent-check
  │
  └── /app/skill-matching  GET  /api/v1/profiles/{id} ──► Role 3
                           GET  /api/v1/jds/{id} ─────────► Role 1
                           POST /api/v1/matches ─────────► Role 5 (deterministic)
                           POST /api/v1/improvement-plan ► Role 5
```

---

## Repository Layout (Original → Integrated)

```
role-1/  →  radix-platform/services/role-1-jd-analytics/
role-2/  →  radix-platform/services/role-2-resume-parsing/ + api_server.py (NEW)
role-3/backend/  →  radix-platform/services/role-3-profile-builder/
role-3/RADIX-Talent-Match/artifacts/radix-talent-match/  →  radix-platform/frontend/
role-4/  →  radix-platform/services/role-4-talent-check/
role-5/apps/skill_matching/  →  radix-platform/services/role-5-skill-matching/
```

Original role folders remain untouched.
