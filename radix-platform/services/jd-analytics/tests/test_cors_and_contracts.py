import json

from app.config import Settings
from app.main import create_app
from app.utils.contracts import CONTRACTS_DIR, build_contracts, render
from fastapi.testclient import TestClient

ALLOWED = "http://localhost:5173"


def test_preflight_allowed_origin():
    c = TestClient(create_app())
    r = c.options("/api/v1/jds/analyze", headers={
        "Origin": ALLOWED, "Access-Control-Request-Method": "POST"})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == ALLOWED


def test_other_origin_is_not_allowed():
    c = TestClient(create_app())
    r = c.options("/api/v1/jds/analyze", headers={
        "Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers


def test_indexing_headers_are_exposed_to_browser_code():
    c = TestClient(create_app())
    r = c.get("/health", headers={"Origin": ALLOWED})
    assert "X-Indexing-Status" in r.headers["access-control-expose-headers"]


def test_cors_origins_setting_parsing():
    s = Settings(_env_file=None, cors_origins=" http://a.com/ , http://b.com ")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]


def test_committed_contract_files_match_models():
    for name, schema in build_contracts().items():
        path = CONTRACTS_DIR / name
        assert path.exists(), f"{name} missing: run  python -m app.utils.contracts"
        assert path.read_text(encoding="utf-8") == render(schema), f"{name} is out of date: re-run the export"


def test_contract_contents():
    skill = json.loads((CONTRACTS_DIR / "skill.schema.json").read_text())
    assert set(skill["required"]) == {"skill_name", "category_code", "evidence", "confidence"}
    assert len(skill["properties"]["category_code"]["enum"]) == 13
    jd = json.loads((CONTRACTS_DIR / "jd-analysis.schema.json").read_text())
    assert {"source_type", "source_file", "jd_id"} <= set(jd["required"])
    assert "skills" in jd["properties"]  # optional in the shared schema (defaults to an empty list)
