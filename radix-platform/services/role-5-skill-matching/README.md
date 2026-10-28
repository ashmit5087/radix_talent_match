# Role 5 - Skill Matching

Compares one candidate's skills with **one** extracted JD skill list (Role 1 output) and returns a
0-100 score plus matched / partial / needs-review / missing skills, each with a rationale.
Deterministic, offline, no LLM, no API keys. No UI (Role 3 owns that).

## Setup (uv)
```bash
cd apps/skill_matching
uv sync --extra dev
uv run pytest -q
```

## CLI
```bash
uv run python -m skill_matching.cli --candidate <candidate.json> --jd <job-description.json>
```
Exit codes: `0` ok, `2` invalid input (message on stderr), `1` unexpected error.

## API
```bash
uv run uvicorn skill_matching.api:app --host 127.0.0.1 --port 8005
curl -X POST http://127.0.0.1:8005/api/v1/matches -H "Content-Type: application/json" --data-binary @match-request.json
```
| Method | Path | Purpose |
|---|---|---|
| GET | `/health`, `/` | liveness, endpoint pointers |
| POST | `/api/v1/matches` | score one `candidate` against one `job_description` |
| POST | `/api/v1/matches/preview` | per-requirement classification, no score |

Request: `{"candidate": {...skills[]}, "job_description": {source_file, company, role, skills[]}}`.
Required response fields: `jd_source_file`, `match_score`, `matched_skills`, `missing_skills`.
Additive: `partial_matches`, `review_required`, `score_breakdown`, `summary`, `algorithm_version`, `warnings`.
Errors: `400` invalid JSON/contract, `422` JD with no skills, `500` generic message (no traces).
Machine-readable contract: `../../contracts/role5_skill_matching.schema.json`.

## Using Role 4's Talent Check (optional)
`POST /api/v1/matches/with-talent-check` (same body plus `talent_check`) or CLI `--talent-check PATH`.
Per JD skill, using its `category_code` row (`gap = required_level - candidate_level`):
- gap <= 0 or no row: normal matching, full credit
- 0 < gap <= 3: normal matching with unchanged skill-match credit
- gap >= 4 (critical): retains a critical proficiency flag while direct skill-name matching still runs
- Which categories are critical comes from Role 4's `summary.critical_categories` when present (Role 4 is the single source of truth); `CRITICAL_GAP_MIN` is only the fallback.
`readiness_score` is passed through for context only and is not blended into `match_score`.
Threshold lives in `config.CRITICAL_GAP_MIN`.

## Improvement plan (what-if + optional LLM)
`POST /api/v1/improvement-plan` (body: `candidate`, `job_description`, optional `talent_check`, optional `use_llm`) or CLI `--plan [--llm]`.
- **Offline layer (default):** every requirement not at full credit becomes an action with `score_gain`
  (same formula as scoring), ranked by gain, with a cumulative `projected_score_after` and category study steps
  (`recommendations.py`). Action types: `learn_skill`, `strengthen_evidence`, `verify_and_add_evidence`, `raise_level`.
- **LLM layer (opt-in):** `llm_plan.py` uses the `openai` SDK against any OpenAI-compatible endpoint
  (OpenAI, xAI Grok, OpenRouter, Ollama). Set `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` (see `.env.example`) and
  `uv sync --extra llm`. It may only rewrite `steps` and add a `narrative`; scores, gains and the action list stay
  deterministic. Only skill names/categories/statuses/levels are sent (no name, email or evidence text).
  Any failure or missing config falls back to the offline plan with a warning.

## How scoring works
`score = 100 * (matched_weight + 0.5 * partial_weight) / total_required_weight`.
Every JD skill weighs 1.0 unless it carries an optional `importance`. The denominator is the JD's
requirements only, so extra or duplicate candidate skills never raise the score. Each JD requirement
counts once.

Classification order (first hit wins): exact -> approved alias -> composite (data structures +
algorithms = DSA) -> related skill (partial) -> whole-word phrase overlap (partial) -> ambiguous
(`review_required`, 0 points) -> missing. A candidate skill extracted with `low` confidence is
never counted; it becomes `review_required`. All alias/relation tables live in
`src/skill_matching/aliases.py` so reviewers can challenge them.

## Known limitations
- Alias/relation tables are hand-curated and small; unlisted synonyms are reported missing.
- Only the `skills` array is matched; projects/internships/certifications are not mined.
- No proficiency levels; upstream `confidence` is evidence quality, not skill level.
- The runtime `data/` directory intentionally contains no mock or sample candidate data.
  Test-only synthetic fixtures live under `tests/fixtures/` and are never used by the API.
- Optional semantic matching is not implemented; `matcher.SkillMatcher` is the extension point.
- The score is decision support, not a judgment of a person's ability.
