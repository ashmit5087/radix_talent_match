# RADIX Platform — API Contracts

Cross-role data flow, payload shapes, and shared field definitions.
This is the integration source-of-truth — not a replacement for each service's `/docs`.

---

## Shared Skill Schema (All Roles)

All five roles agree on this canonical skill representation:

```typescript
type Skill = {
  skill_name: string;         // e.g. "Python"
  category_code: CategoryCode; // one of 13 RADIX codes
  evidence: string;            // evidence text, max 1000 chars
  confidence: "high" | "medium" | "low"; // NOT proficiency
};
```

### Category Codes
| Code | Domain |
|------|--------|
| COD | Coding |
| DSA | Data Structures & Algorithms |
| OOD | Object-Oriented Design |
| APTI | Aptitude |
| COMM | Communication |
| AI | AI / Machine Learning |
| CLOUD | Cloud Computing |
| SQL | SQL & Databases |
| SWE | Software Engineering |
| SYSD | System Design |
| NETW | Networking |
| OS | Operating Systems |
| OTHER | Fallback |

---

## Role 1 — JD Analytics

**Base URL**: `http://localhost:8001`

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/health` | — | `{ status }` |
| POST | `/api/v1/jds/analyze` | `multipart/form-data` file | `JDAnalysis` |
| GET | `/api/v1/jds` | — | `JDAnalysis[]` |
| GET | `/api/v1/jds/{jd_id}` | — | `JDAnalysis` |
| GET | `/api/v1/jds/{jd_id}/skills` | — | `Skill[]` |
| PATCH | `/api/v1/jds/{jd_id}/skills` | `{ skills: Skill[] }` | — |
| DELETE | `/api/v1/jds/{jd_id}` | — | — |
| POST | `/api/v1/jds/search` | `{ query: string, top_k: number }` | `JDAnalysis[]` |

```typescript
type JDAnalysis = {
  jd_id: string;
  source_type: string;
  source_file: string;
  company?: string;
  role?: string;
  skills: Skill[];
};
```

---

## Role 2 — Resume Parsing

**Base URL**: `http://localhost:8002`
**New**: HTTP adapter added in this integration. Original CLI (`parse_resume.py`) unchanged.

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/health` | — | `{ status, groq_api_key_configured }` |
| POST | `/api/v1/resumes/parse` | `multipart/form-data` file (PDF/DOCX, ≤10 MB) | `ResumeExtract` |

```typescript
type ResumeExtract = {
  source_type: "resume";
  source_file: string;
  company: null;
  role: null;
  skills: Skill[];
  education: string | null;
  projects: string[];
  experience: string[];
  certifications: string[];
};
```

**Environment**: Requires `GROQ_API_KEY`.

---

## Role 3 — Profile Builder

**Base URL**: `http://localhost:8003`

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/health` | — | `{ status, environment, persistence_mode }` |
| POST | `/api/v1/profiles` | `CandidateProfileCreate` | `CandidateProfileResponse` |
| GET | `/api/v1/profiles/{profile_id}` | — | `CandidateProfileResponse` |
| PUT | `/api/v1/profiles/{profile_id}` | `CandidateProfileUpdate` | `CandidateProfileResponse` |
| GET | `/api/v1/profiles/{profile_id}/skills` | — | `SkillListResponse` |
| GET | `/api/v1/profiles/{profile_id}/completeness` | — | `ProfileCompletenessResponse` |
| POST | `/api/v1/profiles/{profile_id}/cv` | `multipart/form-data` file | `CvUploadResponse` |

**Persistence**: Supabase when `SUPABASE_URL` + `SUPABASE_ANON_KEY` are set; otherwise in-memory (data lost on restart).

---

## Role 4 — Talent Check

**Base URL**: `http://localhost:8004`

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/api/health` | — | `{ status, company_count, available_categories }` |
| GET | `/api/categories` | — | Category list |
| GET | `/api/companies?q=&limit=` | — | `CompanySummary[]` |
| GET | `/api/companies/{id}` | — | `Company` |
| GET | `/api/candidates` | — | Mock candidates (for testing) |
| POST | `/api/talent-check` | `{ company_id, candidate_profile }` | `TalentCheckResult` |
| POST | `/api/talent-check/direct` | `{ company_id, skill_levels }` | `TalentCheckResult` |

```typescript
type TalentCheckResult = {
  candidate_name: string;
  readiness_score: number;    // 0–100
  verdict?: string;
  critical_gaps?: string[];
  focus_areas?: string[];
  category_results?: Record<string, unknown>;
};
```

---

## Role 5 — Skill Matching

**Base URL**: `http://localhost:8005`

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/health` | — | `{ status }` |
| POST | `/api/v1/matches` | `MatchRequest` | `MatchResult` |
| POST | `/api/v1/matches/preview` | `MatchRequest` | `MatchResult` (lightweight) |
| POST | `/api/v1/matches/with-talent-check` | `MatchRequestWithTalentCheck` | `MatchResult` |
| POST | `/api/v1/improvement-plan` | `MatchRequest` | `{ actions: ImprovementAction[] }` |

```typescript
type MatchRequest = {
  candidate: { skills: Skill[] };
  job_description: JDAnalysis;
  talent_check: TalentCheckResult | null;
};

type MatchResult = {
  match_score: number;        // 0–100
  summary: string;
  missing_skills: MatchSkill[];
  partial_matches: MatchSkill[];
  matched_skills: MatchSkill[];
  review_required: MatchSkill[];
  score_breakdown?: { formula?: string };
  disclaimer: string;
  improvement_plan?: { actions: ImprovementAction[] };
};
```

---

## Cross-Role Data Flow

```
                         ┌─────────────────────────────────────┐
                         │          adapters.ts                │
                         │                                     │
ResumeExtract (Role 2) ──► resumeToProfileCreate()   ────────► ProfileCreate (Role 3)
Profile (Role 3)        ──► profileToTalentCheckPayload() ───► candidate_profile (Role 4)
Profile + JDAnalysis    ──► buildMatchRequest() ──────────────► MatchRequest (Role 5)
Profile + JD + TCResult ──► buildMatchWithTalentCheckRequest() ► MatchRequest+TC (Role 5)
                         └─────────────────────────────────────┘
```

---

## CORS Configuration

Each service must allow requests from the frontend origin (`http://localhost:5173`).

| Role | CORS status |
|------|-------------|
| 1 | Configured in `app/main.py` |
| 2 | Configured in `api_server.py` (new) |
| 3 | Configured in `backend/main.py` |
| 4 | Verify `CORSMiddleware` in `api.py` |
| 5 | Verify `CORSMiddleware` in `api.py` |
