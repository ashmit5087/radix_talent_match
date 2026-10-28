"""
TC-12, TC-13: Cross-role end-to-end integration flows.
Requires all 5 services running.
These tests compose multiple roles: Role 3 + Role 4 + Role 5.
(Role 1 and Role 2 file-upload flows are covered separately with real files.)
"""
import pytest
import httpx
from conftest import ROLE3, ROLE4, ROLE5

# Shared candidate skills (would normally come from Role 2 resume parse)
CANDIDATE_SKILLS_PAYLOAD = [
    {"skill_name": "Python", "category_code": "SE", "evidence": "3 years", "confidence": "high"},
    {"skill_name": "SQL", "category_code": "DE", "evidence": "2 years", "confidence": "medium"},
    {"skill_name": "FastAPI", "category_code": "SE", "evidence": "REST APIs", "confidence": "high"},
]

JD_PAYLOAD = {
    "jd_id": "cross-test-jd-001",
    "source_type": "manual",
    "source_file": "senior_engineer.json",
    "company": "Acme Corp",
    "role": "Senior Backend Engineer",
    "skills": [
        {"skill_name": "Python", "category_code": "SE", "evidence": "Required", "confidence": "high"},
        {"skill_name": "Docker", "category_code": "DevOps", "evidence": "Required", "confidence": "high"},
        {"skill_name": "Redis", "category_code": "DE", "evidence": "Nice to have", "confidence": "low"},
    ],
}


@pytest.fixture(scope="module")
def profile_id() -> str:
    """TC-12 step 1: Create a live profile via Role 3."""
    payload = {
        "personal_info": {
            "full_name": "Cross-Role Test Candidate",
            "email": "crossrole@radix-test.ai",
        },
        "skills": [
            {**s, "source": "manual"} for s in CANDIDATE_SKILLS_PAYLOAD
        ],
    }
    r = httpx.post(f"{ROLE3}/api/v1/profiles", json=payload, timeout=15)
    assert r.status_code in (200, 201), f"Profile create: {r.status_code} {r.text[:200]}"
    return r.json()["profile_id"]


@pytest.fixture(scope="module")
def company_id() -> int:
    """TC-13: Get first available company from Role 4."""
    r = httpx.get(f"{ROLE4}/api/companies", params={"limit": 1}, timeout=8)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1, "No companies available in Role 4"
    return data[0]["id"]


def test_flow_profile_then_match(profile_id: str):
    """TC-12: Profile from Role 3 feeds into Role 5 skill match."""
    # Fetch the profile back from Role 3
    rp = httpx.get(f"{ROLE3}/api/v1/profiles/{profile_id}", timeout=10)
    assert rp.status_code == 200
    profile_body = rp.json()

    # Build match request from the live profile
    profile_skills = profile_body.get("skills", [])
    candidate_skills = [
        {
            "skill_name": s.get("skill_name", ""),
            "category_code": s.get("category_code", ""),
            "evidence": s.get("evidence", ""),
            "confidence": s.get("confidence", "medium"),
        }
        for s in profile_skills
    ]

    match_req = {
        "candidate": {"skills": candidate_skills},
        "job_description": JD_PAYLOAD,
        "talent_check": None,
    }
    rm = httpx.post(f"{ROLE5}/api/v1/matches", json=match_req, timeout=15)
    assert rm.status_code == 200, f"Match failed: {rm.status_code} {rm.text[:300]}"
    score = rm.json().get("overall_score")
    assert score is not None and 0 <= score <= 100, f"Bad score: {score}"


def test_flow_talent_check_weighted_match(profile_id: str, company_id: int):
    """TC-13: Role 3 profile → Role 4 talent check → Role 5 weighted match."""
    # Step 1: Fetch profile
    rp = httpx.get(f"{ROLE3}/api/v1/profiles/{profile_id}", timeout=10)
    assert rp.status_code == 200
    profile_body = rp.json()
    personal = profile_body.get("personal_info", {})
    profile_skills = profile_body.get("skills", [])

    # Step 2: Talent check (Role 4)
    talent_payload = {
        "company_id": company_id,
        "candidate_profile": {
            "name": personal.get("full_name", "Test"),
            "skills": [
                {
                    "skill_name": s.get("skill_name"),
                    "category": s.get("category_code"),
                    "confidence": s.get("confidence", "medium"),
                    "evidence": s.get("evidence", ""),
                }
                for s in profile_skills
            ],
        },
    }
    rt = httpx.post(f"{ROLE4}/api/talent-check", json=talent_payload, timeout=15)
    assert rt.status_code == 200, f"Talent check: {rt.status_code} {rt.text[:200]}"
    talent_result = rt.json()

    # Step 3: Weighted match (Role 5)
    candidate_skills = [
        {
            "skill_name": s.get("skill_name", ""),
            "category_code": s.get("category_code", ""),
            "evidence": s.get("evidence", ""),
            "confidence": s.get("confidence", "medium"),
        }
        for s in profile_skills
    ]
    match_req = {
        "candidate": {"skills": candidate_skills},
        "job_description": JD_PAYLOAD,
        "talent_check": talent_result,
    }
    rm = httpx.post(f"{ROLE5}/api/v1/matches", json=match_req, timeout=15)
    assert rm.status_code == 200, f"Weighted match: {rm.status_code} {rm.text[:200]}"
    score_weighted = rm.json().get("overall_score")
    assert score_weighted is not None and 0 <= score_weighted <= 100

    # Cross-check: unweighted match
    match_req_no_tc = {**match_req, "talent_check": None}
    rm2 = httpx.post(f"{ROLE5}/api/v1/matches", json=match_req_no_tc, timeout=15)
    assert rm2.status_code == 200
    score_plain = rm2.json().get("overall_score")

    # Scores may differ when talent_check is included (this is a behavioral assertion)
    # We just confirm both are valid — not necessarily equal
    assert 0 <= score_plain <= 100, f"Plain score OOB: {score_plain}"
    print(f"\n  Plain score: {score_plain}  |  Talent-weighted score: {score_weighted}")

