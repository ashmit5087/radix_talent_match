# RADIX Platform — Integration Matrix

Which roles talk to which, and through what mechanism.

---

## Service Communication Map

| Caller | Called | Trigger | Data Exchanged |
|--------|--------|---------|----------------|
| **Frontend** | Role 1 (JD Analytics) | User uploads JD file | `POST /api/v1/jds/analyze` → `JDAnalysis` |
| **Frontend** | Role 2 (Resume Parsing) | User uploads resume | `POST /api/v1/resumes/parse` → `ResumeExtract` |
| **Frontend** | Role 3 (Profile Builder) | User saves profile | `POST /api/v1/profiles` → `ProfileResponse` |
| **Frontend** | Role 3 (Profile Builder) | User fetches profile | `GET /api/v1/profiles/{id}` → `ProfileResponse` |
| **Frontend** | Role 4 (Talent Check) | User searches company | `GET /api/companies?q=` → `Company[]` |
| **Frontend** | Role 4 (Talent Check) | User runs talent check | `POST /api/talent-check` → `TalentCheckResult` |
| **Frontend** | Role 5 (Skill Matching) | User runs skill match | `POST /api/v1/matches` → `MatchResult` |
| **Frontend** | Role 5 (Skill Matching) | User runs skill match | `POST /api/v1/improvement-plan` → `ImprovementPlan` |
| **Frontend** | All 5 services | Settings health check | `GET /{healthPath}` → status |

> **Note:** All integration is frontend-orchestrated. Services do **not** call each other directly. The browser composes multi-role flows.

---

## Integration Dependency Graph

```
User Action
    │
    ├─▶ Upload Resume ──▶ Role 2 ─────────────────────────────────────┐
    │                                                                  │
    │                   ResumeExtract (skills, education, projects)   │
    │                                                                  ▼
    ├─▶ Save Profile ──────────────────────────────────────────▶ Role 3
    │                                                            ProfileResponse (profile_id)
    │
    ├─▶ Upload JD ──────▶ Role 1 ─────────────────────────────────────┐
    │                                                                  │
    │                   JDAnalysis (skills, role, company)            │
    │                                                                  │
    │                                          ┌───────────────────────┘
    │                                          │
    ├─▶ Search Company ──▶ Role 4 ─────────────┤
    │                   Company[]              │
    │                                          │
    ├─▶ Talent Check ──▶ Role 4 ───────────────┤
    │                   TalentCheckResult      │
    │                                          ▼
    └─▶ Run Match ──────────────────────▶ Role 5
                         MatchResult + ImprovementPlan
```

---

## Data Adapter Layer (`services.ts`)

Cross-role type conversion is handled in `radix-platform/frontend/src/lib/radix/services.ts`:

| Adapter | From → To | Function |
|---------|-----------|----------|
| Role 2 → Role 3 | `ResumeExtract` → `ProfileCreate` | `resumeToProfile()` |
| Role 3 → Role 4 | `ProfileResponse` → talent check payload | Inline mapping in talent check call |
| Role 3+1 → Role 5 | `ProfileResponse` + `JDAnalysis` → `MatchRequest` | `runFullAssessment()` |

---

## Environment Variable Wiring

| Env Var | Service | Port |
|---------|---------|------|
| `VITE_JD_API_URL` | Role 1 — JD Analytics | 8001 |
| `VITE_RESUME_API_URL` | Role 2 — Resume Parsing | 8002 |
| `VITE_PROFILE_API_URL` | Role 3 — Profile Builder | 8003 |
| `VITE_TALENT_API_URL` | Role 4 — Talent Check | 8004 |
| `VITE_MATCH_API_URL` | Role 5 — Skill Matching | 8005 |

