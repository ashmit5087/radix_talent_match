"""SupabaseAnalysisStore against an in-memory fake of Supabase's REST API (PostgREST).

This checks our request shapes and mapping logic. It does NOT prove the SQL migration runs on a real
Supabase project; run supabase/migrations/001_role1_jd_tables.sql there and try the flow once.
"""
import json
import uuid
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import routes
from app.config import Settings
from app.services.supabase_store import SupabaseAnalysisStore
from tests.conftest import ML_JD, make_pdf, upload

KEY = "service-role-secret-xyz"


class FakeSupabase:
    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.requests: list[httpx.Request] = []
        self.fail = False

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.requests.append(req)
        if self.fail:
            return httpx.Response(500, json={"message": "boom"})
        assert req.headers["apikey"] == KEY and req.headers["authorization"] == f"Bearer {KEY}"
        path = req.url.path.replace("/rest/v1", "")
        q = dict(req.url.params)
        body = json.loads(req.content) if req.content else None
        if path == "/rpc/save_jd_analysis":
            if body["p_id"] in self.rows:
                return httpx.Response(409, json={})
            now = self._now()
            self.rows[body["p_id"]] = {
                "id": body["p_id"], "source_file": body["p_source_file"], "company": body["p_company"],
                "role": body["p_role"], "indexing_status": body["p_status"], "chunk_count": body["p_chunks"],
                "created_at": now, "updated_at": now,
                "jd_skills": [{**s, "position": i} for i, s in enumerate(body["p_skills"])],
            }
            return httpx.Response(204)
        if path == "/rpc/replace_jd_skills":
            row = self.rows.get(body["p_jd_id"])
            if row:
                row["jd_skills"] = [{**s, "position": i} for i, s in enumerate(body["p_skills"])]
                row["updated_at"] = self._now()
            return httpx.Response(200, json=bool(row))
        if path == "/jd_analyses":
            wanted = q.get("id", "")[3:] if q.get("id", "").startswith("eq.") else None
            if req.method == "GET":
                rows = [r for r in self.rows.values() if wanted is None or r["id"] == wanted]
                return httpx.Response(200, json=list(reversed(rows)))
            if req.method == "DELETE":
                gone = self.rows.pop(wanted, None)
                return httpx.Response(200, json=[gone] if gone else [])
        return httpx.Response(404, json={})


@pytest.fixture
def fake():
    return FakeSupabase()


@pytest.fixture
def sb_store(fake):
    return SupabaseAnalysisStore("https://proj.supabase.co", KEY, transport=httpx.MockTransport(fake))


@pytest.fixture
def sb_client(app, sb_store):
    app.dependency_overrides[routes.get_analysis_store] = lambda: sb_store
    return TestClient(app)


def test_full_flow_on_supabase_store(sb_client, fake):
    created = upload(sb_client, "ds.pdf", make_pdf(ML_JD)).json()
    jd_id = created["jd_id"]
    assert sb_client.get(f"/api/v1/jds/{jd_id}").json() == created      # skills keep their order
    assert sb_client.get("/api/v1/jds").json()["items"][0]["skill_count"] == 3
    new = [{"skill_name": "System Design", "category_code": "SYSD", "evidence": "added", "confidence": "medium"}]
    assert sb_client.patch(f"/api/v1/jds/{jd_id}/skills", json={"skills": new}).json()["skills"] == new
    assert sb_client.delete(f"/api/v1/jds/{jd_id}").status_code == 200
    assert sb_client.get(f"/api/v1/jds/{jd_id}").status_code == 404
    assert fake.rows == {}


def test_unknown_id_and_patch_missing(sb_client):
    missing = str(uuid.uuid4())
    assert sb_client.get(f"/api/v1/jds/{missing}").status_code == 404
    assert sb_client.patch(f"/api/v1/jds/{missing}/skills", json={"skills": []}).status_code == 404


def test_supabase_failure_is_503_without_leaking(sb_client, fake):
    fake.fail = True
    r = sb_client.get("/api/v1/jds")
    assert r.status_code == 503 and r.json()["error"]["code"] == "STORAGE_ERROR"
    assert KEY not in r.text and "boom" not in r.text


def test_analysis_saved_with_one_atomic_rpc_call(sb_client, fake):
    upload(sb_client, "ds.pdf", make_pdf(ML_JD))
    writes = [r for r in fake.requests if r.method == "POST"]
    assert [r.url.path for r in writes] == ["/rest/v1/rpc/save_jd_analysis"]


def test_config_requires_credentials_for_supabase():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, storage_backend="supabase")
    s = Settings(_env_file=None, storage_backend="supabase", supabase_url="https://x.supabase.co",
                 supabase_service_role_key=KEY)
    assert s.storage_backend == "supabase"
    assert KEY not in repr(s)
