"""Use Role 4's Talent Check result to shortcut and refine Role 5 scoring.

Per JD skill, by its category_code:
  * no Role 4 row / levels unknown / gap <= 0 -> normal matching, full credit
  * 0 < gap <= 3 (scored gap)                 -> normal matching with unchanged skill-match credit
  * gap > 3 (critical gap)                    -> retain the critical flag while matching still runs

Critical-gap skills retain direct skill-name match credit, while the critical flag drives
proficiency-growth recommendations. Role 4's readiness_score is passed through for context
only and is NOT blended into match_score (they answer different questions).
"""

from __future__ import annotations

from typing import Optional

from .config import CRITICAL_GAP_MIN
from .matcher import DeterministicMatcher, SkillMatcher, dedupe_jd
from .normalizer import normalize_text
from .schemas import (
    CandidateProfile,
    JobDescription,
    MatchResponse,
    Skill,
    SkillResult,
    TalentCheckContext,
    TalentCheckResult,
)


def _levels(tc: TalentCheckResult) -> dict[str, tuple[int, int, int]]:
    """category -> (required, candidate, gap). Worst (largest) gap wins on duplicates."""
    out: dict[str, tuple[int, int, int]] = {}
    for row in tc.skillset_gap:
        if row.required_level is None or row.candidate_level is None:
            continue
        gap = row.required_level - row.candidate_level
        prev = out.get(row.category_code)
        if prev is None or gap > prev[2]:
            out[row.category_code] = (row.required_level, row.candidate_level, gap)
    return out


def _critical_rule(tc: TalentCheckResult, levels: dict[str, tuple[int, int, int]]) -> tuple[set[str], int, str]:
    """Which categories are critical. Role 4 is the source of truth whenever it sends
    summary.critical_categories; otherwise fall back to the local threshold."""
    summ = tc.summary
    if summ is not None and summ.critical_categories is not None:
        return set(summ.critical_categories), summ.critical_gap_min or CRITICAL_GAP_MIN, "from Talent Check summary"
    return {c for c, (_, _, g) in levels.items() if g >= CRITICAL_GAP_MIN}, CRITICAL_GAP_MIN, "derived locally"


def _critical_result(jd: Skill, req: int, cand: int, gap: int, threshold: int) -> SkillResult:
    return SkillResult(
        skill_name=jd.skill_name,
        category_code=jd.category_code,
        status="missing",
        jd_evidence=jd.evidence,
        jd_confidence=jd.confidence,
        critical_gap=True,
        category_required_level=req,
        category_candidate_level=cand,
        category_gap=gap,
        level_factor=0.0,
        match_method="talent_check_critical_gap",
        rationale=(
            f"Critical gap from Talent Check: {jd.category_code} required level {req}, "
            f"candidate level {cand} (gap {gap}, critical when gap >= {threshold}). "
            "Skill matching was skipped for this requirement."
        ),
        weight=float(jd.importance) if jd.importance else 1.0,
        contribution=0.0,
    )


def run_match_with_talent_check(
    candidate: CandidateProfile,
    jd: JobDescription,
    tc: TalentCheckResult,
    matcher: Optional[SkillMatcher] = None,
) -> MatchResponse:
    # imported here to avoid a circular import with service.py
    from .service import _DEFAULT_MATCHER, assemble_response

    matcher = matcher or _DEFAULT_MATCHER
    levels = _levels(tc)
    crit_set, threshold, rule_source = _critical_rule(tc, levels)
    jd_unique, warnings = dedupe_jd(jd.skills)

    # Talent Check describes proficiency/readiness, while Role 5 measures
    # skill-name overlap. A critical proficiency gap must not erase a skill
    # that the candidate actually lists; otherwise valid profiles routinely
    # collapse to a zero match score. Match every requirement first, then
    # attach the Talent Check context below.
    to_match: list[tuple[int, Skill]] = list(enumerate(jd_unique))
    outcome = matcher.match([s for _, s in to_match], candidate.skills)
    matched_results = list(outcome.results) if outcome else []
    warnings += outcome.warnings

    # Matcher output keeps input order, so zip back onto original positions.
    by_index: dict[int, SkillResult] = {}
    for (i, _), r in zip(to_match, matched_results):
        lv = levels.get(r.category_code)
        if lv:
            req, cand, gap = lv
            r.category_required_level, r.category_candidate_level, r.category_gap = req, cand, gap
            r.critical_gap = r.category_code in crit_set
            if r.status in ("matched", "partial"):
                r.level_factor = 1.0
            if r.critical_gap:
                r.rationale += (
                    f" Talent Check flags a critical {r.category_code} proficiency gap "
                    f"(required {req}, candidate {cand}); skill-name match credit is retained."
                )
            elif 0 < gap and r.status in ("matched", "partial"):
                r.rationale += (
                    f" Talent Check records a {r.category_code} proficiency gap "
                    f"(required {req}, candidate {cand}); skill-match credit is unchanged."
                )
        by_index[i] = r
    results = [by_index[i] for i in sorted(by_index)]

    if tc.company and jd.company and normalize_text(tc.company) != normalize_text(jd.company):
        warnings.append(
            f"Talent Check company '{tc.company}' differs from JD company '{jd.company}'; "
            "category levels may not describe this employer's bar."
        )

    scored = sorted(c for c, (_, _, g) in levels.items() if g > 0 and c not in crit_set)
    crit = sorted(crit_set)
    ctx = TalentCheckContext(
        readiness_score=tc.readiness_score,
        critical_gap_threshold=f"gap >= {threshold} (required_level - candidate_level), {rule_source}",
        critical_categories=crit,
        scored_gap_categories=scored,
        handling=(
            "Talent Check proficiency gaps are reported as context while direct skill-name "
            "match credit remains unchanged; readiness_score is informational only and never "
            "blended into match_score."
        ),
    )
    return assemble_response(jd, results, warnings, ctx)
