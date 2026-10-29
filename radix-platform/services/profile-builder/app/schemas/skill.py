from enum import Enum
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator


class CategoryCode(str, Enum):
    COD = "COD"      # Coding
    DSA = "DSA"      # Data Structures & Algorithms
    OOD = "OOD"      # Object-Oriented Design
    APTI = "APTI"    # Aptitude
    COMM = "COMM"    # Communication
    AI = "AI"        # AI / Machine Learning
    CLOUD = "CLOUD"  # Cloud Computing
    SQL = "SQL"      # SQL & Databases
    SWE = "SWE"      # Software Engineering
    SYSD = "SYSD"    # System Design
    NETW = "NETW"    # Networking
    OS = "OS"        # Operating Systems
    OTHER = "OTHER"  # Fallback for other skills


ConfidenceLevel = Literal["high", "medium", "low"]


def normalize_confidence_value(v: Union[float, int, str]) -> tuple[ConfidenceLevel, Optional[float]]:
    """
    Deterministic mapping for confidence alignment:
      - String 'high', 'medium', 'low' -> direct canonical level
      - Numeric:
          >= 0.80 -> 'high'
          >= 0.50 -> 'medium'
          <  0.50 -> 'low'
    Returns (canonical_level, raw_numeric_value_or_none)
    """
    if isinstance(v, (int, float)):
        f_val = float(v)
        if not (0.0 <= f_val <= 1.0):
            raise ValueError(f"Numeric confidence must be between 0.0 and 1.0. Received: {f_val}")
        if f_val >= 0.80:
            return "high", round(f_val, 3)
        elif f_val >= 0.50:
            return "medium", round(f_val, 3)
        else:
            return "low", round(f_val, 3)

    if isinstance(v, str):
        clean = v.strip().lower()
        if clean in {"high", "medium", "low"}:
            return clean, None  # type: ignore[return-value]
        # Attempt to parse as numeric string
        try:
            f_val = float(clean)
            if not (0.0 <= f_val <= 1.0):
                raise ValueError(f"Numeric confidence string must evaluate between 0.0 and 1.0. Received: {v}")
            if f_val >= 0.80:
                return "high", round(f_val, 3)
            elif f_val >= 0.50:
                return "medium", round(f_val, 3)
            else:
                return "low", round(f_val, 3)
        except ValueError as err:
            raise ValueError(
                f"Confidence must be 'high', 'medium', 'low', or a float between 0.0 and 1.0. Received: '{v}'"
            ) from err

    raise ValueError(f"Confidence must be a string or number. Received type: {type(v).__name__}")


class SkillSchema(BaseModel):
    skill_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="The canonical skill or technology name.",
        examples=["Python", "PostgreSQL", "System Design"],
    )
    category_code: CategoryCode = Field(
        ...,
        description="Agreed 12 RADIX category codes, with OTHER as fallback.",
        examples=["COD", "SQL", "SYSD"],
    )
    evidence: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Evidence or justification extracted or provided for the skill.",
        examples=["Built production REST APIs using FastAPI and Pydantic"],
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Extraction certainty indicator strictly adhering to RADIX brief: 'high' | 'medium' | 'low'. Not a proficiency score.",
        examples=["high", "medium"],
    )
    raw_confidence: Optional[float] = Field(
        default=None,
        description="Original numeric certainty score (0.0-1.0) if extracted by an ML/LLM parser.",
        examples=[0.95],
    )
    source: Optional[Literal["extracted", "manual"]] = Field(
        default="manual",
        description="Indicates whether this entry was prefilled from resume parsing or added manually.",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_and_normalize_skill(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data

        # Validate skill_name
        name = data.get("skill_name")
        if isinstance(name, str):
            stripped = name.strip()
            if not stripped:
                raise ValueError("skill_name cannot be empty or whitespace.")
            data["skill_name"] = stripped

        # Normalize confidence to canonical 'high' | 'medium' | 'low'
        raw_conf = data.get("confidence")
        if raw_conf is not None:
            canonical_level, raw_num = normalize_confidence_value(raw_conf)
            data["confidence"] = canonical_level
            if raw_num is not None and data.get("raw_confidence") is None:
                data["raw_confidence"] = raw_num

        return data


class SkillListResponse(BaseModel):
    profile_id: str
    skills: List[SkillSchema]
    total_skills: int
    categories_covered: List[CategoryCode]
