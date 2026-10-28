import json

from fastapi.testclient import TestClient

from conftest import cand, jd, sk
from skill_matching.api import app

client = TestClient(app, raise_server_exceptions=False)


def test_health_and_root():
    assert client.get("/health").json()["status"] == "ok"
    assert "POST /api/v1/matches" in client.get("/").json()["endpoints"]["match"]


def test_match_ok(load):
    r = client.post("/api/v1/matches", json=load("sample_match_request.json"))
    assert r.status_code == 200
    body = r.json()
    for k in ("jd_source_file", "match_score", "matched_skills", "missing_skills"):
        assert k in body
    assert 0 <= body["match_score"] <= 100


def test_empty_jd_422():
    r = client.post("/api/v1/matches", json={"candidate": cand(sk("Python")), "job_description": jd()})
    assert r.status_code == 422 and r.json()["error"] == "no_job_skills"


def test_invalid_json_400():
    r = client.post("/api/v1/matches", content=b"{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400


def test_missing_section_400():
    r = client.post("/api/v1/matches", json={"candidate": cand(sk("Python"))})
    assert r.status_code == 400 and "job_description" in r.json()["detail"]


def test_bad_skill_400():
    r = client.post("/api/v1/matches", json={"candidate": cand(sk("Python")), "job_description": jd({"nope": 1})})
    assert r.status_code == 400


def test_preview(load):
    r = client.post("/api/v1/matches/preview", json=load("sample_match_request.json"))
    assert r.status_code == 200 and "results" in r.json() and "match_score" not in r.json()


def test_500_is_generic(monkeypatch):
    import skill_matching.api as api

    def boom(*a, **k):
        raise RuntimeError("secret-stack-detail")

    monkeypatch.setattr(api, "match_raw", boom)
    r = client.post("/api/v1/matches", json={"candidate": cand(sk("Python")), "job_description": jd(sk("Python"))})
    assert r.status_code == 500 and "secret" not in r.text
