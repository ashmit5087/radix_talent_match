"""Shared fixtures. No real LLM, no embedding-model download, no real ChromaDB directory."""
import io
import json
import re
import zlib

import pytest
from docx import Document
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.api import routes
from app.config import Settings, get_settings
from app.main import create_app
from app.services.analysis_store import AnalysisStore
from app.services.vector_store import VectorStore

ML_JD = (
    "Acme Analytics is hiring a Data Scientist. Key Responsibilities: build machine learning models "
    "for forecasting and predictive analytics. We are looking for strong Python programming and SQL skills. "
    "Good communication with stakeholders is expected."
)
CLOUD_JD = (
    "Nimbus Systems seeks a Cloud Engineer. You will deploy services on AWS, manage Kubernetes clusters "
    "and design resilient distributed system architecture. Networking knowledge is a plus."
)


class HashEmbedder:
    """Deterministic test-only embedder (bag-of-words hashing). NEVER used in the real app."""
    model_name = "test-hash-embedder"
    DIM = 256

    def embed(self, texts):
        out = []
        for t in texts:
            v = [0.0] * self.DIM
            for w in re.findall(r"[a-z]+", t.lower()):
                v[zlib.crc32(w.rstrip("s").encode()) % self.DIM] += 1.0
            norm = sum(x * x for x in v) ** 0.5 or 1.0
            out.append([x / norm for x in v])
        return out


class FakeLLM:
    provider_name = "fake"
    model_name = "fake-model"

    def __init__(self):
        self.calls = 0
        self.prompts = []
        self.error = None            # exception instance to raise
        self.error_times = None      # raise only this many times, then succeed
        self.response = json.dumps({
            "company": "Acme Analytics", "role": "Data Scientist",
            "skills": [
                {"skill_name": "Python", "category_code": "COD",
                 "evidence": "strong Python programming", "confidence": "high"},
                {"skill_name": "SQL", "category_code": "SQL", "evidence": "SQL skills", "confidence": "high"},
                {"skill_name": "Machine Learning", "category_code": "AI",
                 "evidence": "build machine learning models", "confidence": "high"},
            ],
        })

    def generate_json(self, system_prompt, user_prompt, response_model):
        self.calls += 1
        self.prompts.append((system_prompt, user_prompt))
        if self.error is not None and (self.error_times is None or self.calls <= self.error_times):
            raise self.error
        return self.response


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None, gemini_api_key="test-secret-key-123",
        chroma_persist_directory=str(tmp_path / "chroma"), jd_database_path=str(tmp_path / "jd.sqlite3"), llm_retry_backoff_seconds=0,
        llm_max_retries=2, max_upload_size_mb=1,
    )


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def store(settings):
    return VectorStore(settings.chroma_path, settings.chroma_collection_name, HashEmbedder(),
                       settings.chunk_size_chars, settings.chunk_overlap_chars)


@pytest.fixture
def analyses(settings):
    return AnalysisStore(settings.jd_db_path)


@pytest.fixture
def app(settings, fake_llm, store, analyses):
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[routes.get_llm_provider] = lambda: (lambda: fake_llm)
    application.dependency_overrides[routes.get_vector_store_provider] = lambda: (lambda: store)
    application.dependency_overrides[routes.get_analysis_store] = lambda: analyses
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


# ---- helpers to build sample documents in memory --------------------------------------
def make_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in re.findall(r".{1,90}(?:\s|$)", text):
        c.drawString(40, y, line.strip())
        y -= 14
        if y < 40:
            c.showPage()
            y = 800
    c.save()
    return buf.getvalue()


def make_blank_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    return buf.getvalue()


def make_docx(text: str) -> bytes:
    doc = Document()
    for para in text.split("\n"):
        doc.add_paragraph(para)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def upload(client, name, content, ctype="application/octet-stream"):
    return client.post("/api/v1/jds/analyze", files={"file": (name, content, ctype)})
