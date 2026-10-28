# RADIX Talent Match Hackathon: Role 4 (Talent Check) Context

> Paste this whole file into your AI editor (e.g. Antigravity) as project context. It contains everything discussed so far: the hackathon brief, my role, the data, the design decisions still open, and the build plan.

---

## 0. Instruction for the AI editor

I am building **Role 4: Talent Check** for the RADIX Talent Match Hackathon. Use this file as the source of truth. Build in Python (backend logic + API) with a React frontend. Keep the scoring logic as plain code (no LLM). Structure the code in two layers (see section 6) so that the way candidate levels arrive can change without rewriting the scoring.

Start with, in this order:
1. The SQL-to-JSON company loader (section 5, tested snippet included).
2. The scoring function `score(candidate_levels, company)`.
3. Four hand-written mock candidate profiles that differ on purpose.
4. A small API (FastAPI) exposing `run_talent_check`.
5. A React UI: company selector, "Run Talent Check" button, results view (per-skillset gap bars + readiness score).

---

## 1. The hackathon in brief

**RADIX Talent Match** is a small, real, end-to-end tool that helps a *candidate* understand how ready they actually are for a specific job. It uses RADIX's 12-skillset framework and real hiring data. Previous RADIX work was the company side of a placement platform; this flips it to the candidate side.

**Teams:** exactly 5 members, 5 roles, one member also acts as Scrum Master (the Scrum Master is the owner of Role 1 in the brief's illustration, but the team decides).

**Integrated flow:** Pick a JD → Parse resume → Build/update profile → Run Talent Check → Run Skill Matching

### Timeline (2026)
| Date | Event |
|---|---|
| 24 Oct (Sat), 9:30 AM sharp | Hackathon launch |
| 24 to 28 Oct | Build phase |
| **28 Oct (Wed)** | **Deadline: integrated tool and presentation fully complete** |
| 29 Oct (Thu) | Peer presentations, top 9 teams selected |
| 30 Oct (Fri) | Expert panel (industry experts, TGL experts, JSS faculty, JSS management), top 3 selected |
| 31 Oct (Sat) | TGL Blitz grand finale (JSS Noida management, industry experts, investors/startups, TGL team) |

### Certificates
- All participants: Participation Certificate
- Top 9 teams: Pre-Finalist Certificate
- Top 3 teams: Finalist Certificate

### Presentation
45 minutes per team. Plan a **live walkthrough of the integrated tool** (not just slides) covering: (1) the problem, (2) the architecture, (3) live demo, (4) one challenge faced. Rehearse end to end without mentor help.

### Tech stack (from the brief)
- Language: Python throughout
- AI layer: LangChain / LLM agent only where it genuinely helps (JD Analytics, Resume Parsing, fuzzy part of Skill Matching). Plain code for Profile Builder form and Talent Check scoring.
- Frontend: React (matches RADIX portal)
- Storage: Supabase, JSON for most things

### Definition of done
- All 5 pieces run on their own against at least 2 of the sample JDs/resumes.
- The 5 pieces are wired into one flow, end to end, for at least one company/JD/candidate combination.
- **Talent Check and Skill Matching give visibly different results for different candidates** (the scoring logic cannot be constant).

---

## 2. The five roles

| # | Role | Type | Mission | Input | Output |
|---|---|---|---|---|---|
| 1 | JD Analytics (+ Scrum Master in the illustration) | LLM extraction | Extract required skills from a JD (PDF/DOCX), mapped onto the 12 categories | A JD file | JD skill list |
| 2 | Resume Parsing | LLM extraction | Extract skills and technical signal from a resume (PDF/DOCX) | A resume file | Resume skill list + education/projects/experience |
| 3 | Profile Builder | Plain code | Form for basic details, skills, hackathons/internships, certifications, preferred roles, CV upload; save/load as JSON | Form entry, ideally pre-filled from Role 2 | Saved candidate profile |
| **4** | **Talent Check (MINE)** | **Plain code** | **Compare a candidate profile against a company's expected level across all 12 skillsets and show the gap** | **Saved profile + selected company** | **Readiness score + per-skillset gap breakdown** |
| 5 | Skill Matching | Fuzzy match / LLM | Match a candidate against one specific JD | Profile/resume + one JD skill list from Role 1 | Match score + matched and missing skills |

### Handoffs
- JD Analytics → Skill Matching
- Resume Parsing → Profile Builder
- Profile Builder → Talent Check, Skill Matching
- Talent Check and Skill Matching are end outputs

### Dependency note
Everyone depends on Role 3 (Profile Builder). The Scrum Master must make sure Roles 4 and 5 are not left waiting on it. Ask Role 3 for a save/load loop early, even with dummy data.

### Scrum Master duties (for reference)
Leads the kick-off, makes sure the shared data contract is agreed and written down, keeps the team on schedule for 28 Oct, owns the milestone tracker (Not Started / In Progress / Blocked / Done), clears blockers early, leads integration, gets the team presentation-ready.

---

## 3. My role (Role 4: Talent Check) in detail

- **One button** that compares a candidate's profile against a company's expected bar across all 12 RADIX skillsets and shows the gap.
- **Input:** a saved profile (from Role 3) and a selected company.
- **Output:** a readiness score (0 to 100) and a per-skillset gap breakdown.
- **Approach:** mostly comparison and scoring logic, plain code. No agent needed.
- **Brief's key instruction:** decide early what "ready" means numerically (threshold, weighted score, etc.). It is a design decision, not just implementation, and it changes what the button shows.

### Proposed output shape (from the shared contract)
```json
{
  "company": "...",
  "skillset_gap": [
    {
      "category_code": "...",
      "required_level": 1-10,
      "candidate_level": 1-10,
      "gap": true|false
    }
  ],
  "readiness_score": 0-100
}
```
Field names can be changed if the team agrees. Extra fields I may want for the UI: `tier`, `category_name`, `weight`, `gap_size`.

---

## 4. Shared data contract (proposed in the brief, not final)

### The 12 RADIX skill categories
| Code | Name |
|---|---|
| COD | Coding |
| DSA | Data Structures & Algorithms |
| OOD | Object-Oriented Design |
| APTI | Aptitude |
| COMM | Communication |
| AI | AI |
| CLOUD | Cloud |
| SQL | SQL |
| SWE | Software Engineering |
| SYSD | System Design |
| NETW | Networking |
| OS | Operating Systems |

Anything outside these uses `OTHER`.

### A single skill
```json
{
  "skill_name": "...",
  "category_code": "DSA|COD|OOD|APTI|COMM|AI|CLOUD|SQL|SWE|SYSD|NETW|OS|OTHER",
  "evidence": "short quote or reason",
  "confidence": "high|medium|low"
}
```

### Extracted skill list (Roles 1 and 2)
```json
{
  "source_type": "jd|resume",
  "source_file": "...",
  "company": "...",
  "role": "...",
  "skills": [ <skill>, ... ]
}
```

### Candidate profile (Role 3)
```json
{
  "name": "...",
  "email": "...",
  "education": "...",
  "skills": [ <skill>, ... ],
  "hackathons": [...],
  "internships": [...],
  "certifications": [...],
  "preferred_roles": [...],
  "cv_file": "..."
}
```

### Skill Matching result (Role 5)
```json
{
  "jd_source_file": "...",
  "match_score": 0-100,
  "matched_skills": [...],
  "missing_skills": [...]
}
```

**The brief says to lock this schema as a team before building and write it down where everyone can see it.**

---

## 5. Company data: `staging_company_skill_levels_rows.sql`

I have the company requirements in SQL form (in addition to the brief's mention of `talent_check_company_skillsets.json`; confirm with the facilitator that they agree).

### Structure
- One `INSERT INTO public.staging_company_skill_levels (...) VALUES (...), (...)` statement
- **116 company rows**
- Metadata columns (ignore): `id`, `processed`, `processed_at`, `error_message`, `created_at`
- Company name column: `companies`

### Column to category-code mapping
| SQL column | Code |
|---|---|
| `coding` | COD |
| `data_structures_and_algorithms` | DSA |
| `object_oriented_programming_and_design` | OOD |
| `aptitude_and_problem_solving` | APTI |
| `communication_skills` | COMM |
| `ai_native_engineering` | AI |
| `devops_and_cloud` | CLOUD |
| `sql_and_design` | SQL |
| `software_engineering` | SWE |
| `system_design_and_architecture` | SYSD |
| `computer_networking` | NETW |
| `operating_system` | OS |

### Cell format
Each skill cell is a string like `'9-CR'` or `'5 - AP'`:
- The **number** is the required level (1 to 10): this is `required_level`.
- The **two-letter tier** is one of `CU`, `AP`, `AS`, `EV`, `CR`. It looks like a proficiency descriptor, probably Bloom-style (understand, apply, analyze, evaluate, create). Roughly: CU around 1-5, AP around 3-7, AS around 4-8, EV around 5-10, CR around 7-10. **This is my guess. Confirm with the facilitator.**

### Companies in the brief's test pack (map to rows)
| Brief name | SQL row | Required levels (COD, DSA, OOD, APTI, COMM, AI, CLOUD, SQL, SWE, SYSD, NETW, OS) |
|---|---|---|
| Google | id 4, "Google LLC (Subsidiary of Alphabet Inc.)" | 8-CR, 9-CR, 8-CR, 9-CR, 7-EV, 7-EV, 9-EV, 8-EV, 9-EV, 4-AS, 9-CR, 9-CR |
| Microsoft | id 78, "Microsoft Corporation" | 6-AS, 9-EV, 8-CR, 8-EV, 7-EV, 8-EV, 7-EV, 8-AS, 9-EV, 8-CR, 8-EV, 8-EV |
| Oracle FSS | id 24, "Oracle Financial Services Software Limited" | 5-AP, 6-AP, 6-EV, 6-AP, 6-AS, 6-AS, 5-AP, 6-AP, 7-AS, 5-CR, 5-AP, 5-AP |

Do not confuse Oracle FSS (id 24) with "Oracle India Private Limited" (id 3).

### Data quirks to handle
1. **Inconsistent spacing:** `software_engineering` uses `'5 - AP'` while others use `'5-AP'`. Strip whitespace before parsing.
2. **Duplicate company:** ZS Associates appears twice (ids 33 and 102) with different values. Decide which row wins (e.g. latest id).
3. **Messy names:** some names have trailing spaces (IBM, Barclays, Zerodha, Blink Commerce). One is garbled by an encoding error (Byju's appears as `ByjuÃ¢â‚¬â„¢s`). Normalize names.
4. **Wide range across companies:** e.g. OpenAI, Palantir and DeepMind sit around 8-10 on most skills; Capgemini, Infosys, Wipro and TCS sit around 2-5. The same candidate will therefore get very different readiness scores per company, which supports the "visibly different results" requirement.

### Loader (tested: parses all 116 rows, resolves ids 4, 24 and 78 correctly)
```python
import re, json

COLS = ["COD","DSA","OOD","APTI","COMM","AI","CLOUD","SQL","SWE","SYSD","NETW","OS"]

def parse_cell(cell):
    m = re.match(r"^\s*(\d+)\s*-\s*([A-Z]{2})\s*$", cell)
    return {"level": int(m.group(1)), "tier": m.group(2)}

def load_companies(path):
    text = open(path, encoding="utf-8").read()
    pat = re.compile(r"\(\s*(\d+),\s*'((?:[^']|'')*)',\s*((?:'[^']*',\s*){12})")
    out = {}
    for m in pat.finditer(text):
        cid = int(m.group(1))
        name = m.group(2).replace("''", "'").strip()
        cells = re.findall(r"'([^']*)'", m.group(3))
        out[cid] = {
            "id": cid,
            "company": name,
            "skills": {c: parse_cell(v) for c, v in zip(COLS, cells)},
        }
    return out
```
Still to add: dedupe ZS Associates, fix the Byju's name, and export a clean JSON file (e.g. `{company_name: {COD: {level, tier}, ...}}`).

---

## 6. Open design problem: where `candidate_level` comes from

The company side has levels (1 to 10). The candidate profile in the contract is only a **skill list** (`skill_name`, `category_code`, `evidence`, `confidence`), with no levels. My output needs a `candidate_level` (1 to 10) for each of the 12 categories. Options:

1. **Derive from the skill list:** e.g. count skills per category, weight by confidence, add bonuses for projects/internships/certifications/hackathons. Plain code, but I invent the formula.
2. **Add a per-category self-rating to the Profile Builder form:** the candidate sets 1-10 for each skillset (field like `skill_levels: {"COD": 6, "DSA": 4, ...}`), pre-filled from the resume parse. Simpler and more transparent, but needs a contract change.
3. **Hybrid:** derive a suggested level, let the candidate adjust it.

**Decision pending with the team (especially Role 3).** Suggested message to send:

> "For Talent Check, I need a candidate level (1 to 10) for each of the 12 skillsets in the saved profile. Can the Profile Builder include these as a `skill_levels` field, e.g. `{"COD": 6, "DSA": 4, ...}`, pre-filled from the resume parse and editable by the candidate? If not, I'll derive them from the skills list."

### Two-layer code structure (build this way)
- **Layer A: `get_candidate_levels(profile) -> {code: level}`**: placeholder for now. If the profile carries `skill_levels`, read them directly; otherwise derive from the skills list with a formula. This is the only part that changes if the team picks a different format.
- **Layer B: `score(candidate_levels, company) -> result`**: the real logic, never changes.

### Scoring definition (my proposal; decide and document)
- Per category: `ratio = min(candidate_level / required_level, 1.0)`
- `gap = candidate_level < required_level` (optionally with a small tolerance)
- `readiness_score = round(100 * weighted_average(ratio))`, weighted by required level so categories the company cares about count more
- Optional label on top: e.g. Ready / Close / Not yet, with thresholds
- Also surface `gap_size = max(required - candidate, 0)` and the tier label for the UI (e.g. "needs Evaluate-level DSA, you are at Apply")

Whatever is chosen, I must be able to explain it in one or two sentences during the presentation.

---

## 7. Test data

### Sample candidates (deliberately different skill profiles)
| Candidate | Profile | Fit as stated in the resume |
|---|---|---|
| Anny Ro | Systems-leaning generalist | Strong fit for SWE-heavy roles, weaker fit for data roles |
| Karthik Subramanian | Data-leaning analyst | Strong fit for Data Scientist / Data Analyst roles, weaker fit for pure SWE |
| Priya Menon | Entry-level, support-oriented | Best fit for Oracle FSS roles, weaker fit for Google / Microsoft |
| Rohan Verma | Strong all-rounder | Competitive fit across nearly every role |

### Job descriptions (6 real JDs, 3 companies, 2 roles each; PDF and DOCX)
- Google LLC: Software Engineer (SWE) (Bengaluru, Hybrid); Data Scientist (Bengaluru)
- Microsoft Corporation: Software Engineer (Hyderabad); Data Analyst (Hyderabad)
- Oracle Financial Services Software: Associate Software Engineer (Bengaluru/Mumbai); Application Support Analyst (Bengaluru/Chennai)

Talent Check and Skill Matching results must visibly differ between candidates.

### Mock profiles to write for testing (until Role 3 delivers a real profile)
Hand-write four JSON profiles (Anny, Karthik, Priya, Rohan) with a `skill_levels` map (1 to 10 for all 12 codes) matching the descriptions above, plus the `skills` list in the contract format. Sanity checks to run:
- Priya vs Oracle FSS should score noticeably higher than Priya vs Google.
- Rohan should score reasonably well across Google, Microsoft and Oracle FSS.
- Karthik should be weaker on SWE/OS/NETW/SYSD-heavy requirements than on SQL/AI.
- Anny should be strong on OS/NETW/SYSD/COD, weaker on SQL/AI.

---

## 8. What I am missing / still need (checklist)

1. **A way to get `candidate_level`**: agree format with Role 3 (section 6).
2. **My definition of "ready"** (section 6, proposal given).
3. **Candidate test data**: the sample resume and JD pack (PDF and DOCX) and the starter folder; build mock profiles meanwhile.
4. **Confirmation of the data contract**:
   - whether `talent_check_company_skillsets.json` matches the SQL file
   - which ZS Associates row is correct
   - the exact meaning of tiers CU / AP / AS / EV / CR (ask the facilitator)
   - the exact profile format Role 3 will save, its file location, and how the selected company is passed in
   - whether to add extra output fields (`tier`, `category_name`, `weight`)
5. **Engineering pieces around the scoring logic:**
   - Python module with `run_talent_check(profile, company) -> result`
   - thin API (FastAPI or Flask) for the React frontend; agree who owns the backend glue
   - React UI: company selector, "Run Talent Check" button, results view (bar or radar chart of per-skillset gaps plus score)
   - company data loader (section 5)
6. **Things not yet seen:** the milestone checklist (`RADIX_Talent_Match_Milestone_Checklist.xlsx`, 2 milestones per role, 10 whole-team) and the team roster / role assignments.
7. **Demo readiness:** be able to explain the scoring in one or two sentences; pick one candidate shown against two companies with clearly different results.

---

## 9. Plan

**Should I start building now, or wait for the other roles' data? Start now.** The deadline is 28 Oct, and most of my piece does not depend on their data.

### Build now (no dependencies)
1. SQL-to-JSON company loader
2. Scoring logic (Layer B) against 12 candidate levels and a company's 12 required levels
3. Four mock profiles
4. API endpoint and React UI with fake input

### Do not wait on
- Roles 1 and 2 (JD and resume extraction): no direct dependency
- Role 5: no dependency

### Watch out for
- Not agreeing the level format early and discovering the mismatch at integration time
- Role 3 being late: raise it with the Scrum Master if no save/load loop appears within a day or two

### Suggested order
1. Agree profile format and level source with Role 3 (send the message in section 6 today).
2. Build the loader and export clean JSON.
3. Write the scoring function against mock profiles.
4. Add the API and UI.
5. Test with all four candidates across Google, Microsoft and Oracle FSS and check that results differ visibly.
6. Rehearse the demo.

### Suggested file layout
```
talent_check/
  data/
    staging_company_skill_levels_rows.sql
    companies.json            # generated by the loader
    mock_profiles/
      anny_ro.json
      karthik_subramanian.json
      priya_menon.json
      rohan_verma.json
  backend/
    loader.py                 # SQL -> companies.json
    levels.py                 # Layer A: get_candidate_levels(profile)
    scoring.py                # Layer B: score(candidate_levels, company)
    api.py                    # FastAPI: GET /companies, POST /talent-check
  frontend/                   # React: selector, button, results view
```
