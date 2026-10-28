"""Classify each JD requirement as matched / partial / review_required / missing.

The baseline is deterministic and offline. `SkillMatcher` is a Protocol so an
optional semantic/LLM matcher can be swapped in later without changing the
API contract (spec 4.5). Any such matcher must never let similarity alone
assert a skill as proven.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from .aliases import (
    COMPOSITES,
    CONTAINMENT_BLOCKLIST,
    PARTIAL_RELATIONS,
    REVIEW_RELATIONS,
)
from .config import MAX_EVIDENCE_CHARS, STATUS_SCORE
from .normalizer import atoms, canonical, normalize_text
from .schemas import Confidence, Skill, SkillResult

_CONF_RANK = {"high": 3, "medium": 2, None: 1, "low": 0}


class SkillMatcher(Protocol):
    method_family: str

    def match(
        self, jd_skills: list[Skill], candidate_skills: list[Skill]
    ) -> "MatchOutcome": ...


@dataclass
class MatchOutcome:
    results: list[SkillResult]
    warnings: list[str] = field(default_factory=list)


@dataclass
class _Cand:
    """A de-duplicated candidate skill (all raw entries sharing a canonical key)."""

    key: str
    best: Skill
    names: list[str]

    @property
    def confidence(self) -> Optional[Confidence]:
        return self.best.confidence


def _clip(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    if len(text) <= MAX_EVIDENCE_CHARS:
        return text
    return text[: MAX_EVIDENCE_CHARS - 1].rstrip() + "…"


def _quality(s: Skill) -> tuple[int, int]:
    """Higher is a better representative: confidence, then has-evidence."""
    return (_CONF_RANK[s.confidence], 1 if (s.evidence or "").strip() else 0)


def dedupe_candidate(skills: list[Skill]) -> dict[str, _Cand]:
    """Merge candidate skills sharing a canonical key. Order is preserved."""
    out: dict[str, _Cand] = {}
    for s in skills:
        key = canonical(s.skill_name)
        if not key:
            continue
        cand = out.get(key)
        if cand is None:
            out[key] = _Cand(key=key, best=s, names=[s.skill_name])
        else:
            if s.skill_name not in cand.names:
                cand.names.append(s.skill_name)
            if _quality(s) > _quality(cand.best):
                cand.best = s
    return out


def dedupe_jd(skills: list[Skill]) -> tuple[list[Skill], list[str]]:
    """Collapse duplicate JD requirements so each counts once."""
    seen: dict[str, Skill] = {}
    warnings: list[str] = []
    for s in skills:
        key = canonical(s.skill_name)
        if key in seen:
            warnings.append(
                f"Duplicate JD requirement '{s.skill_name}' merged with "
                f"'{seen[key].skill_name}'; it is counted once."
            )
            continue
        seen[key] = s
    return list(seen.values()), warnings


class DeterministicMatcher:
    """Exact / alias / composite / related-term matching. No network, no LLM."""

    method_family = "deterministic"

    def match(self, jd_skills: list[Skill], candidate_skills: list[Skill]) -> MatchOutcome:
        jd_unique, warnings = dedupe_jd(jd_skills)
        cands = dedupe_candidate(candidate_skills)
        if not cands:
            warnings.append("Candidate has no skills; every requirement is reported missing.")

        # atom index: each individual skill claimed inside a compound candidate skill name
        self._atoms: dict[str, "_Cand"] = {}
        for c in cands.values():
            for a in atoms(c.best.skill_name):
                if a != c.key:
                    self._atoms.setdefault(a, c)

        results = [self._match_one(jd, cands) for jd in jd_unique]

        for jd in jd_unique:
            if jd.confidence == "low":
                warnings.append(
                    f"JD requirement '{jd.skill_name}' was extracted with low confidence; "
                    "verify it against the original posting."
                )

        # One candidate skill supporting several JD requirements: list it, but
        # each requirement still contributes at most once (never inflated).
        usage: dict[str, list[str]] = {}
        for r in results:
            if r.status in ("matched", "partial") and r.candidate_skill:
                usage.setdefault(canonical(r.candidate_skill), []).append(r.skill_name)
        for key, reqs in usage.items():
            if len(reqs) > 1:
                shown = cands[key].names[0] if key in cands else key
                warnings.append(
                    f"Candidate skill '{shown}' supports {len(reqs)} JD requirements "
                    f"({', '.join(reqs)}); each requirement is still scored once."
                )

        return MatchOutcome(results=results, warnings=warnings)

    # ------------------------------------------------------------------ core
    def _match_one(self, jd: Skill, cands: dict[str, _Cand]) -> SkillResult:
        key = canonical(jd.skill_name)
        weight = float(jd.importance) if jd.importance else 1.0

        # 1. exact / alias ------------------------------------------------
        if key in cands:
            c = cands[key]
            exact = normalize_text(jd.skill_name) == normalize_text(c.best.skill_name)
            method = "exact" if exact else "alias"
            how = (
                "the normalized skill names are identical"
                if exact
                else "an approved alias maps both names to the same skill"
            )
            return self._build(jd, weight, "matched", [c], method, how)

        # 2. composite (e.g. data structures + algorithms => DSA) ----------
        for needed in COMPOSITES.get(key, []):
            if all(n in cands for n in needed):
                parts = [cands[n] for n in sorted(needed)]
                joined = " + ".join(p.best.skill_name for p in parts)
                return self._build(
                    jd, weight, "matched", parts, "composite",
                    f"the candidate lists all required components ({joined})",
                )

        # 2b. compound candidate name that explicitly lists this skill as one of its parts
        hit = self._atoms.get(key)
        if hit is not None:
            return self._build(
                jd, weight, "matched", [hit], "compound_atom",
                f"the candidate skill '{hit.best.skill_name}' explicitly lists '{jd.skill_name}' as one of its parts",
            )

        # 3. related (partial) -------------------------------------------
        for ck in cands:
            reason = PARTIAL_RELATIONS.get((key, ck))
            if reason:
                return self._build(
                    jd, weight, "partial", [cands[ck]], "related_skill", reason
                )

        # 4. phrase containment (partial, conservative) ------------------
        contained = self._containment(key, cands)
        if contained is not None:
            c, direction = contained
            return self._build(
                jd, weight, "partial", [c], "phrase_containment",
                f"the candidate skill and the JD term overlap as a whole-word phrase "
                f"({direction}); related, but not proven equivalent",
            )

        # 5. ambiguous / generic -> human review -------------------------
        for ck in cands:
            reason = REVIEW_RELATIONS.get((key, ck))
            if reason:
                return self._build(
                    jd, weight, "review_required", [cands[ck]], "ambiguous_relation", reason
                )

        # 6. missing -----------------------------------------------------
        return self._build(jd, weight, "missing", [], None, "")

    @staticmethod
    def _containment(key: str, cands: dict[str, _Cand]):
        """Whole-word phrase containment, either direction. Blocklisted/very
        short terms never qualify (avoids 'go' in 'go to market', etc.)."""
        jd_tokens = key.split()
        for ck, c in cands.items():
            if ck == key:
                continue
            ct = ck.split()
            for small, big, direction in (
                (jd_tokens, ct, "candidate phrase contains the JD term"),
                (ct, jd_tokens, "JD phrase contains the candidate term"),
            ):
                small_key = " ".join(small)
                if len(small_key) <= 2 or small_key in CONTAINMENT_BLOCKLIST:
                    continue
                if len(small) >= len(big):
                    continue
                n = len(small)
                if any(big[i : i + n] == small for i in range(len(big) - n + 1)):
                    return c, direction
        return None

    # ----------------------------------------------------------- assembling
    def _build(
        self,
        jd: Skill,
        weight: float,
        status: str,
        cands: list[_Cand],
        method: Optional[str],
        how: str,
    ) -> SkillResult:
        considered = [n for c in cands for n in c.names]

        if status == "missing":
            return SkillResult(
                skill_name=jd.skill_name,
                category_code=jd.category_code,
                status="missing",
                jd_evidence=_clip(jd.evidence),
                jd_confidence=jd.confidence,
                rationale="No candidate skill provided sufficient matching evidence.",
                weight=weight,
                contribution=0.0,
            )

        primary = max(cands, key=lambda c: _quality(c.best))
        best = primary.best
        evidence = _clip(best.evidence)
        shown_skill = best.skill_name
        if method == "composite":
            # Show every component and its own evidence; invent nothing.
            shown_skill = " + ".join(c.best.skill_name for c in cands)
            ev_parts = [
                f"{c.best.skill_name}: {c.best.evidence.strip()}"
                for c in cands
                if (c.best.evidence or "").strip()
            ]
            evidence = _clip(" | ".join(ev_parts)) if ev_parts else None
        notes: list[str] = []

        # Low-confidence candidate extraction never yields a strong match.
        if status in ("matched", "partial") and all(
            c.confidence == "low" for c in cands
        ):
            notes.append(
                "the candidate skill was extracted with low confidence, so it is "
                "flagged for review instead of counted"
            )
            status = "review_required"

        label = {
            "matched": "Matched",
            "partial": "Partial match",
            "review_required": "Needs review",
        }[status]
        rationale = f"{label}: candidate skill '{shown_skill}' vs JD '{jd.skill_name}' - {how}."
        if status == "review_required" and notes:
            rationale = (
                f"Needs review: candidate skill '{shown_skill}' appears to match "
                f"JD '{jd.skill_name}' ({how}), but " + "; ".join(notes) + "."
            )
        if evidence is None:
            rationale += " The candidate supplied no evidence for this skill; the match rests on the skill name only."

        return SkillResult(
            skill_name=jd.skill_name,
            category_code=jd.category_code,
            status=status,  # type: ignore[arg-type]
            candidate_skill=shown_skill,
            candidate_skills_considered=considered,
            jd_evidence=_clip(jd.evidence),
            candidate_evidence=evidence,
            candidate_evidence_present=evidence is not None,
            jd_confidence=jd.confidence,
            candidate_confidence=best.confidence,
            match_method=method,
            rationale=rationale,
            weight=weight,
            contribution=round(weight * STATUS_SCORE[status], 6),
        )
