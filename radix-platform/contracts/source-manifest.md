# RADIX Platform — Source Manifest

Definitive map of every source file in the integrated platform and its purpose.

---

## Frontend (`radix-platform/frontend/`)

### Routes (`src/routes/`)
| File | Route | Purpose |
|------|-------|---------|
| `__root.tsx` | `/` | Root layout — sidebar, nav, theme |
| `index.tsx` | `/` | Landing / hero page |
| `onboarding.tsx` | `/onboarding` | Resume upload → profile creation flow |
| `app.tsx` | `/app` | Authenticated app shell (sidebar layout) |
| `app.dashboard.tsx` | `/app/dashboard` | Dashboard overview |
| `app.resume.tsx` | `/app/resume` | Resume upload + parsed skills view |
| `app.profile.new.tsx` | `/app/profile/new` | Manual profile wizard |
| `app.jds.tsx` | `/app/jds` | JD list + analyze new JD |
| `app.talent-check.tsx` | `/app/talent-check` | Company search + readiness check |
| `app.skill-matching.tsx` | `/app/skill-matching` | Profile vs JD skill match |
| `app.assessments.tsx` | `/app/assessments` | Assessment list |
| `app.assessments.new.tsx` | `/app/assessments/new` | **New assessment wizard (Role 1+4+5)** |
| `app.assessments.$assessmentId.tsx` | `/app/assessments/:id` | Assessment detail + results |
| `app.settings.tsx` | `/app/settings` | Service health diagnostics |
| `developer.tsx` | `/developer` | Developer diagnostics page |

### API Layer (`src/lib/radix/`)
| File | Purpose |
|------|---------|
| `services.ts` | All 5 role API call functions + typed request/response shapes |
| `contracts.ts` | Shared TypeScript interfaces (`CandidateProfile`, `AssessmentRecord`, `MatchResult`, `ImprovementPlan`, `Completeness`) |
| `session.ts` | Module-level closures for cross-route state (avoids TanStack Router split-bundle immutable import errors) |
| `mock.ts` | Demo profile and fixture data for offline/demo mode |

### UI Components
| File | Purpose |
|------|---------|
| `src/components/radix/ui.tsx` | RADIX-specific UI components (`PageHeader`, `ScoreRing`, etc.) |
| `src/components/ui/` | shadcn/ui primitives (Button, Input, Card, Dialog, etc.) |

### Config
| File | Purpose |
|------|---------|
| `vite.config.ts` | Vite + TanStack Start + Nitro SSR config |
| `tsconfig.json` | TypeScript strict config with `@/` path alias |
| `vitest.config.ts` | Unit test config |
| `.env.example` | Template for all 5 `VITE_*_API_URL` env vars |

---

## Role 1 — JD Analytics (`radix-platform/services/role-1-jd-analytics/`)

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application entry point |
| `app/config.py` | Settings (GEMINI_API_KEY, ChromaDB path) |
| `app/schemas.py` | Pydantic request/response models |
| `app/errors.py` | Custom HTTP exception handlers |
| `app/api/` | Route handlers for `/api/v1/jds/*` |
| `app/services/` | Business logic: Gemini extraction, ChromaDB indexing |
| `app/utils/` | File parsing utilities (PDF, DOCX) |
| `requirements.txt` | Python dependencies |

---

## Role 2 — Resume Parsing (`radix-platform/services/role-2-resume-parsing/`)

| File | Purpose |
|------|---------|
| `api_server.py` | **NEW** FastAPI adapter — wraps CLI pipeline as REST service on port 8002 |
| `parse_resume.py` | Entry-point CLI: orchestrates extraction pipeline |
| `extract.py` | Groq LLM skill extraction logic |
| `read_file.py` | PDF/DOCX text extraction (pdfplumber, python-docx) |
| `schema.py` | Pydantic output models |
| `check_output.py` | Output validation utilities |
| `requirements.txt` | Python dependencies (includes fastapi, uvicorn added for adapter) |

---

## Role 3 — Profile Builder (`radix-platform/services/role-3-profile-builder/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI application entry point (port 8003) |
| `app/` | Route handlers, business logic, Supabase integration |
| `database/` | DB connection, schema definitions |
| `mock_data/` | Sample profiles for testing |
| `uploads/` | CV file storage (local) |
| `tests/` | pytest test suite |
| `requirements.txt` | Python dependencies |

---

## Role 4 — Talent Check (`radix-platform/services/role-4-talent-check/`)

| File | Purpose |
|------|---------|
| `talent_check/backend/api.py` | FastAPI service — companies, talent-check, health endpoints |
| `talent_check/backend/scoring.py` | Asymptotic saturating curve scoring engine (k=4.0) |
| `talent_check/backend/levels.py` | Skill → 12-category level mapping + evidence point accumulator |
| `talent_check/backend/loader.py` | companies.json loader |
| `talent_check/data/` | `companies.json` — 115 enterprise company benchmarks |
| `talent_check/cli.py` | Interactive terminal CLI |
| `companies.json` | Root-level alias to data file |
| `requirements.txt` | Python dependencies |

---

## Role 5 — Skill Matching (`radix-platform/services/role-5-skill-matching/`)

| File | Purpose |
|------|---------|
| `src/skill_matching/api.py` | FastAPI service — `/api/v1/matches`, `/api/v1/improvement-plan` |
| `src/skill_matching/matcher.py` | Core deterministic skill matching algorithm |
| `src/skill_matching/scorer.py` | Weighted score computation (0–100) |
| `src/skill_matching/normalizer.py` | Skill name canonicalization |
| `src/skill_matching/aliases.py` | Skill synonym/alias dictionary |
| `src/skill_matching/recommendations.py` | Improvement plan generator |
| `src/skill_matching/llm_plan.py` | Optional LLM-enhanced plan advisory |
| `src/skill_matching/talent_check.py` | Role 4 integration adapter |
| `src/skill_matching/schemas.py` | Pydantic models |
| `src/skill_matching/config.py` | Settings (optional OpenAI key for LLM plan) |
| `src/skill_matching/cli.py` | CLI entry point |
| `tests/` | pytest test suite |
| `pyproject.toml` | Project metadata + dependency spec |

---

## Shared Infrastructure (`radix-platform/`)

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full stack container orchestration |
| `.env.example` | Platform-level environment template |
| `scripts/setup.ps1` | One-time install: venvs + npm |
| `scripts/dev.ps1` | Launch all 5 services + frontend |
| `contracts/api-contracts.md` | Combined API contract reference |
| `contracts/endpoint-inventory.md` | **This repo** — all endpoints listed |
| `contracts/integration-matrix.md` | Role-to-role communication map |
| `contracts/data-flow.md` | End-to-end data flow diagrams |
| `contracts/schema-mapping.md` | Cross-role type transformation reference |
| `contracts/source-manifest.md` | **This file** — complete source index |
| `contracts/integration-test-cases.md` | Test scenarios for QA |

