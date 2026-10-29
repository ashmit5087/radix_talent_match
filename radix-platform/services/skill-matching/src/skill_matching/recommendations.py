"""Deterministic, offline improvement plan: what-if scoring + ranked gap actions.

For every requirement that is not yet earning full credit we compute how many score
points closing it would add (same formula as scoring), rank actions by that gain
(critical gaps first on ties), and project the cumulative score. No model is involved.
The optional LLM layer (llm_plan.py) may only rewrite the `steps` text and add a
narrative; it never changes a score, a gain or the action list.
"""

from __future__ import annotations

import math

from .schemas import ImprovementAction, ImprovementPlan, MatchResponse, SkillResult

# Generic, hand-written study steps per RADIX category. {skill} is the JD skill name.
CATEGORY_STEPS: dict[str, list[str]] = {
    "COD": ["Build a small end-to-end project that uses {skill} and publish it with a README.",
            "Do ~15 focused exercises in {skill}, then review idiomatic patterns in its docs."],
    "DSA": ["Practice problems by topic (arrays, hashing, trees, graphs, DP) and note the pattern each uses.",
            "Implement the core structures for {skill} from scratch and state their complexities."],
    "OOD": ["Redesign a small project using SOLID principles and 2-3 design patterns.",
            "Write a short class diagram and explain each design trade-off for {skill}."],
    "SQL": ["Practice joins, aggregation, window functions and indexing on a sample dataset.",
            "Design a normalized schema for a small app and write the queries it needs ({skill})."],
    "SYSD": ["Study and sketch designs for 3 classic systems (URL shortener, chat, feed).",
             "Practice stating requirements, estimating load and naming bottlenecks for {skill}."],
    "NETW": ["Trace a request end to end (DNS, TCP, TLS, HTTP) and explain each hop.",
             "Build a tiny client/server program to apply {skill}."],
    "OS": ["Review processes, threads, scheduling, memory and file systems with small experiments.",
           "Write a short program that demonstrates a core {skill} concept (e.g. a scheduler or lock)."],
    "CLOUD": ["Deploy a small app on one cloud provider's free tier and document the steps.",
              "Learn the core services behind {skill} (compute, storage, networking, IAM)."],
    "AI": ["Complete one hands-on {skill} project with a clear dataset, metric and write-up.",
           "Explain the model/approach you used and its limitations in the project README."],
    "COMM": ["Write a one-page summary of a project for a non-technical reader.",
             "Practice a 2-minute explanation of your work and get feedback."],
    "APTI": ["Take timed aptitude practice sets and review every wrong answer.",
             "Track weak topics and revisit them weekly."],
    "SWE": ["Use {skill} in a team-style workflow (branches, reviews, tests, CI) on a project.",
            "Add tests and a README showing how you apply {skill}."],
    "OTHER": ["Do a small hands-on project with {skill} and write down what you built.",
              "Add concrete evidence of {skill} to your profile."],
}


def _steps(category: str, skill: str) -> list[str]:
    return [t.format(skill=skill) for t in CATEGORY_STEPS.get(category, CATEGORY_STEPS["OTHER"])]


def _all_results(resp: MatchResponse) -> list[SkillResult]:
    return resp.matched_skills + resp.partial_matches + resp.review_required + resp.missing_skills


def _classify(r: SkillResult) -> tuple[str, list[str], str] | None:
    """(action_type, steps, why) for results below full credit, else None."""
    full = r.weight
    if (
        r.status == "matched"
        and r.category_candidate_level is not None
        and r.category_required_level is not None
        and r.category_candidate_level < r.category_required_level
    ):
        need = f"{r.category_candidate_level} -> {r.category_required_level}"
        steps = [
            f"Raise your {r.category_code} level toward the bar ({need}) with harder, more advanced work.",
            *_steps(r.category_code, r.skill_name)[:1],
        ]
        return "raise_level", steps, (
            f"Listed and matched, but Talent Check shows a {r.category_code} "
            f"proficiency gap ({need})."
        )
    if r.contribution >= full - 1e-9:
        return None
    if r.status == "missing":
        why = (
            f"Critical gap per Talent Check (level {r.category_candidate_level} vs required "
            f"{r.category_required_level})." if r.critical_gap
            else f"'{r.skill_name}' is required by the JD and nothing in the profile shows it."
        )
        return "learn_skill", _steps(r.category_code, r.skill_name), why
    if r.status == "partial":
        reason = r.rationale.split(" - ", 1)[-1].split(" Credit scaled", 1)[0].split(" The candidate supplied", 1)[0].rstrip(". ")
        steps = [f"Close the specific difference: {reason}.",
                 f"Add explicit evidence of '{r.skill_name}' itself, not only a related skill."]
        return "strengthen_evidence", steps, f"Only a related skill is listed ('{r.candidate_skill}')."
    if r.status == "review_required":
        steps = [f"Confirm you actually have '{r.skill_name}' and add it by name with evidence.",
                 "Add one concrete example (project, task or result) as evidence."]
        return "verify_and_add_evidence", steps, "The match is ambiguous or low-confidence, so it earns no credit yet."
    return None


def build_plan(resp: MatchResponse) -> ImprovementPlan:
    results = _all_results(resp)
    total = resp.score_breakdown.total_required_weight
    earned = sum(r.contribution for r in results)

    raw = []
    for r in results:
        info = _classify(r)
        if info is None:
            continue
        gain_w = r.weight - r.contribution
        raw.append((gain_w, r, info))
    # biggest gain first; critical gaps, then input order, break ties deterministically
    raw.sort(key=lambda t: (-t[0], not t[1].critical_gap, t[1].skill_name.lower()))

    actions: list[ImprovementAction] = []
    running = earned
    for gain_w, r, (atype, steps, why) in raw:
        running += gain_w
        projected = max(0, min(100, int(math.floor(100.0 * running / total + 0.5))))
        need = None
        if r.category_required_level is not None and r.category_candidate_level is not None:
            need = f"{r.category_candidate_level} -> {r.category_required_level}"
        actions.append(ImprovementAction(
            skill_name=r.skill_name, category_code=r.category_code, action_type=atype,
            current_status=r.status, critical_gap=r.critical_gap, level_needed=need,
            score_gain=round(100.0 * gain_w / total, 1), projected_score_after=projected,
            steps=steps, why=why,
        ))
    return ImprovementPlan(
        current_score=resp.match_score,
        projected_score_if_all_closed=actions[-1].projected_score_after if actions else resp.match_score,
        actions=actions,
    )
