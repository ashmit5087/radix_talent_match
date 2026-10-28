# RADIX Platform — Integration Test Cases

Scenarios that must pass for the platform to be considered production-ready. Covers all 5 services and cross-role flows.

---

## Test Environment Setup

```powershell
# Start all services
cd radix-platform
.\scripts\dev.ps1

# Confirm all 5 are online
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/api/health
curl http://localhost:8005/health
```

---

## TC-01: Role 1 — JD Analysis (Happy Path)

**Goal:** Upload a valid JD PDF and receive structured skill extraction.

```bash
curl -X POST http://localhost:8001/api/v1/jds/analyze \
  -F "file=@tests/fixtures/sample_jd.pdf"
```

**Expected:**
- HTTP 200
- Response contains `jd_id` (non-empty string)
- `skills` array has ≥ 1 item
- Each skill has `skill_name`, `category_code`, `confidence` ∈ {high, medium, low}

---

## TC-02: Role 1 — JD List & Fetch

**Goal:** Analyzed JDs persist and are retrievable.

```bash
# List
curl http://localhost:8001/api/v1/jds
# → array, length ≥ 1 after TC-01

# Fetch by ID from TC-01
curl http://localhost:8001/api/v1/jds/{jd_id}
# → same JDAnalysis object
```

---

## TC-03: Role 2 — Resume Parsing (Happy Path)

**Goal:** Upload a valid resume and receive extracted skills.

```bash
curl -X POST http://localhost:8002/api/v1/resumes/parse \
  -F "file=@tests/fixtures/sample_resume.pdf"
```

**Expected:**
- HTTP 200
- `source_type` = `"resume"`
- `skills` array has ≥ 1 item
- `education` is a non-empty string

---

## TC-04: Role 2 — Unsupported File Type

```bash
curl -X POST http://localhost:8002/api/v1/resumes/parse \
  -F "file=@tests/fixtures/image.png"
```

**Expected:** HTTP 422 or 400 with a descriptive error message.

---

## TC-05: Role 3 — Profile Create & Retrieve

**Goal:** Create a profile and retrieve it by ID.

```bash
# Create
curl -X POST http://localhost:8003/api/v1/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "personal_info": { "full_name": "Test User", "email": "test@radix.ai" },
    "skills": [
      { "skill_name": "Python", "category_code": "SE", "evidence": "3 years", "confidence": "high", "source": "manual" }
    ]
  }'
# → save profile_id

# Retrieve
curl http://localhost:8003/api/v1/profiles/{profile_id}
```

**Expected:**
- Create → HTTP 201 or 200 with `profile_id`
- Retrieve → same data, `profile_id` matches

---

## TC-06: Role 3 — Profile Completeness

```bash
curl http://localhost:8003/api/v1/profiles/{profile_id}/completeness
```

**Expected:**
- HTTP 200
- `score` between 0 and 100
- `missing_fields` is an array (may be empty)

---

## TC-07: Role 4 — Company Search

```bash
curl "http://localhost:8004/api/companies?q=google&limit=5"
```

**Expected:**
- HTTP 200
- Array of ≤ 5 companies
- Each item has `id` (integer), `company` (string), `skills` (object)
- At least one result contains "google" (case-insensitive) in the `company` field

---

## TC-08: Role 4 — Talent Check (Profile)

**Goal:** Run a talent check against a known company.

```bash
# First get a company ID from TC-07 (e.g., id=1)
curl -X POST http://localhost:8004/api/talent-check \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 1,
    "candidate_profile": {
      "name": "Test Candidate",
      "skills": [
        { "skill_name": "Python", "confidence": "high", "evidence": "3 years", "category": "SE" },
        { "skill_name": "SQL", "confidence": "medium", "evidence": "2 years", "category": "DE" }
      ]
    }
  }'
```

**Expected:**
- HTTP 200
- `readiness_score` ∈ [0, 100]
- `verdict` is a non-empty string
- `critical_gaps` is an array
- `focus_areas` is an array

---

## TC-09: Role 4 — Direct Talent Check

```bash
curl -X POST http://localhost:8004/api/talent-check/direct \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 1,
    "skill_levels": { "SE": 7, "DS": 5, "ML": 3, "Cloud": 6 }
  }'
```

**Expected:** Same shape as TC-08. `readiness_score` should reflect the provided levels.

---

## TC-10: Role 5 — Skill Match

**Goal:** Run a deterministic match between a candidate and JD.

```bash
curl -X POST http://localhost:8005/api/v1/matches \
  -H "Content-Type: application/json" \
  -d '{
    "candidate": {
      "skills": [
        { "skill_name": "Python", "category_code": "SE", "evidence": "3 years", "confidence": "high" },
        { "skill_name": "FastAPI", "category_code": "BE", "evidence": "2 years", "confidence": "high" }
      ]
    },
    "job_description": {
      "jd_id": "test-jd",
      "source_type": "file",
      "source_file": "test.pdf",
      "skills": [
        { "skill_name": "Python", "category_code": "SE", "evidence": "required", "confidence": "high" },
        { "skill_name": "Docker", "category_code": "DevOps", "evidence": "required", "confidence": "high" }
      ]
    },
    "talent_check": null
  }'
```

**Expected:**
- HTTP 200
- `overall_score` ∈ [0, 100]
- `matched_skills` contains Python (present in both)
- `gap_skills` contains Docker (in JD but not candidate)

---

## TC-11: Role 5 — Improvement Plan

Same request body as TC-10, but to:
```bash
curl -X POST http://localhost:8005/api/v1/improvement-plan ...
```

**Expected:**
- `summary` is a non-empty string
- `steps` array has ≥ 1 step for Docker (the identified gap)
- Each step has `skill_name`, `priority`, `action`

---

## TC-12: Cross-Role Flow — Resume → Profile → Match

**Goal:** End-to-end integration: upload resume → save profile → run match.

1. `POST /api/v1/resumes/parse` → extract skills (TC-03)
2. `POST /api/v1/profiles` using extracted skills (TC-05) → `profile_id`
3. `POST /api/v1/jds/analyze` → `jd_id` (TC-01)
4. `POST /api/v1/matches` using profile skills + JD → `overall_score`

**Expected:** All 4 steps succeed with 200. Final `overall_score` is deterministic for the same inputs.

---

## TC-13: Cross-Role Flow — Profile → Talent Check → Weighted Match

1. Create profile (TC-05) → `profile_id`
2. Search companies (TC-07) → `company_id`
3. Run talent check (TC-08) → `TalentCheckResult`
4. `POST /api/v1/matches` with `talent_check: TalentCheckResult`

**Expected:** `overall_score` differs from TC-10 (talent check weighting applied). No HTTP errors.

---

## TC-14: Health Checks — All Services

```bash
for port in 8001 8002 8003 8005; do
  curl -s http://localhost:$port/health | python -m json.tool
done
curl -s http://localhost:8004/api/health | python -m json.tool
```

**Expected:** All return HTTP 200 with `"status": "healthy"` (or equivalent).

---

## TC-15: CORS Headers

```bash
curl -I -X OPTIONS http://localhost:8001/api/v1/jds/analyze \
  -H "Origin: http://localhost:5173"
```

**Expected:** `Access-Control-Allow-Origin: *` (or `http://localhost:5173`) in response headers. All 5 services must pass this.

---

## Regression Baseline

After any code change, run the following minimum set to confirm no regressions:
1. TC-01 (JD parse)
2. TC-03 (Resume parse)
3. TC-05 (Profile create/get)
4. TC-07 (Company search)
5. TC-10 (Skill match)
6. TC-14 (All health checks)

