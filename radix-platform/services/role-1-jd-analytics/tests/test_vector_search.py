from app.services.analysis_store import AnalysisStore
from app.services.vector_store import VectorStore, chunk_text
from tests.conftest import CLOUD_JD, ML_JD, HashEmbedder, make_pdf, upload


def _index_two(client):
    upload(client, "ml.pdf", make_pdf(ML_JD))
    upload(client, "cloud.pdf", make_pdf(CLOUD_JD))


def test_chunking_overlaps_and_covers_text():
    text = " ".join(f"word{i}" for i in range(400))
    chunks = chunk_text(text, 200, 50)
    assert len(chunks) > 1 and all(len(c) <= 200 for c in chunks)
    assert chunks[0].split()[-1] in chunks[1]  # overlap
    assert chunk_text("short", 200, 50) == ["short"]


def test_index_and_search_finds_expected_document(client):
    _index_two(client)
    r = client.post("/api/v1/jds/search", json={"query": "experience building machine learning models", "top_k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["distance_metric"] == "cosine" and body["count"] == 2
    top = body["results"][0]
    assert top["source_file"] == "ml.pdf" and top["company"] == "Acme Analytics"
    assert top["chunk_index"] == 0 and isinstance(top["distance"], float)
    assert body["results"][0]["distance"] <= body["results"][1]["distance"]


def test_search_empty_collection(client):
    r = client.post("/api/v1/jds/search", json={"query": "anything"})
    assert r.status_code == 200 and r.json()["results"] == [] and r.json()["count"] == 0


def test_delete_removes_saved_analysis_and_chunks(client):
    ids = {}
    for name, text in [("ml.pdf", ML_JD), ("cloud.pdf", CLOUD_JD)]:
        ids[name] = upload(client, name, make_pdf(text)).json()["jd_id"]
    r = client.delete(f"/api/v1/jds/{ids['ml.pdf']}")
    assert r.status_code == 200 and r.json()["chunks_deleted"] >= 1 and r.json()["analysis_deleted"]
    assert client.get(f"/api/v1/jds/{ids['ml.pdf']}").status_code == 404
    assert client.delete(f"/api/v1/jds/{ids['ml.pdf']}").status_code == 404
    hits = client.post("/api/v1/jds/search", json={"query": "machine learning", "top_k": 20}).json()["results"]
    assert {h["jd_id"] for h in hits} == {ids["cloud.pdf"]}


def test_clear_index_requires_confirm_and_keeps_analyses(client):
    _index_two(client)
    assert client.delete("/api/v1/jds/index").status_code == 400
    assert client.post("/api/v1/jds/search", json={"query": "python"}).json()["count"] > 0
    r = client.delete("/api/v1/jds/index?confirm=true")
    assert r.status_code == 200 and r.json()["chunks_deleted"] >= 2
    assert client.post("/api/v1/jds/search", json={"query": "python"}).json()["results"] == []
    assert client.get("/api/v1/jds").json()["count"] == 2   # saved analyses survive


def test_index_survives_restart(settings, client):
    _index_two(client)
    reopened = VectorStore(settings.chroma_path, settings.chroma_collection_name, HashEmbedder())
    assert reopened.count() >= 2
    assert reopened.search("kubernetes aws", 1)[0]["source_file"] == "cloud.pdf"
    assert AnalysisStore(settings.jd_db_path).count() == 2   # saved analyses survive too


def test_embedding_model_mismatch_is_detected(settings, store):
    import pytest
    from app.errors import AppError

    class Other(HashEmbedder):
        model_name = "some-other-model"

    with pytest.raises(AppError) as e:
        VectorStore(settings.chroma_path, settings.chroma_collection_name, Other())
    assert e.value.status_code == 409
