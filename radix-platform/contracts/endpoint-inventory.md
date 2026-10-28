# RADIX Platform — Endpoint Inventory

**All microservice REST endpoints across all 5 roles.**

---

## Role 1 — JD Analytics (port 8001)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/health` | Service health check | None |
| `POST` | `/api/v1/jds/analyze` | Upload and analyze a JD (PDF/DOCX). Returns extracted skills + metadata. | None |
| `GET` | `/api/v1/jds` | List all previously analyzed JDs | None |
| `GET` | `/api/v1/jds/{jd_id}` | Fetch a single analyzed JD by ID | None |
| `POST` | `/api/v1/jds/search` | Semantic search over stored JDs | None |

### `POST /api/v1/jds/analyze`
**Request:** `multipart/form-data` — `file` (PDF or DOCX)  
**Response:**
```json
{
  "jd_id": "abc123",
  "source_type": "file",
  "source_file": "senior_engineer.pdf",
  "company": "Acme Corp",
  "role": "Senior Software Engineer",
  "skills": [
    { "skill_name": "Python", "category_code": "SE", "evidence": "3+ years Python", "confidence": "high" }
  ]
}
```

---

## Role 2 — Resume Parsing (port 8002)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/health` | Service health check | None |
| `POST` | `/api/v1/resumes/parse` | Upload and parse a resume (PDF/DOCX). Returns extracted skills + experience. | None |

### `POST /api/v1/resumes/parse`
**Request:** `multipart/form-data` — `file` (PDF or DOCX)  
**Response:**
```json
{
  "source_type": "resume",
  "source_file": "john_doe_cv.pdf",
  "skills": [
    { "skill_name": "FastAPI", "category_code": "BE", "evidence": "Built REST APIs", "confidence": "high" }
  ],
  "education": "B.Sc. Computer Science, IIT Delhi",
  "projects": ["RADIX Talent Platform", "ML Pipeline v2"],
  "experience": ["3 years at Infosys", "2 years at Startup X"],
  "certifications": ["AWS Solutions Architect"]
}
```

---

## Role 3 — Profile Builder (port 8003)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/health` | Service health check | None |
| `POST` | `/api/v1/profiles` | Create a new candidate profile | None |
| `GET` | `/api/v1/profiles/{profile_id}` | Retrieve a profile by ID | None |
| `GET` | `/api/v1/profiles/{profile_id}/completeness` | Get profile completeness score + missing fields | None |
| `POST` | `/api/v1/profiles/{profile_id}/cv` | Upload a CV file to attach to a profile | None |

### `POST /api/v1/profiles`
**Request:** `application/json`
```json
{
  "personal_info": { "full_name": "Jane Doe", "email": "jane@example.com", "location": "Bangalore", "summary": "..." },
  "skills": [
    { "skill_name": "Python", "category_code": "SE", "evidence": "3 years", "confidence": "high", "source": "extracted" }
  ]
}
```
**Response:** `ProfileResponse` with `profile_id`, timestamps, and echoed data.

---

## Role 4 — Talent Check (port 8004)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/health` | Service health check | None |
| `GET` | `/api/categories` | List 12 RADIX competency categories with tier guides | None |
| `GET` | `/api/companies` | List/search companies (`?q=<query>&limit=<n>`) | None |
| `GET` | `/api/companies/{company_id}` | Get a single company's full benchmark data | None |
| `GET` | `/api/candidates` | List built-in mock candidate profiles | None |
| `POST` | `/api/talent-check` | Run talent check: profile vs company benchmarks | None |
| `POST` | `/api/talent-check/direct` | Run talent check with raw skill levels (1–10) | None |

### `POST /api/talent-check`
**Request:**
```json
{
  "company_id": 42,
  "candidate_profile": { "name": "Jane Doe", "skills": [...] }
}
```
**Response:**
```json
{
  "candidate_name": "Jane Doe",
  "readiness_score": 78.4,
  "verdict": "Strong Candidate",
  "critical_gaps": ["DSA", "System Design"],
  "focus_areas": ["Cloud", "ML Ops"],
  "category_results": { "SE": 8, "DS": 5, ... }
}
```

---

## Role 5 — Skill Matching (port 8005)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/health` | Service health check | None |
| `POST` | `/api/v1/matches` | Run deterministic skill match: candidate vs JD | None |
| `POST` | `/api/v1/matches/preview` | Lightweight preview match (no persistence) | None |
| `POST` | `/api/v1/improvement-plan` | Generate gap-weighted improvement plan | None |

### `POST /api/v1/matches`
**Request:**
```json
{
  "candidate": { "skills": [...] },
  "job_description": { "jd_id": "...", "skills": [...] },
  "talent_check": null
}
```
**Response:** `MatchResult` with `overall_score`, `matched_skills`, `gap_skills`, `category_breakdown`.

---

## Notes

- All services support `CORS *` for local development.
- All file uploads must be PDF or DOCX (scanned/image-only PDFs not supported by Role 1).
- Role 4 `GET /api/companies` returns `{ id, company, skills }` — `company` is the display name field (not `name`).

