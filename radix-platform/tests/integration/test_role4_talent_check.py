"""
TC-07, TC-08, TC-09: Role 4 — Talent Check & Company Search
"""
import pytest
import httpx
from conftest import ROLE4

CANDIDATE_PROFILE = {
    "name": "Integration Test Candidate",
    "headline": "Software Engineer",
    "skills": [
        {"skill_name": "Python", "category": "SE", "confidence": "high", "evidence": "3 years"},
        {"skill_name": "SQL", "category": "DE", "confidence": "medium", "evidence": "2 years"},
        {"skill_name": "Docker", "category": "DevOps", "confidence": "medium", "evidence": "1 year"},
    ],
}


def _first_company_id() -> int:
    """Helper: fetch first company ID from the list."""
    r = httpx.get(f"{ROLE4}/api/companies", params={"limit": 1}, timeout=8)
    assert r.status_code == 200, f"Companies list failed: {r.status_code}"
    companies = r.json()
    assert len(companies) >= 1, "No companies in database"
    return companies[0]["id"]


def test_company_search_returns_results():
    """TC-07: Company list endpoint returns at least 1 result."""
    r = httpx.get(f"{ROLE4}/api/companies", params={"limit": 10}, timeout=8)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list), f"Expected list, got: {type(data)}"
    assert len(data) >= 1, "Company list is empty — is companies.json loaded?"


def test_company_search_with_query():
    """TC-07: Filtered search returns matching companies."""
    # Grab first company name and search a prefix
    r = httpx.get(f"{ROLE4}/api/companies", params={"limit": 1}, timeout=8)
    assert r.status_code == 200
    first = r.json()[0]
    name_prefix = first["company"][:4].lower()

    r2 = httpx.get(f"{ROLE4}/api/companies", params={"q": name_prefix, "limit": 5}, timeout=8)
    assert r2.status_code == 200
    results = r2.json()
    assert all(name_prefix in c["company"].lower() for c in results), \
        f"Filter returned non-matching company: {results}"


def test_company_search_fields():
    """TC-07: Each company must have id (int) and company (str)."""
    r = httpx.get(f"{ROLE4}/api/companies", params={"limit": 5}, timeout=8)
    assert r.status_code == 200
    for c in r.json():
        assert isinstance(c["id"], int), f"id is not int: {c}"
        assert isinstance(c["company"], str) and c["company"], f"company is empty: {c}"


def test_talent_check_score_range():
    """TC-08: Readiness score must be 0–100."""
    company_id = _first_company_id()
    payload = {"company_id": company_id, "candidate_profile": CANDIDATE_PROFILE}
    r = httpx.post(f"{ROLE4}/api/talent-check", json=payload, timeout=15)
    assert r.status_code == 200, f"Talent check failed: {r.status_code} {r.text[:300]}"
    body = r.json()
    score = body.get("readiness_score")
    assert score is not None, f"Missing readiness_score: {body}"
    assert 0 <= score <= 100, f"Score out of range: {score}"


def test_talent_check_response_structure():
    """TC-08: Response must include verdict, critical_gaps, focus_areas."""
    company_id = _first_company_id()
    payload = {"company_id": company_id, "candidate_profile": CANDIDATE_PROFILE}
    r = httpx.post(f"{ROLE4}/api/talent-check", json=payload, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert "verdict" in body and body["verdict"], f"Missing verdict: {body}"
    assert "critical_gaps" in body and isinstance(body["critical_gaps"], list)
    assert "focus_areas" in body and isinstance(body["focus_areas"], list)


def test_talent_check_direct():
    """TC-09: Direct skill-level endpoint returns valid score."""
    company_id = _first_company_id()
    payload = {
        "company_id": company_id,
        "skill_levels": {"SE": 7, "DS": 5, "ML": 3, "Cloud": 6, "DevOps": 4},
    }
    r = httpx.post(f"{ROLE4}/api/talent-check/direct", json=payload, timeout=15)
    assert r.status_code == 200, f"Direct check failed: {r.status_code} {r.text[:300]}"
    body = r.json()
    score = body.get("readiness_score")
    assert score is not None and 0 <= score <= 100, f"Bad score: {score}"


def test_talent_check_invalid_company():
    """TC-08 edge: unknown company_id must return 404."""
    payload = {"company_id": 999999999, "candidate_profile": CANDIDATE_PROFILE}
    r = httpx.post(f"{ROLE4}/api/talent-check", json=payload, timeout=15)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"


def test_categories_endpoint():
    """Role 4 categories must return 12 RADIX competencies."""
    r = httpx.get(f"{ROLE4}/api/categories", timeout=8)
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) >= 12, f"Expected ≥12 categories, got {len(cats)}: {cats}"

