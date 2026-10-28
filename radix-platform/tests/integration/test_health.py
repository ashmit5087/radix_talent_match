"""
TC-14 & TC-15: Health checks for all 5 services.
Must be first-pass: if any service is down, later tests are expected to fail.
"""
import pytest
import httpx
from conftest import ROLE1, ROLE2, ROLE3, ROLE4, ROLE5


HEALTH_ENDPOINTS = [
    ("Role 1 — JD Analytics",   ROLE1, "/health"),
    ("Role 2 — Resume Parsing", ROLE2, "/health"),
    ("Role 3 — Profile Builder",ROLE3, "/health"),
    ("Role 4 — Talent Check",   ROLE4, "/api/health"),
    ("Role 5 — Skill Matching", ROLE5, "/health"),
]


@pytest.mark.parametrize("name,base,path", HEALTH_ENDPOINTS, ids=[e[0] for e in HEALTH_ENDPOINTS])
def test_health(name: str, base: str, path: str):
    """TC-14: Every service must respond 200 at its health endpoint."""
    r = httpx.get(base + path, timeout=8)
    assert r.status_code == 200, f"{name} returned {r.status_code}: {r.text[:200]}"
    body = r.json()
    # Accept any truthy status value: "healthy", "ok", True, etc.
    status = body.get("status", "")
    assert status, f"{name} health body has no 'status' field: {body}"


@pytest.mark.parametrize("name,base,path", HEALTH_ENDPOINTS, ids=[e[0] for e in HEALTH_ENDPOINTS])
def test_cors_headers(name: str, base: str, path: str):
    """TC-15: CORS headers must be present on all services."""
    r = httpx.options(
        base + path,
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        timeout=8,
    )
    # OPTIONS may return 200 or 204
    assert r.status_code in (200, 204), f"{name} CORS preflight returned {r.status_code}"
    acao = r.headers.get("access-control-allow-origin", "")
    assert acao, f"{name} missing Access-Control-Allow-Origin header"

