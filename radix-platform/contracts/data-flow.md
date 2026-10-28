# RADIX Platform — Data Flow

End-to-end data flow for each major user journey through the platform.

---

## Flow A — Resume Upload → Profile → Skill Match

```
1. User uploads PDF/DOCX resume on /app/resume
        │
        ▼
2. POST http://localhost:8002/api/v1/resumes/parse
   ┌──────────────────────────────────────────────┐
   │  Role 2 (Groq LLM pipeline)                  │
   │  • pdfplumber / python-docx extracts text    │
   │  • LangChain + Groq LLM classifies skills    │
   │  • Returns ResumeExtract JSON                │
   └──────────────────────────────────────────────┘
        │
        │  ResumeExtract { skills[], education, projects, experience }
        ▼
3. Frontend displays extracted skills to user
        │
        │  User clicks "Create Profile"
        ▼
4. resumeToProfile() converts ResumeExtract → ProfileCreate
        │
        ▼
5. POST http://localhost:8003/api/v1/profiles
   ┌──────────────────────────────────────────────┐
   │  Role 3 (Supabase / in-memory store)         │
   │  • Validates personal_info + skills          │
   │  • Assigns profile_id                        │
   │  • Persists to Supabase (or in-memory)       │
   │  • Returns ProfileResponse                   │
   └──────────────────────────────────────────────┘
        │
        │  ProfileResponse { profile_id, skills[], personal_info }
        ▼
6. Frontend stores profile_id (session.ts)
        │
        │  User navigates to /app/assessments/new
        ▼
7. User uploads JD → POST /api/v1/jds/analyze (Role 1) → JDAnalysis
        │
        ▼
8. POST http://localhost:8005/api/v1/matches
   + POST http://localhost:8005/api/v1/improvement-plan (parallel)
   ┌──────────────────────────────────────────────┐
   │  Role 5 (Deterministic matcher)              │
   │  • Normalizes skill names (aliases.py)       │
   │  • Computes weighted overlap score (0–100)   │
   │  • Identifies matched & gap skills           │
   │  • Optionally weights by talent_check score  │
   │  • Generates improvement plan steps          │
   └──────────────────────────────────────────────┘
        │
        │  MatchResult + ImprovementPlan
        ▼
9. Frontend navigates to /app/assessments/:id
   Displays score rings, gap analysis, plan steps
```

---

## Flow B — JD Analysis → Talent Check → Match

```
1. User uploads JD → POST /api/v1/jds/analyze (Role 1) → JDAnalysis
        │
        ▼
2. User opens /app/assessments/new
   Toggles "Include Talent Check"
        │
        ▼
3. CompanyPicker calls GET /api/companies?q= (Role 4)
   User selects a company
        │
        ▼
4. POST http://localhost:8004/api/talent-check
   ┌──────────────────────────────────────────────┐
   │  Role 4 (Deterministic scoring engine)       │
   │  • get_candidate_levels_with_points()        │
   │    → maps skills to 12 RADIX categories      │
   │    → applies asymptotic saturating curve     │
   │      k=4.0: score = k·x/(k+x)               │
   │  • score() compares vs company benchmarks    │
   │  • Returns readiness_score (0–100), verdict  │
   │    critical_gaps, focus_areas                │
   └──────────────────────────────────────────────┘
        │
        │  TalentCheckResult
        ▼
5. POST /api/v1/matches with talent_check: TalentCheckResult
   Role 5 uses talent check gaps to weight the match score
        │
        ▼
6. AssessmentRecord constructed and stored in session
   Navigate to /app/assessments/:id
```

---

## Flow C — Manual Profile → Talent Check Only

```
1. User fills form on /app/profile/new
        │
        ▼
2. POST /api/v1/profiles (Role 3) → profile_id
        │
        ▼
3. User navigates to /app/talent-check
   Enters profile_id + searches company
        │
        ▼
4. GET /api/companies (Role 4)
   POST /api/talent-check (Role 4)
        │
        ▼
5. Display: readiness score, verdict, category breakdown,
   critical gaps (areas below company bar),
   focus areas (highest-ROI improvements)
```

---

## Data Shape Lifecycle

| Stage | Shape | Role |
|-------|-------|------|
| Raw file | `File` (PDF/DOCX) | Browser |
| Parsed resume | `ResumeExtract` | Role 2 output |
| Stored profile | `ProfileResponse` | Role 3 output |
| Parsed JD | `JDAnalysis` | Role 1 output |
| Talent score | `TalentCheckResult` | Role 4 output |
| Match request | `MatchRequest` | Assembled by frontend |
| Match result | `MatchResult` | Role 5 output |
| Improvement plan | `ImprovementPlan` | Role 5 output |
| Assessment record | `AssessmentRecord` | Frontend composite |

