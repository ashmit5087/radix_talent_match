# RADIX Talent Match — Hackathon Master Guide

## 1. What RADIX is

RADIX is an evidence-aware candidate intelligence platform. It turns a resume and a
job description into:

1. A structured candidate profile.
2. A company-readiness benchmark.
3. A deterministic job skill-match score.
4. An explainable, prioritized growth plan.

The central product idea is that **company readiness and job matching are related but
not the same measurement**:

- **Role 4 — Talent Check** asks: “How ready is this candidate for the general
  competency bar of a company?”
- **Role 5 — Skill Matching** asks: “How closely does this candidate match this
  particular job description?”

Role 4 context can be shown with a Role 5 result, but Role 4 readiness does not
artificially reduce the Role 5 match score.

---

## 2. Current architecture

```text
Browser / React frontend :5173
        |
        |-- Role 1 :8001  JD Analytics
        |-- Role 2 :8002  Resume Parsing
        |-- Role 3 :8003  Profile Builder
        |-- Role 4 :8004  Talent Check
        `-- Role 5 :8005  Skill Matching

Optional persistence:
        Supabase PostgreSQL
        - profiles
        - profile_skills
        - jd_analyses
        - jd_skills
        - assessments
```

### Technology choices

- Frontend: React, TanStack Router, Vite, Tailwind CSS, TypeScript.
- Backend: FastAPI services with isolated Python environments.
- Role 1: deterministic extraction fallback plus optional Gemini/ChromaDB flow.
- Role 2: resume extraction adapter with optional Groq-powered extraction.
- Role 3: profile schema and persistence service.
- Role 4: deterministic competency and company-readiness scoring.
- Role 5: deterministic skill matching and improvement-plan generation.
- Optional database: Supabase PostgreSQL.
- Local browser session: `sessionStorage` stores the active profile and assessment
  history for a fast hackathon demo.

---

## 3. End-to-end user journey

### Step 1 — Upload a resume

The user opens `/onboarding` and uploads a PDF or DOCX.

The frontend calls:

```text
POST http://localhost:8002/api/v1/resumes/parse
```

Role 2 returns:

- Candidate source filename.
- Extracted skills.
- Education.
- Projects.
- Experience.
- Certifications.

When a new resume is successfully parsed, the frontend clears the previous
assessment history from the active browser session. This prevents an old score from
being presented as a score for a new resume.

### Step 2 — Build the profile

The frontend maps Role 2 output into the canonical `CandidateProfile` shape and
optionally sends the skill payload to Role 3:

```text
POST http://localhost:8003/api/v1/profiles
```

The profile is also stored in browser session storage so the demo remains usable if
Supabase is not configured.

The profile page supports manual additions for details missed by the parser:

- Location.
- Headline.
- Skills and skill category.
- Projects.
- Experience.
- Education.
- Certifications.
- Preferred roles.

Manual skills are marked with `source: "manual"` and are included in later Role 4
and Role 5 requests.

### Step 3 — Run Talent Check

The **Talent Check** page is available at:

```text
http://localhost:5173/app/talent-check
```

It loads companies from Role 4:

```text
GET  http://localhost:8004/api/companies
POST http://localhost:8004/api/talent-check
```

The page evaluates the active profile against multiple companies and displays:

- Average readiness.
- Company-by-company readiness.
- Verdict.
- Competencies met.
- Competency gaps.
- Critical gap count.
- Focus areas.

### Step 4 — Analyze a job description

The assessment flow uploads a JD to Role 1:

```text
POST http://localhost:8001/api/v1/jds/analyze
```

Role 1 returns the normalized job requirements:

```json
{
  "source_file": "role.pdf",
  "company": "Example Corp",
  "role": "Data Analyst",
  "skills": [
    {
      "skill_name": "SQL",
      "category_code": "SQL",
      "evidence": "Advanced SQL",
      "confidence": "high"
    }
  ]
}
```

If the external LLM provider is unavailable, Role 1's deterministic fallback
extractor continues to identify known skills and job/company headings.

### Step 5 — Run the job match

The frontend sends the Role 1 JD and active candidate skills to Role 5:

```text
POST http://localhost:8005/api/v1/matches
```

If Role 4 context was selected, the integrated endpoint is used:

```text
POST http://localhost:8005/api/v1/matches/with-talent-check
```

Role 5 returns:

- `match_score` from 0 to 100.
- Fully matched skills.
- Partial matches.
- Review-required skills.
- Missing skills.
- Evidence rationales.
- Score breakdown.
- Role 4 context, when supplied.

The score is deterministic:

```text
score = 100 * (matched_weight + 0.5 * partial_weight) / total_required_weight
```

Role 4 readiness and proficiency gaps remain visible as context and growth-plan
signals, but do not erase a direct Role 5 skill match.

### Step 6 — View growth

Role 5 generates the improvement plan:

```text
POST http://localhost:8005/api/v1/improvement-plan
```

The Skill Growth page provides an assessment selector. It shows the plan for exactly
one selected assessment at a time:

- Current score.
- Projected score path.
- Ranked actions.
- Score gain per action.
- Learning steps.
- Proficiency level target when available.

Plans are not merged across roles, so the interface stays clean.

---

## 4. The five roles

## Role 1 — JD Analytics

### Mission

Convert an unstructured job description into a reliable, normalized requirements
document.

### Responsibilities

- Accept PDF/DOCX job descriptions.
- Extract company and role headings.
- Identify required skills.
- Assign RADIX category codes.
- Preserve evidence text and extraction confidence.
- Optionally index analyzed JDs for search.
- Fall back to deterministic extraction when an LLM is unavailable.

### API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/v1/jds/analyze` | Analyze a JD upload |
| GET | `/api/v1/jds` | List analyzed JDs |
| GET | `/api/v1/jds/{jd_id}` | Retrieve a JD |
| POST | `/api/v1/jds/search` | Search stored JDs |

### Frontend interaction

The New Assessment screen uploads a JD to Role 1. The returned normalized object is
passed directly to Role 5, avoiding a second interpretation of the same document.

### Hackathon talking point

“Role 1 converts noisy hiring language into an auditable skill contract instead of
passing raw text blindly into a scoring model.”

---

## Role 2 — Resume Parsing

### Mission

Convert a candidate resume into structured evidence.

### Responsibilities

- Accept PDF/DOCX resumes.
- Extract skills and evidence.
- Extract education, projects, experience, and certifications.
- Preserve confidence metadata.
- Expose a stable HTTP adapter for the frontend.

### API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/v1/resumes/parse` | Parse a resume |

### Frontend interaction

The onboarding page displays the parsed result before saving. The candidate can then
review and complete details manually on My Profile.

### Hackathon talking point

“We do not treat extraction as the final truth. We show the candidate what was
found, label evidence quality, and let the candidate fill gaps.”

---

## Role 3 — Profile Builder

### Mission

Maintain the canonical candidate profile consumed by the rest of the system.

### Responsibilities

- Validate profile shape.
- Store personal information and normalized skills.
- Calculate completeness.
- Preserve extracted versus manually entered sources.
- Provide profile retrieval for downstream services.

### API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/v1/profiles` | Create profile |
| GET | `/api/v1/profiles/{profile_id}` | Retrieve profile |
| GET | `/api/v1/profiles/{profile_id}/completeness` | Completeness |
| POST | `/api/v1/profiles/{profile_id}/cv` | Attach CV |

### Frontend interaction

My Profile shows:

- Real checklist status based on the saved profile.
- Extracted/manual source labels.
- Completeness percentage.
- Manual completion controls.

### Hackathon talking point

“The profile is the shared contract between parsing, readiness scoring, and job
matching. This prevents every service from inventing its own candidate schema.”

---

## Role 4 — Talent Check

### Mission

Measure general readiness against company competency benchmarks.

### Competencies

Role 4 evaluates categories including:

- Coding.
- Data Structures and Algorithms.
- Object-Oriented Design.
- Aptitude.
- Communication.
- AI.
- Cloud.
- SQL and design.
- Software engineering.
- System design.
- Networking.
- Operating systems.

### Responsibilities

- Maintain company benchmark requirements.
- Convert candidate evidence into category levels.
- Calculate readiness.
- Identify ordinary and critical gaps.
- Return verdicts and focus areas.

### API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/categories` | Competency definitions |
| GET | `/api/companies` | Company search/list |
| GET | `/api/companies/{id}` | Company benchmark |
| POST | `/api/talent-check` | Profile-based check |
| POST | `/api/talent-check/direct` | Raw level-based check |

### Frontend interaction

The dedicated Talent Check page evaluates the candidate against several companies
at once. It displays the average readiness and company cards with met, gap, and
critical counts.

### Important design boundary

Role 4 readiness is not a job-match percentage. A candidate may have low general
company readiness but still match a specific data analyst JD well.

### Hackathon talking point

“Role 4 answers the strategic question: where is this candidate ready to compete,
and which competency gaps should they close first?”

---

## Role 5 — Skill Matching and Growth

### Mission

Compare candidate evidence with the exact requirements of one JD and produce an
explainable improvement plan.

### Matching order

1. Exact match.
2. Approved alias.
3. Compound skill match, such as data structures plus algorithms.
4. Related/partial match.
5. Phrase overlap.
6. Review required.
7. Missing.

Low-confidence evidence is not silently treated as a full match.

### Responsibilities

- Calculate a deterministic 0–100 score.
- Explain every classification.
- Support compound skills.
- Recognize curated related evidence such as Power BI to data visualization.
- Generate ranked learning actions.
- Preserve Role 4 critical-gap context without distorting JD overlap.

### API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/v1/matches` | Match profile to JD |
| POST | `/api/v1/matches/preview` | Lightweight classification |
| POST | `/api/v1/matches/with-talent-check` | Match with Role 4 context |
| POST | `/api/v1/improvement-plan` | Generate growth plan |

### LLM policy

Role 5 does **not** require an LLM for scoring. The optional LLM layer can rewrite
learning-plan prose only. It cannot change:

- Match score.
- Match classification.
- Score gain.
- Projected score.
- Action ordering.

### Hackathon talking point

“Our score is deterministic and auditable. AI can make the explanation friendlier,
but it cannot secretly change the candidate’s result.”

---

## 5. Frontend pages

| Page | Route | Main purpose |
|---|---|---|
| Onboarding | `/onboarding` | Upload and parse resume |
| Home | `/app` | Current profile and latest assessment |
| My Profile | `/app/profile` | Checklist, evidence, and manual editing |
| Assessments | `/app/assessments` | Assessment history |
| New Assessment | `/app/assessments/new` | Upload JD, optional company benchmark, run match |
| Assessment Details | `/app/assessments/{id}` | Explain one match |
| Skill Growth | `/app/skill-growth` | Select one assessment and view its plan |
| Talent Check | `/app/talent-check` | Compare profile across companies |
| Role Showcase | `/app/showcase` | Demonstrate individual service behavior |
| Settings | `/app/settings` | Runtime/settings information |

### UI state rules

- A new resume clears old browser assessment history.
- A new resume requires a new assessment before old score cards reappear.
- Skill Growth always displays one selected assessment.
- Manually added profile details are persisted and used downstream.
- Score displays are decision-support estimates, not hiring decisions.

---

## 6. Database and persistence

RADIX supports two persistence layers.

### Browser session storage

Used for the local demo and fast UI state:

| Key | Contents |
|---|---|
| `radix_profile_id` | Active profile identifier |
| `radix_profile_data` | Canonical candidate profile |
| `radix_latest_assessment` | Latest assessment |
| `radix_assessments_list` | Assessment history |

This makes the frontend usable without a configured Supabase project.

When a new resume is parsed successfully, the two assessment keys are cleared.

### Supabase PostgreSQL

When `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are configured, the frontend
asynchronously syncs profiles and assessments.

#### `profiles`

Stores:

- Profile ID.
- Name and email.
- Headline/location.
- Full canonical profile JSONB.
- Created/updated timestamps.

#### `profile_skills`

Stores normalized skill rows:

- Profile ID.
- Skill name.
- Category code.
- Evidence.
- Confidence.
- Source: extracted or manual.

#### `jd_analyses`

Stores analyzed JD metadata:

- Source filename.
- Company.
- Role.
- Indexing status.
- Chunk count.
- Timestamps.

#### `jd_skills`

Stores normalized JD requirements:

- JD ID.
- Skill name.
- Category.
- Evidence.
- Confidence.
- Original position.

#### `assessments`

Stores the assessment result when the assessment persistence schema is deployed:

- Assessment ID.
- Profile ID.
- Role/company/JD filename.
- Match score.
- Matched, partial, and missing skills.
- Improvement plan.
- Talent Check context.
- Summary and timestamps.

### Database safety note

The supplied hackathon SQL currently includes permissive policies for the profile
tables to make evaluation easy. For a production deployment, add authentication,
owner-based row-level security, server-side secret handling, and audit logging.

---

## 7. Five-person team split

Give each person ownership of one role, while everyone understands the shared
pipeline.

### Person 1 — JD Intelligence Lead

Owns Role 1 and the JD side of the demo.

#### Preparation

- Explain PDF/DOCX ingestion.
- Explain skill extraction and confidence.
- Explain deterministic fallback behavior.
- Prepare one clear JD example with explicit and implicit requirements.
- Demonstrate `POST /api/v1/jds/analyze`.

#### 60-second script

> “I own JD Analytics. My service takes an unstructured job description and turns it
> into a normalized, categorized requirement contract. Every skill keeps evidence and
> confidence, so later scoring is explainable. If a provider is unavailable, our
> deterministic fallback still extracts known requirements instead of failing
> silently.”

#### Likely judge question

**Why not send the raw JD directly to an LLM?**

> “Because downstream scoring needs a stable contract. We separate extraction from
> scoring and retain evidence, making the result inspectable and repeatable.”

### Person 2 — Resume Intelligence Lead

Owns Role 2 and extraction quality.

#### Preparation

- Demonstrate resume upload.
- Explain extracted versus manual evidence.
- Show confidence labels.
- Prepare an example where a parser misses a detail and the user fills it manually.
- Explain why personal profile fields are not sent to Role 5's optional explanation LLM.

#### 60-second script

> “I own Resume Parsing. We convert a resume into structured candidate evidence:
> skills, education, projects, experience, and certifications. Extraction is not
> treated as infallible. The UI shows what was found and lets the candidate add
> missing details, which are tagged as manual evidence.”

#### Likely judge question

**What happens when parsing misses something?**

> “The candidate can add it from My Profile. The source is preserved as manual, and
> the added evidence flows into both Talent Check and Skill Matching.”

### Person 3 — Profile and Data Lead

Owns Role 3, schemas, persistence, and UI contracts.

#### Preparation

- Explain the canonical `CandidateProfile`.
- Explain browser session fallback.
- Explain Supabase tables.
- Demonstrate the completeness checklist.
- Explain why Role 2 and Role 4 do not pass incompatible shapes directly.

#### 60-second script

> “I own the canonical profile layer. Role 3 gives the platform one shared candidate
> contract, including source and confidence for every skill. The browser session
> keeps the hackathon demo resilient, while Supabase can persist profiles, skills,
> JD analyses, and assessments.”

#### Likely judge question

**How do you prevent stale scores after a new resume?**

> “A successful new resume parse clears the active assessment and growth history.
> The user must run a new assessment against the new profile.”

### Person 4 — Company Readiness Lead

Owns Role 4 and the Talent Check page.

#### Preparation

- Explain the 12 competency categories.
- Explain company benchmark requirements.
- Explain readiness score, verdict, gaps, and critical gaps.
- Demonstrate the multi-company comparison page.
- Clarify that company readiness is not the same as JD match.

#### 60-second script

> “I own Talent Check. Role 4 benchmarks the candidate against company-level
> competency bars and produces readiness, verdict, focus areas, and critical gaps.
> The new page compares several companies so a candidate can see where they are
> currently strongest before choosing an application target.”

#### Likely judge question

**Why can Role 4 be low while Role 5 is high?**

> “Because they answer different questions. Role 4 measures broad company readiness;
> Role 5 measures overlap with one specific JD. A focused candidate can match a
> data analyst role without being ready for every engineering competency.”

### Person 5 — Matching and Product Lead

Owns Role 5, growth plans, and the final UI story.

#### Preparation

- Explain the scoring formula.
- Demonstrate exact, partial, review, and missing classifications.
- Explain compound skills and curated aliases.
- Demonstrate Skill Growth with the assessment selector.
- Explain the optional LLM boundary.

#### 60-second script

> “I own Skill Matching. Role 5 compares the normalized candidate profile against
> one normalized JD using deterministic, evidence-aware rules. It returns a score
> plus the reason for every match and gap. Then it turns the gaps into ranked,
> measurable growth actions. The optional LLM can improve wording, but it can never
> modify the score or action list.”

#### Likely judge question

**Is Role 5 dependent on an LLM?**

> “No. Matching and scoring are deterministic and offline. This makes the score
> repeatable and auditable. An LLM is optional only for rewriting plan language.”

---

## 8. Suggested five-minute demo

### 0:00–0:30 — The problem

Person 5:

> “Candidates receive vague match percentages. RADIX shows what was found, why it
> counts, what is missing, and what to do next.”

### 0:30–1:15 — Resume ingestion

Person 2 uploads the resume and shows extracted evidence.

### 1:15–1:45 — Profile contract

Person 3 opens My Profile, shows checklist status, and adds one missing skill
manually.

### 1:45–2:30 — Company landscape

Person 4 opens Talent Check, runs several company checks, and points out average
readiness, strongest company fit, and critical gaps.

### 2:30–3:15 — JD normalization

Person 1 uploads a JD and shows extracted categorized requirements.

### 3:15–4:15 — Match result

Person 5 runs the assessment and explains matched, partial, review-required, and
missing sections.

### 4:15–4:45 — Growth plan

Person 5 opens Skill Growth, selects the assessment, and demonstrates the projected
score path and ranked actions.

### 4:45–5:00 — Differentiator

Person 3 or 4:

> “A new resume clears old assessment state, every result remains explainable, and
> company readiness is deliberately kept separate from JD-specific matching.”

---

## 9. Commands for the live demo

From:

```text
F:\candidate-assessment-platform\radix-platform
```

### Setup

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\scripts\setup.ps1
```

### Start

```powershell
.\scripts\dev.ps1
```

### Open

```text
http://localhost:5173
```

### Health checks

```powershell
Invoke-WebRequest http://localhost:8001/health
Invoke-WebRequest http://localhost:8002/health
Invoke-WebRequest http://localhost:8003/health
Invoke-WebRequest http://localhost:8004/health
Invoke-WebRequest http://localhost:8005/health
Invoke-WebRequest http://localhost:5173
```

### Validation

```powershell
Set-Location .\services\role-1-jd-analytics
.\.venv\Scripts\python.exe -m pytest tests -q

Set-Location ..\role-5-skill-matching
.\.venv\Scripts\python.exe -m pytest tests -q

Set-Location ..\..\frontend
npm run build
```

---

## 10. Judge-facing differentiators

1. **Evidence over black-box scores** — every result has a reason.
2. **Two useful measurements** — company readiness and JD fit are not conflated.
3. **Candidate agency** — users can correct parser omissions manually.
4. **Deterministic scoring** — the same inputs produce the same score.
5. **Actionable output** — every gap becomes a prioritized learning action.
6. **Graceful degradation** — optional LLM providers can fail without taking down
   the core product.
7. **Clean state management** — new resumes cannot inherit old assessment scores.
8. **Company landscape view** — candidates can compare several preliminary fits
   before investing in an application.

## Closing pitch

> “RADIX does not stop at ‘you scored 69’. It explains which evidence produced the
> score, distinguishes company readiness from job-specific fit, lets candidates
> correct missing information, and gives them a concrete path from today’s profile
> to a stronger application.”

