import json

from fastapi.testclient import TestClient

from app.schemas import ErrorResponse
from tests.conftest import ML_JD, make_pdf, upload


def _assert_error(r, status, code):
    assert r.status_code == status
    body = r.json()
    ErrorResponse.model_validate(body)
    assert body["error"]["code"] == code


def test_unsupported_type_415(client):
    _assert_error(upload(client, "jd.txt", b"hello"), 415, "UNSUPPORTED_FILE_TYPE")


def test_empty_and_corrupt_400(client):
    _assert_error(upload(client, "jd.pdf", b""), 400, "EMPTY_FILE")
    _assert_error(upload(client, "jd.pdf", b"%PDF-1.4 junk"), 400, "CORRUPT_DOCUMENT")


def test_oversize_413(client):
    _assert_error(upload(client, "jd.pdf", b"%PDF-" + b"0" * (2 * 1024 * 1024)), 413, "FILE_TOO_LARGE")


def test_missing_file_422(client):
    r = client.post("/api/v1/jds/analyze")
    _assert_error(r, 422, "VALIDATION_ERROR")


def test_invalid_search_params_422(client):
    for body in [{"query": "x", "top_k": 0}, {"query": "x", "top_k": 21}, {"query": ""},
                 {"query": "   "}, {"query": "a" * 1001}, {"top_k": 3}]:
        _assert_error(client.post("/api/v1/jds/search", json=body), 422, "VALIDATION_ERROR")


def test_unknown_route_uses_error_format(client):
    _assert_error(client.get("/nope"), 404, "NOT_FOUND")


def test_unexpected_error_does_not_leak(app, settings):
    from app.api import routes

    def boom():
        raise RuntimeError(f"secret internals at {settings.chroma_path} key test-secret-key-123")

    app.dependency_overrides[routes.get_vector_store_provider] = lambda: boom
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/v1/jds/search", json={"query": "python"})
    _assert_error(r, 500, "INTERNAL_ERROR")
    assert "secret" not in r.text and "Traceback" not in r.text


def test_no_secrets_or_paths_in_any_response(client, settings, tmp_path):
    responses = [
        upload(client, "jd.pdf", make_pdf(ML_JD)),
        client.post("/api/v1/jds/search", json={"query": "python"}),
        client.get("/api/v1/jds"),
        client.get("/api/v1/jds/provider-info"),
        client.get("/"), client.get("/health"),
        upload(client, "jd.txt", b"x"),
    ]
    for r in responses:
        json.dumps(r.json())  # JSON-serializable
        assert "test-secret-key-123" not in r.text
        assert str(tmp_path) not in r.text          # no local filesystem path
        assert "data/chroma" not in r.text and "\\\\" not in r.text
