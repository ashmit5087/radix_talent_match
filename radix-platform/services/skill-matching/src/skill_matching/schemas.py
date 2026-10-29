"""Pydantic request/response models for Role 5.

Inputs are tolerant of optional fields but validate the required ones.
Unknown extra fields from other roles are ignored, not rejected, so the
shared contract can grow without breaking Role 5.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

CategoryCode = Literal[
    "COD", "DSA", "OOD", "APTI", "COMM", "AI",
    "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER",
]
Confidence = Literal["high", "medium", "low"]
MatchStatus = Literal["matched", "partial", "missing", "review_required"]


class Skill(BaseModel):
    """Shared skill object (brief page 9)."""

    model_config = ConfigDict(extra="ignore")

    skill_name: str
    category_code: CategoryCode = "OTHER"
    evidence: Optional[str] = None
    confidence: Optional[Confidence] = None
    # Optional, not in the brief: lets the team add JD importance later.
    importance: Optional[float] = Field(default=None, gt=0)

    @field_validator("skill_name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("skill_name must not be blank")
        return v.strip()

    @field_validator("category_code", mode="before")
    @classmethod
    def _category_upper(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return "OTHER"
        return v.strip().upper() if isinstance(v, str) else v

    @field_validator("confidence", mode="before")
    @classmethod
    def _confidence_lower(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
            return v or None
        return v


class CandidateProfile(BaseModel):
    """Role 3 profile or Role 2 resume skill list. Only `skills` is used."""

    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    skills: list[Skill] = Field(default_factory=list)


class JobDescription(BaseModel):
    """Role 1 JD skill list."""

    model_config = ConfigDict(extra="ignore")

    source_type: Optional[str] = "jd"
    source_file: str = ""
    company: Optional[str] = None
    role: Optional[str] = None
    skills: list[Skill]

    @field_validator("skills")
    @classmethod
    def _skills_not_empty(cls, v: list[Skill]) -> list[Skill]:
        if not v:
            raise ValueError("job description must contain at least one skill")
        return v


class MatchRequest(BaseModel):
    candidate: CandidateProfile
    job_description: JobDescription


class SkillResult(BaseModel):
    """One JD requirement, fully accounted for."""

    skill_name: str
    category_code: CategoryCode
    status: MatchStatus
    candidate_skill: Optional[str] = None
    candidate_skills_considered: list[str] = Field(default_factory=list)
    jd_evidence: Optional[str] = None
    candidate_evidence: Optional[str] = None
    candidate_evidence_present: bool = False
    jd_confidence: Optional[Confidence] = None
    candidate_confidence: Optional[Confidence] = None
    match_method: Optional[str] = None
    # Filled only when a Role 4 Talent Check result is supplied.
    critical_gap: bool = False
    category_required_level: Optional[int] = None
    category_candidate_level: Optional[int] = None
    category_gap: Optional[int] = None
    level_factor: Optional[float] = None
    rationale: str
    weight: float
    contribution: float


class ScoreBreakdown(BaseModel):
    scoring_method: str
    matched_weight: float
    partial_weight: float
    review_required_weight: float
    missing_weight: float
    total_required_weight: float
    formula: str
    weighting: str


class MatchResponse(BaseModel):
    # Required by the brief (page 9) - never rename or remove.
    jd_source_file: str
    match_score: int = Field(ge=0, le=100)
    matched_skills: list[SkillResult]
    missing_skills: list[SkillResult]
    # Additive explanation fields.
    company: Optional[str] = None
    role: Optional[str] = None
    partial_matches: list[SkillResult] = Field(default_factory=list)
    review_required: list[SkillResult] = Field(default_factory=list)
    score_breakdown: ScoreBreakdown
    talent_check_context: Optional[TalentCheckContext] = None
    summary: str
    algorithm_version: str
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Decision support only: this score reflects skill-name/alias overlap "
        "between two upstream extractions, not a judgment of a person's ability."
    )


class SkillsetGap(BaseModel):
    """One row of Role 4's `skillset_gap` list (brief page 10)."""

    model_config = ConfigDict(extra="ignore")

    category_code: CategoryCode
    required_level: Optional[int] = Field(default=None, ge=1, le=10)
    candidate_level: Optional[int] = Field(default=None, ge=0, le=10)
    gap: Optional[bool] = None

    @field_validator("category_code", mode="before")
    @classmethod
    def _cat_upper(cls, v):
        return v.strip().upper() if isinstance(v, str) else v


class TalentCheckSummary(BaseModel):
    """Role 4 summary block. Role 4 is the single source of truth for which categories are critical."""

    model_config = ConfigDict(extra="ignore")

    critical_categories: Optional[list[str]] = None
    critical_gap_min: Optional[int] = Field(default=None, ge=1, le=10)

    @field_validator("critical_categories", mode="before")
    @classmethod
    def _codes_upper(cls, v):
        if isinstance(v, list):
            return [c.strip().upper() for c in v if isinstance(c, str)]
        return v


class TalentCheckResult(BaseModel):
    """Role 4 output. Only levels and (informationally) readiness_score are used."""

    model_config = ConfigDict(extra="ignore")

    company: Optional[str] = None
    skillset_gap: list[SkillsetGap] = Field(default_factory=list)
    readiness_score: Optional[float] = Field(default=None, ge=0, le=100)
    summary: Optional[TalentCheckSummary] = None


class TalentCheckContext(BaseModel):
    readiness_score: Optional[float] = None
    critical_gap_threshold: str
    critical_categories: list[str] = Field(default_factory=list)
    scored_gap_categories: list[str] = Field(default_factory=list)
    handling: str


class PreviewResponse(BaseModel):
    jd_source_file: str
    results: list[SkillResult]
    warnings: list[str] = Field(default_factory=list)


class ImprovementAction(BaseModel):
    skill_name: str
    category_code: CategoryCode
    action_type: Literal["learn_skill", "strengthen_evidence", "verify_and_add_evidence", "raise_level"]
    current_status: MatchStatus
    critical_gap: bool = False
    level_needed: Optional[str] = None  # e.g. "3 -> 8" from Talent Check
    score_gain: float  # points on the 0-100 scale if this action is fully closed
    projected_score_after: int  # cumulative, after this action and all above it
    steps: list[str]
    why: str


class ImprovementPlan(BaseModel):
    current_score: int
    projected_score_if_all_closed: int
    actions: list[ImprovementAction]
    source: Literal["deterministic", "deterministic+llm"] = "deterministic"
    narrative: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Projected scores are what-if estimates from the same scoring formula. Closing a gap "
        "means the skill (and its evidence) would then appear in the profile and, when a Talent "
        "Check is supplied, that category's level would also reach the required level. It is not "
        "a prediction of any hiring outcome."
    )
