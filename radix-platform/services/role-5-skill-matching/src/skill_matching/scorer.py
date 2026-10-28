"""Weighted required-skill coverage (spec 4.3).

    score = 100 * sum(w_i * s_i) / sum(w_i)
    s_i = 1.0 matched, 0.5 partial, 0.0 missing / review_required

The denominator is the JD's required weight only, so unrelated or duplicate
candidate skills can never raise the score.
"""

from __future__ import annotations

import math

from .schemas import ScoreBreakdown, SkillResult

FORMULA = "100 * (matched_weight + 0.5 * partial_weight) / total_required_weight"


def compute_score(results: list[SkillResult]) -> tuple[int, ScoreBreakdown]:
    if not results:
        raise ValueError("cannot score an empty list of JD requirements")

    totals = {"matched": 0.0, "partial": 0.0, "review_required": 0.0, "missing": 0.0}
    for r in results:
        totals[r.status] += r.weight
    total = sum(totals.values())
    if total <= 0:
        raise ValueError("total required weight must be positive")

    earned = sum(r.contribution for r in results)
    # Round half up, deterministically; clamp for float safety.
    score = max(0, min(100, int(math.floor(100.0 * earned / total + 0.5))))

    equal = len({r.weight for r in results}) == 1 and results[0].weight == 1.0
    breakdown = ScoreBreakdown(
        scoring_method="weighted_required_skill_coverage",
        matched_weight=round(totals["matched"], 6),
        partial_weight=round(totals["partial"], 6),
        review_required_weight=round(totals["review_required"], 6),
        missing_weight=round(totals["missing"], 6),
        total_required_weight=round(total, 6),
        formula=FORMULA,
        weighting=(
            "equal (every JD skill weight 1.0; no importance supplied)"
            if equal
            else "custom (JD skills carried an importance value)"
        ),
    )
    return score, breakdown
