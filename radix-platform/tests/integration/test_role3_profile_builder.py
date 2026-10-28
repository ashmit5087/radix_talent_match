"""
TC-05, TC-06: Role 3 — Profile Builder
Creates profiles and checks completeness. No file upload needed.
"""
import pytest
import httpx
from conftest import ROLE3

SAMPLE_PROFILE = {
    "personal_info": {
        "full_name": "Integration Test User",
        "email": "integration@radix-test.ai",
        "location": "Bangalore, India",
        "summary": "Test candidate for RADIX integration tests",
    },
    "skills": [
        {
            "skill_name": "Python",
            "category_code": "SE",
            "evidence": "3 years of production use",
            "confidence": "high",
            "source": "manual",
        },
        {
            "skill_name": "FastAPI",
            "category_code": "SE",
            "evidence": "Built microservices",
            "confidence": "high",
            "source": "manual",
        },
        {
            "skill_name": "PostgreSQL",
            "category_code": "DE",
            "evidence": "Schema design experience",
            "confidence": "medium",
            "source": "manual",
        },
    ],
}


@pytest.fixture(scope="module")
def created_profile_id() -> str:
    """Create a profile once for all tests in this module."""
    r = httpx.post(f"{ROLE3}/api/v1/profiles", json=SAMPLE_PROFILE, timeout=15)
    assert r.status_code in (200, 201), f"Profile create failed: {r.status_code} {r.text[:300]}"
    body = r.json()
    assert "profile_id" in body, f"Missing profile_id in: {body}"
    return body["profile_id"]


def test_profile_create_returns_id(created_profile_id: str):
    """TC-05: Profile creation returns a non-empty profile_id."""
    assert created_profile_id and isinstance(created_profile_id, str)


def test_profile_retrieve(created_profile_id: str):
    """TC-05: Profile can be retrieved by ID after creation."""
    r = httpx.get(f"{ROLE3}/api/v1/profiles/{created_profile_id}", timeout=10)
    assert r.status_code == 200, f"Get profile failed: {r.status_code} {r.text[:300]}"
    body = r.json()
    assert body.get("profile_id") == created_profile_id or body.get("id") == created_profile_id, \
        f"ID mismatch: {body}"


def test_profile_skills_persisted(created_profile_id: str):
    """TC-05: Created profile must contain the submitted skills."""
    r = httpx.get(f"{ROLE3}/api/v1/profiles/{created_profile_id}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    skills = body.get("skills", [])
    skill_names = [s.get("skill_name", "").lower() for s in skills]
    assert "python" in skill_names, f"Python not in persisted skills: {skill_names}"


def test_profile_completeness(created_profile_id: str):
    """TC-06: Completeness endpoint returns a score in 0–100."""
    r = httpx.get(f"{ROLE3}/api/v1/profiles/{created_profile_id}/completeness", timeout=10)
    assert r.status_code == 200, f"Completeness failed: {r.status_code} {r.text[:300]}"
    body = r.json()
    score = body.get("score")
    assert score is not None, f"Missing score: {body}"
    assert 0 <= score <= 100, f"Score out of range: {score}"


def test_profile_not_found():
    """TC-05 edge: Non-existent profile ID must return 404."""
    r = httpx.get(f"{ROLE3}/api/v1/profiles/nonexistent-profile-id-xyz", timeout=10)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"

