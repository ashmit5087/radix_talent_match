def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] and body["version"] and body["docs_url"] == "/docs"


def test_health_needs_no_llm_or_embedding_model(client, fake_llm):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert fake_llm.calls == 0


def test_docs_and_openapi_available(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for p in ["/", "/health", "/api/v1/jds/categories", "/api/v1/jds/analyze", "/api/v1/jds/search",
              "/api/v1/jds", "/api/v1/jds/{jd_id}", "/api/v1/jds/{jd_id}/skills", "/api/v1/jds/index",
              "/api/v1/jds/provider-info"]:
        assert p in paths
    analyze = paths["/api/v1/jds/analyze"]["post"]
    assert "multipart/form-data" in analyze["requestBody"]["content"]
    for status in ["400", "413", "415", "422", "429", "502", "503", "504"]:
        assert status in analyze["responses"]
    assert set(paths["/api/v1/jds/{jd_id}/skills"]) == {"get", "patch"}
    assert set(paths["/api/v1/jds/{jd_id}"]) == {"get", "delete"}
    assert "application/json" in paths["/api/v1/jds/search"]["post"]["requestBody"]["content"]
