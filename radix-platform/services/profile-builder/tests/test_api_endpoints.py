import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.repositories.profile_repository import DatabasePersistenceError


def test_root_and_health_endpoints(client: TestClient):
    # Root check
    r1 = client.get("/")
    assert r1.status_code == 200
    assert "Profile Builder" in r1.json()["service"]

    # Health check
    r2 = client.get("/health")
    assert r2.status_code == 200
    assert r2.json()["status"] == "healthy"
    assert "persistence_mode" in r2.json()


def test_create_and_get_profile(client: TestClient, sample_profile_payload):
    # 1. Create profile
    resp = client.post("/api/v1/profiles", json=sample_profile_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "profile_id" in data
    profile_id = data["profile_id"]
    assert data["personal_info"]["full_name"] == "Karthik Subramaniam"
    assert len(data["skills"]) == 3
    # Check normalized confidence
    for s in data["skills"]:
        assert s["confidence"] in ["high", "medium", "low"]

    # 2. Get profile
    get_resp = client.get(f"/api/v1/profiles/{profile_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["profile_id"] == profile_id
    assert get_data["personal_info"]["email"] == "karthik.sub@example.com"


def test_get_nonexistent_profile_returns_404(client: TestClient):
    resp = client.get("/api/v1/profiles/non-existent-id-12345")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_update_profile_preserves_profile_id(client: TestClient, sample_profile_payload):
    # Create first
    create_resp = client.post("/api/v1/profiles", json=sample_profile_payload)
    profile_id = create_resp.json()["profile_id"]

    # Update
    update_payload = {
        "personal_info": {
            "full_name": "Karthik S. Updated",
            "email": "karthik.new@example.com",
            "summary": "Updated summary text",
        },
        "preferred_roles": ["Lead Data Architect"],
    }
    put_resp = client.put(f"/api/v1/profiles/{profile_id}", json=update_payload)
    assert put_resp.status_code == 200
    put_data = put_resp.json()

    # profile_id MUST NOT change
    assert put_data["profile_id"] == profile_id
    assert put_data["personal_info"]["full_name"] == "Karthik S. Updated"
    assert put_data["preferred_roles"] == ["Lead Data Architect"]
    # Existing education & skills are preserved
    assert len(put_data["education"]) == 1
    assert len(put_data["skills"]) == 3


def test_update_nonexistent_profile_returns_404(client: TestClient):
    resp = client.put(
        "/api/v1/profiles/fake-id-9999",
        json={"preferred_roles": ["Architect"]},
    )
    assert resp.status_code == 404


def test_create_profile_from_resume_mock_001(client: TestClient):
    resp = client.post("/api/v1/profiles/from-resume/mock-001")
    assert resp.status_code == 201
    data = resp.json()

    assert data["profile_id"] is not None
    assert data["personal_info"]["full_name"] == "Rohan Verma"
    assert data["personal_info"]["email"] == "rohan.verma@example.com"
    assert data["personal_info"]["source"] == "extracted"

    # Verify skills carry source='extracted', valid categories, and 'high'|'medium'|'low' confidence
    assert len(data["skills"]) >= 6
    for skill in data["skills"]:
        assert skill["source"] == "extracted"
        assert skill["category_code"] in [
            "COD", "DSA", "OOD", "APTI", "COMM", "AI",
            "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER"
        ]
        assert skill["evidence"]
        assert skill["confidence"] in ["high", "medium", "low"]


def test_create_profile_from_invalid_resume_returns_404(client: TestClient):
    resp = client.post("/api/v1/profiles/from-resume/missing-resume-999")
    assert resp.status_code == 404


def test_get_profile_skills_for_roles_4_and_5(client: TestClient, sample_profile_payload):
    create_resp = client.post("/api/v1/profiles", json=sample_profile_payload)
    profile_id = create_resp.json()["profile_id"]

    skills_resp = client.get(f"/api/v1/profiles/{profile_id}/skills")
    assert skills_resp.status_code == 200
    data = skills_resp.json()

    assert data["profile_id"] == profile_id
    assert data["total_skills"] == 3
    assert len(data["skills"]) == 3
    # Check that required fields for Role 4 & Role 5 are present
    for s in data["skills"]:
        assert "skill_name" in s
        assert "category_code" in s
        assert "evidence" in s
        assert s["confidence"] in ["high", "medium", "low"]


def test_get_profile_completeness_endpoint(client: TestClient, sample_profile_payload):
    create_resp = client.post("/api/v1/profiles", json=sample_profile_payload)
    profile_id = create_resp.json()["profile_id"]

    comp_resp = client.get(f"/api/v1/profiles/{profile_id}/completeness")
    assert comp_resp.status_code == 200
    data = comp_resp.json()

    assert data["profile_id"] == profile_id
    assert 0 <= data["overall_percentage"] <= 100
    assert "section_scores" in data
    assert "completed_sections" in data
    assert "incomplete_sections" in data
    assert "missing_recommendations" in data


def test_upload_and_download_cv_endpoint(client: TestClient, sample_profile_payload):
    # 1. Create a profile
    create_resp = client.post("/api/v1/profiles", json=sample_profile_payload)
    profile_id = create_resp.json()["profile_id"]

    # 2. Upload PDF CV
    pdf_content = b"%PDF-1.4 Mock CV document bytes for testing"
    files = {"file": ("my_resume.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(f"/api/v1/profiles/{profile_id}/cv", files=files)
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["profile_id"] == profile_id
    assert upload_data["cv_file"] == "my_resume.pdf"
    assert upload_data["size_bytes"] == len(pdf_content)

    # 3. Download the uploaded CV
    download_resp = client.get(f"/api/v1/profiles/{profile_id}/cv")
    assert download_resp.status_code == 200
    assert download_resp.content == pdf_content


def test_upload_cv_invalid_extension_returns_400(client: TestClient, sample_profile_payload):
    create_resp = client.post("/api/v1/profiles", json=sample_profile_payload)
    profile_id = create_resp.json()["profile_id"]

    bad_files = {"file": ("malicious.exe", io.BytesIO(b"bad content"), "application/octet-stream")}
    resp = client.post(f"/api/v1/profiles/{profile_id}/cv", files=bad_files)
    assert resp.status_code == 400
    assert "Unsupported CV file extension" in resp.json()["detail"]


def test_upload_cv_nonexistent_profile_returns_404(client: TestClient):
    files = {"file": ("resume.pdf", io.BytesIO(b"%PDF mock"), "application/pdf")}
    resp = client.post("/api/v1/profiles/non-existent-id/cv", files=files)
    assert resp.status_code == 404


def test_database_error_prevents_false_success(client: TestClient, sample_profile_payload):
    """
    CRITICAL QUALITY GATE:
    When the database repository raises DatabasePersistenceError, the endpoint
    must return 503 Service Unavailable and NEVER return a false 200/201 success.
    """
    from main import app
    from app.services.profile_service import ProfileService, get_profile_service

    mock_svc = ProfileService()

    async def _failing_create(*args, **kwargs):
        raise DatabasePersistenceError("Simulated Supabase connection timeout")

    mock_svc.create_profile = _failing_create

    app.dependency_overrides[get_profile_service] = lambda: mock_svc
    try:
        resp = client.post("/api/v1/profiles", json=sample_profile_payload)
        # Must fail with 503, never 201 false success
        assert resp.status_code == 503
        assert "Database persistence error" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_profile_service, None)


def test_invalid_payload_returns_422(client: TestClient):
    bad_payload = {
        "personal_info": {
            "full_name": "Test User",
            "email": "not-valid-email",
        }
    }
    resp = client.post("/api/v1/profiles", json=bad_payload)
    assert resp.status_code == 422
