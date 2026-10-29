"""FastAPI application factory. Run with:  uvicorn app.main:app --reload"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import SERVICE_NAME, SERVICE_VERSION, jd_router, system_router
from app.config import get_settings
from app.errors import register_error_handlers

DESCRIPTION = """
**Role 1 - JD Analytics.** Upload a job description (PDF/DOCX) and receive the skills it requires
as validated RADIX-schema JSON under a reusable `jd_id`. Extracted text is also indexed in a local ChromaDB so it can be searched by meaning.

**Request lifecycle**

`PDF/DOCX upload -> file validation -> text extraction -> LLM skill extraction -> Pydantic validation -> ChromaDB chunking and indexing -> JSON response`

The vector indexing step stores text chunks and embeddings; the response itself always uses the shared RADIX skill schema.

**Error format** (all errors): `{"error": {"code": "...", "message": "...", "details": null}}`
"""

TAGS = [
    {"name": "System", "description": "Service info and health."},
    {"name": "JD Analytics", "description": "Upload a JD, get RADIX skill JSON with a jd_id, then read, list or correct saved analyses."},
    {"name": "Semantic Search", "description": "Search indexed JD text by meaning (ChromaDB)."},
    {"name": "Index Management", "description": "Delete saved JDs or clear the search index. All destructive."},
]


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = FastAPI(
        title=SERVICE_NAME, version=SERVICE_VERSION, description=DESCRIPTION, openapi_tags=TAGS,
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
    )
    # Let the React frontend (a different origin) call this API from the browser.
    # Only the listed origins are allowed; X-Indexing-* headers are exposed so JavaScript can read them.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Indexing-Status", "X-Indexed-Chunks", "X-Indexing-Error"],
        allow_credentials=False,
    )
    register_error_handlers(app)
    app.include_router(system_router)
    app.include_router(jd_router)
    return app


app = create_app()
