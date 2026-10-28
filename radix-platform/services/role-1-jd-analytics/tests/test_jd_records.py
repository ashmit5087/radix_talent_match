"""Role 1 saved-analysis endpoints: GET /jds, GET /jds/{id}, GET /jds/{id}/skills, PATCH /jds/{id}/skills."""
import uuid

from app.schemas import ExtractedSkillList
from app.services.analysis_store import AnalysisStore
from tests.conftest import ML_JD, make_pdf, upload

MISSING = str(uuid.uuid4())


def _analyze(client):
    return upload(client, "data_scientist.pdf", make_pdf(ML_JD)).json()


def test_get_saved_analysis_matches_analyze_response(client):
    created = _analyze(client)
    r = client.get(f"/api/v1/jds/{created['jd_id']}")
    assert r.status_code == 200 and r.json() == created
    ExtractedSkillList.model_validate(r.json())


def test_get_skills(client):
    created = _analyze(client)
    r = client.get(f"/api/v1/jds/{created['jd_id']}/skills")
    assert r.status_code == 200
    assert r.json() == {"jd_id": created["jd_id"], "skills": created["skills"]}


def test_list(client):
    a = _analyze(client)
    b = _analyze(client)
    body = client.get("/api/v1/jds").json()
    assert body["count"] == 2 and {i["jd_id"] for i in body["items"]} == {a["jd_id"], b["jd_id"]}
    item = body["items"][0]
    assert item["skill_count"] == 3 and item["indexing_status"] == "indexed" and item["chunk_count"] >= 1


def test_patch_replaces_skills_and_persists(client):
    created = _analyze(client)
    new = [{"skill_name": "System Design", "category_code": "SYSD", "evidence": "added by reviewer",
            "confidence": "medium"}]
    r = client.patch(f"/api/v1/jds/{created['jd_id']}/skills", json={"skills": new})
    assert r.status_code == 200 and r.json()["skills"] == new
    assert client.get(f"/api/v1/jds/{created['jd_id']}").json()["skills"] == new
    assert client.get("/api/v1/jds").json()["items"][0]["skill_count"] == 1


def test_patch_validation(client):
    jd_id = _analyze(client)["jd_id"]
    bad_cat = {"skills": [{"skill_name": "x", "category_code": "NOPE", "evidence": "e", "confidence": "high"}]}
    dup = {"skills": [{"skill_name": "Go", "category_code": "COD", "evidence": "e", "confidence": "high"},
                      {"skill_name": "go", "category_code": "COD", "evidence": "e", "confidence": "low"}]}
    for body in (bad_cat, dup, {}):
        r = client.patch(f"/api/v1/jds/{jd_id}/skills", json=body)
        assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert len(client.get(f"/api/v1/jds/{jd_id}/skills").json()["skills"]) == 3  # unchanged


def test_unknown_and_malformed_ids(client):
    for path in (f"/api/v1/jds/{MISSING}", f"/api/v1/jds/{MISSING}/skills"):
        r = client.get(path)
        assert r.status_code == 404 and r.json()["error"]["code"] == "JD_NOT_FOUND"
    assert client.patch(f"/api/v1/jds/{MISSING}/skills", json={"skills": []}).status_code == 404
    assert client.get("/api/v1/jds/not-a-uuid").status_code == 422


def test_saved_analyses_survive_restart(settings, client):
    created = _analyze(client)
    reopened = AnalysisStore(settings.jd_db_path)
    assert reopened.get(created["jd_id"])["company"] == "Acme Analytics"


def test_saved_record_holds_no_jd_text_or_paths(settings, client, tmp_path):
    _analyze(client)
    raw = settings.jd_db_path.read_bytes()
    assert b"Key Responsibilities" not in raw and str(tmp_path).encode() not in raw
