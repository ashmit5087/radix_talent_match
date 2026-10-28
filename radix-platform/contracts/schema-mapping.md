# RADIX Platform — Schema Mapping

How data shapes transform between roles. Reference for adapter logic in `services.ts` and `contracts.ts`.

---

## Role 2 → Role 3: `ResumeExtract` → `ProfileCreate`

**Adapter:** `resumeToProfile()` in `services.ts`

| `ResumeExtract` field | → | `ProfileCreate` field | Notes |
|---|---|---|---|
| `skills[].skill_name` | → | `skills[].skill_name` | Direct |
| `skills[].category_code` | → | `skills[].category_code` | Direct |
| `skills[].evidence` | → | `skills[].evidence` | Falls back to `"Extracted from resume"` |
| `skills[].confidence` | → | `skills[].confidence` | Direct (`high/medium/low`) |
| _(implicit)_ | → | `skills[].source` | Always `"extracted"` |
| _(user-provided)_ | → | `personal_info.full_name` | Entered in form |
| _(user-provided)_ | → | `personal_info.email` | Entered in form |
| _(user-provided)_ | → | `personal_info.location` | Optional |

---

## Role 3 → Role 4: `ProfileResponse` → Talent Check payload

**Used in:** talent check call in `app.assessments.new.tsx`

| `ProfileResponse` field | → | Role 4 `candidate_profile` field | Notes |
|---|---|---|---|
| `personal_info.full_name` | → | `name` | Display name |
| `personal_info.email` | → | `email` | Contact |
| `skills[].skill_name` | → | `skills[].name` | Role 4 reads skill name |
| `skills[].category_code` | → | `skills[].category` | Used for competency classification |
| `skills[].confidence` | → | `skills[].confidence` | Used in saturating curve weighting |
| `skills[].evidence` | → | `skills[].evidence` | Used for evidence point calculation |

**Role 4 internal mapping:** `get_candidate_levels()` maps skill names to 12 RADIX category codes (SE, DS, ML, DE, Cloud, DevOps, Sys, Sec, PM, BA, QA, Agile) and computes levels 1–10 using the evidence point accumulator.

---

## Role 1 + Role 3 → Role 5: `JDAnalysis` + `ProfileResponse` → `MatchRequest`

**Adapter:** `runFullAssessment()` in `services.ts`

| Source | Field | → | `MatchRequest` field |
|--------|-------|---|---------------------|
| `ProfileResponse` | `skills[].name` | → | `candidate.skills[].skill_name` |
| `ProfileResponse` | `skills[].category` | → | `candidate.skills[].category_code` |
| `ProfileResponse` | `skills[].evidence` | → | `candidate.skills[].evidence` |
| `ProfileResponse` | `skills[].confidence` | → | `candidate.skills[].confidence` |
| `JDAnalysis` | _(whole object)_ | → | `job_description` | Full JDAnalysis object |
| `TalentCheckResult` | _(optional)_ | → | `talent_check` | `null` if not included |

---

## Role 5 Output: `MatchResult` Schema

```typescript
interface MatchResult {
  overall_score: number;          // 0-100 deterministic weighted score
  matched_skills: {
    skill_name: string;
    category_code: string;
    confidence: "high" | "medium" | "low";
    jd_evidence: string;
  }[];
  gap_skills: {
    skill_name: string;
    category_code: string;
    priority: "critical" | "important" | "nice-to-have";
    jd_evidence: string;
  }[];
  category_breakdown: Record<string, {
    matched: number;
    required: number;
    score: number;
  }>;
}
```

---

## Role 5 Output: `ImprovementPlan` Schema

```typescript
interface ImprovementPlan {
  summary: string;
  steps: {
    skill_name: string;
    category_code: string;
    current_level: "none" | "low" | "medium";
    target_level: "medium" | "high";
    priority: "critical" | "important" | "nice-to-have";
    action: string;
    resources?: string[];
    estimated_weeks?: number;
  }[];
  what_if_score?: number;  // projected score if all steps completed
}
```

---

## Role 4 Competency Category Codes

| Code | Full Name |
|------|-----------|
| `SE` | Software Engineering |
| `DS` | Data Structures & Algorithms |
| `ML` | Machine Learning / AI |
| `DE` | Data Engineering |
| `Cloud` | Cloud Platforms |
| `DevOps` | DevOps / CI-CD |
| `Sys` | System Design |
| `Sec` | Security |
| `PM` | Product Management |
| `BA` | Business Analysis |
| `QA` | Quality Assurance |
| `Agile` | Agile / Scrum |

---

## Confidence Level Semantics

| Value | Meaning | Evidence Points (Role 4) |
|-------|---------|--------------------------|
| `high` | Strong direct evidence | 3 points |
| `medium` | Moderate evidence | 2 points |
| `low` | Weak/inferred evidence | 1 point |

