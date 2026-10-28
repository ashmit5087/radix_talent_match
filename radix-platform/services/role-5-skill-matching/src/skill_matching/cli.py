"""Terminal CLI for Role 5.

    python -m skill_matching.cli --candidate C.json --jd J.json [--format text|json]

Exit codes: 0 success, 2 invalid input / contract, 1 unexpected error.
Errors go to stderr. Candidate emails and other personal fields are never printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .schemas import MatchResponse, SkillResult
from .service import InvalidInputError, improvement_plan_raw, match_raw, match_with_talent_check_raw

MAX_FILE_BYTES = 5 * 1024 * 1024


def _load_json(path_str: str, label: str):
    path = Path(path_str)
    if not path.is_file():
        raise InvalidInputError(f"{label} file not found or not a regular file: {path_str}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise InvalidInputError(f"{label} file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB")
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise InvalidInputError(f"{label} file is not valid JSON ({exc.msg} at line {exc.lineno})")
    except UnicodeDecodeError:
        raise InvalidInputError(f"{label} file is not valid UTF-8 text")
    except OSError as exc:
        raise InvalidInputError(f"cannot read {label} file: {exc.strerror}")


def _skill_line(r: SkillResult) -> list[str]:
    cand = f" <- {r.candidate_skill}" if r.candidate_skill else ""
    lines = [f"  - {r.skill_name} [{r.category_code}]{cand}"]
    lines.append(f"      {r.rationale}")
    if r.candidate_evidence:
        lines.append(f"      candidate evidence: {r.candidate_evidence}")
    if r.jd_evidence:
        lines.append(f"      JD evidence: {r.jd_evidence}")
    return lines


def render_text(resp: MatchResponse, candidate_name: str | None) -> str:
    out: list[str] = []
    title = f"{resp.role or 'Role'} @ {resp.company or 'Company'}"
    out.append(f"SKILL MATCH  |  JD: {resp.jd_source_file or '(unnamed)'}  |  {title}")
    if candidate_name:
        out.append(f"Candidate: {candidate_name}")
    out.append("=" * 72)
    out.append(f"MATCH SCORE: {resp.match_score}/100")
    out.append(resp.summary)
    b = resp.score_breakdown
    out.append(
        f"({b.formula}; matched={b.matched_weight:g}, partial={b.partial_weight:g}, "
        f"total={b.total_required_weight:g}; weighting: {b.weighting})"
    )
    sections = [
        ("MATCHED", resp.matched_skills),
        ("PARTIAL (counts 0.5, review recommended)", resp.partial_matches),
        ("NEEDS REVIEW (counts 0)", resp.review_required),
        ("MISSING - gap list", resp.missing_skills),
    ]
    for title_, items in sections:
        out.append("")
        out.append(f"{title_}: {len(items)}")
        if not items:
            out.append("  (none)")
        for r in items:
            out.extend(_skill_line(r))
    tc = resp.talent_check_context
    if tc:
        out.append("")
        out.append(f"TALENT CHECK (Role 4): readiness {tc.readiness_score if tc.readiness_score is not None else 'n/a'} (informational)")
        out.append(f"  critical gaps ({tc.critical_gap_threshold}): {', '.join(tc.critical_categories) or 'none'}")
        out.append(f"  scored gaps (1-3): {', '.join(tc.scored_gap_categories) or 'none'}")
    if resp.warnings:
        out.append("")
        out.append("WARNINGS:")
        out.extend(f"  ! {w}" for w in resp.warnings)
    out.append("")
    out.append(resp.disclaimer)
    return "\n".join(out)


def render_plan(plan) -> str:
    out = ["", "=" * 72,
           f"IMPROVEMENT PLAN ({plan.source}): {plan.current_score} -> {plan.projected_score_if_all_closed} if every gap is closed"]
    if plan.narrative:
        out.append(plan.narrative)
    for i, a in enumerate(plan.actions, 1):
        crit = " [CRITICAL]" if a.critical_gap else ""
        lvl = f" (level {a.level_needed})" if a.level_needed else ""
        out.append(f"{i}. {a.skill_name} [{a.category_code}]{crit}{lvl}: +{a.score_gain} pts -> {a.projected_score_after}  ({a.action_type})")
        out.append(f"     why: {a.why}")
        out.extend(f"     - {st}" for st in a.steps)
    for w in plan.warnings:
        out.append(f"  ! {w}")
    out.append(plan.disclaimer)
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skill-match",
        description="Score one candidate against one extracted JD skill list.",
    )
    p.add_argument("--candidate", required=True, metavar="PATH", help="candidate/profile JSON")
    p.add_argument("--jd", required=True, metavar="PATH", help="Role 1 JD skill-list JSON")
    p.add_argument("--talent-check", metavar="PATH", help="optional Role 4 Talent Check result JSON")
    p.add_argument("--plan", action="store_true", help="also print the improvement plan")
    p.add_argument("--llm", action="store_true", help="with --plan: rewrite steps via an OpenAI-compatible LLM (env-configured); falls back offline")
    p.add_argument("--format", choices=("text", "json"), default="text")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        candidate = _load_json(args.candidate, "candidate")
        jd = _load_json(args.jd, "jd")
        tc = _load_json(args.talent_check, "talent-check") if args.talent_check else None
        plan = None
        if args.plan or args.llm:
            resp, plan = improvement_plan_raw(candidate, jd, tc, use_llm=args.llm)
        elif tc is not None:
            resp = match_with_talent_check_raw(candidate, jd, tc)
        else:
            resp = match_raw(candidate, jd)
    except InvalidInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - never leak a traceback to the terminal user
        print(f"error: unexpected failure ({type(exc).__name__})", file=sys.stderr)
        return 1

    if args.format == "json":
        out = resp.model_dump(mode="json")
        if plan is not None:
            out = {"match": out, "improvement_plan": plan.model_dump(mode="json")}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        name = candidate.get("name") if isinstance(candidate, dict) else None
        print(render_text(resp, name if isinstance(name, str) else None))
        if plan is not None:
            print(render_plan(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
