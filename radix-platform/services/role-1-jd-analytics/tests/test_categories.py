from app.schemas import CATEGORY_DESCRIPTIONS


def test_categories_endpoint(client):
    r = client.get("/api/v1/jds/categories")
    assert r.status_code == 200
    cats = {c["code"]: c["description"] for c in r.json()["categories"]}
    assert set(cats) == {"COD", "DSA", "OOD", "APTI", "COMM", "AI", "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER"}
    assert cats["DSA"] == "Data Structures & Algorithms"
    assert cats == CATEGORY_DESCRIPTIONS


def test_provider_info_has_no_secrets(client, tmp_path):
    r = client.get("/api/v1/jds/provider-info")
    assert r.status_code == 200
    assert r.json()["llm_api_key_configured"] is True
    assert "test-secret-key-123" not in r.text
    assert str(tmp_path) not in r.text
