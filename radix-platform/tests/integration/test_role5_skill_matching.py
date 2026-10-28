"""
TC-10, TC-11: Role 5 — Skill Matching & Improvement Plan
Uses only Role 5 (no other services needed for these tests).
"""
import pytest
import httpx
from conftest import ROLE5

CANDIDATE_SKILLS = [
    {"skill_name": "Python", "category_code": "SE", "evidence": "3 years production use", "confidence": "high"},
    {"skill_name": "FastAPI", "category_code": "SE", "evidence": "Built REST APIs", "confidence": "high"},
    {"skill_name": "PostgreSQL", "category_code": "DE", "evidence": "Schema design", "confidence": "medium"},
]

JD_SKILLS = [
    {"skill_name": "Python", "category_code": "SE", "evidence": "Required", "confidence": "high"},
    {"skill_name": "Docker", "category_code": "DevOps", "evidence": "Required", "confidence": "high"},
    {"skill_name": "Kubernetes", "category_code": "DevOps", "evidence": "Nice to have", "confidence": "medium"},
]

MATCH_PAYLOAD = {
    "candidate": {"skills": CANDIDATE_SKILLS},
    "job_description": {
        "jd_id": "test-integration-jd",
        "source_type": "manual",
        "source_file": "test.json",
        "company": "Acme Corp",
        "role": "Backend Engineer",
        "skills": JD_SKILLS,
    },
    "talent_check": None,
}


def test_skill_match_score_range():
    """TC-10: overall_score must be 0–100."""
    r = httpx.post(f"{ROLE5}/api/v1/matches", json=MATCH_PAYLOAD, timeout=15)
    assert r.status_code == 200, f"Match failed: {r.status_code} {r.text[:300]}"
    body = r.json()
    assert "overall_score" in body, f"Missing overall_score: {body}"
    score = body["overall_score"]
    assert 0 <= score <= 100, f"Score out of range: {score}"


def test_skill_match_identifies_gap():
    """TC-10: Docker is a JD requirement absent from candidate — must appear in gap_skills."""
    r = httpx.post(f"{ROLE5}/api/v1/matches", json=MATCH_PAYLOAD, timeout=15)
    assert r.status_code == 200
    body = r.json()
    gap_names = [g["skill_name"].lower() for g in body.get("gap_skills", [])]
    assert any("docker" in n for n in gap_names), f"Docker not found in gap_skills: {gap_names}"


def test_skill_match_identifies_matched():
    """TC-10: Python is in both candidate and JD — must appear in matched_skills."""
    r = httpx.post(f"{ROLE5}/api/v1/matches", json=MATCH_PAYLOAD, timeout=15)
    assert r.status_code == 200
    body = r.json()
    matched_names = [m["skill_name"].lower() for m in body.get("matched_skills", [])]
    assert any("python" in n for n in matched_names), f"Python not in matched_skills: {matched_names}"


def test_skill_match_deterministic():
    """TC-10: Same inputs must always return the same score."""
    r1 = httpx.post(f"{ROLE5}/api/v1/matches", json=MATCH_PAYLOAD, timeout=15)
    r2 = httpx.post(f"{ROLE5}/api/v1/matches", json=MATCH_PAYLOAD, timeout=15)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["overall_score"] == r2.json()["overall_score"], "Score is non-deterministic!"


def test_improvement_plan_has_steps():
    """TC-11: Improvement plan must have ≥1 step for identified gaps."""
    r = httpx.post(f"{ROLE5}/api/v1/improvement-plan", json=MATCH_PAYLOAD, timeout=15)
    assert r.status_code == 200, f"Plan failed: {r.status_code} {r.text[:300]}"
    body = r.json()
    assert "steps" in body, f"Missing steps: {body}"
    assert len(body["steps"]) >= 1, "Expected at least one improvement step"


def test_improvement_plan_step_structure():
    """TC-11: Each step must have required fields."""
    r = httpx.post(f"{ROLE5}/api/v1/improvement-plan", json=MATCH_PAYLOAD, timeout=15)
    assert r.status_code == 200
    steps = r.json().get("steps", [])
    for step in steps:
        assert "skill_name" in step, f"Step missing skill_name: {step}"
        assert "priority" in step, f"Step missing priority: {step}"
        assert "action" in step, f"Step missing action: {step}"
        assert step["priority"] in ("critical", "important", "nice-to-have"), \
            f"Invalid priority: {step['priority']}"

