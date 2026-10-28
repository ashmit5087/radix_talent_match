import pytest
from pydantic import ValidationError
from app.schemas.skill import (
    CategoryCode,
    SkillSchema,
    normalize_confidence_value,
)
from app.schemas.profile import PersonalInfo, EducationEntry


def test_valid_category_codes():
    """All 12 RADIX category codes plus OTHER must be valid."""
    expected_codes = [
        "COD", "DSA", "OOD", "APTI", "COMM", "AI",
        "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER"
    ]
    for code in expected_codes:
        skill = SkillSchema(
            skill_name="Test Skill",
            category_code=code,
            evidence="Worked on production project",
            confidence="high",
        )
        assert skill.category_code == code


def test_invalid_category_code_fails():
    """Any category code outside the 12+OTHER schema must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        SkillSchema(
            skill_name="Invalid Skill",
            category_code="INVALID_CODE",
            evidence="Some evidence",
            confidence="high",
        )
    assert "category_code" in str(exc_info.value)


def test_confidence_normalization_and_provenance():
    """
    Public contract requires 'high' | 'medium' | 'low'.
    Internal/adapter numeric scores normalize:
      >= 0.80 -> 'high'
      >= 0.50 -> 'medium'
      <  0.50 -> 'low'
    Raw numeric certainty is preserved in raw_confidence.
    """
    # 1. Direct canonical strings
    s1 = SkillSchema(skill_name="Python", category_code="COD", evidence="code", confidence="high")
    assert s1.confidence == "high"
    assert s1.raw_confidence is None

    s2 = SkillSchema(skill_name="Python", category_code="COD", evidence="code", confidence="MEDIUM")
    assert s2.confidence == "medium"

    s3 = SkillSchema(skill_name="Python", category_code="COD", evidence="code", confidence="low")
    assert s3.confidence == "low"

    # 2. Numeric inputs automatically normalized
    s4 = SkillSchema(skill_name="Python", category_code="COD", evidence="code", confidence=0.95)
    assert s4.confidence == "high"
    assert s4.raw_confidence == 0.95

    s5 = SkillSchema(skill_name="Python", category_code="COD", evidence="code", confidence=0.72)
    assert s5.confidence == "medium"
    assert s5.raw_confidence == 0.72

    s6 = SkillSchema(skill_name="Python", category_code="COD", evidence="code", confidence=0.35)
    assert s6.confidence == "low"
    assert s6.raw_confidence == 0.35

    # 3. Numeric string inputs normalized
    s7 = SkillSchema(skill_name="Python", category_code="COD", evidence="code", confidence="0.88")
    assert s7.confidence == "high"
    assert s7.raw_confidence == 0.88

    # 4. Out of bounds or invalid inputs rejected
    with pytest.raises(ValidationError):
        SkillSchema(skill_name="Python", category_code="COD", evidence="code", confidence=-0.1)

    with pytest.raises(ValidationError):
        SkillSchema(skill_name="Python", category_code="COD", evidence="code", confidence=1.5)

    with pytest.raises(ValidationError):
        SkillSchema(skill_name="Python", category_code="COD", evidence="code", confidence="expert")


def test_personal_info_validation():
    """Email and full_name must be strictly validated."""
    p = PersonalInfo(full_name="Priya Menon", email="priya@example.com")
    assert p.full_name == "Priya Menon"

    with pytest.raises(ValidationError):
        PersonalInfo(full_name="Priya Menon", email="not-an-email")

    with pytest.raises(ValidationError):
        PersonalInfo(full_name="   ", email="priya@example.com")


def test_education_validation():
    """Education entries must require institution and degree."""
    edu = EducationEntry(institution="IIT Delhi", degree="B.Tech")
    assert edu.institution == "IIT Delhi"
    assert edu.degree == "B.Tech"

    with pytest.raises(ValidationError):
        EducationEntry(institution="", degree="B.Tech")
