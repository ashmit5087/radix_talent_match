"""HTTP endpoints. Each handler is intentionally short: parse -> analyze -> index -> respond."""
import logging
import uuid
from functools import lru_cache
from typing import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.config import Settings, get_settings
from app.errors import AppError, error_responses
from app.schemas import (
    CATEGORY_DESCRIPTIONS, CategoriesResponse, CategoryInfo, ClearIndexResponse, DeleteJDResponse,
    HealthResponse, JDAnalysisResponse, JDListResponse, JDSkillsResponse, JDSummary, ProviderInfo,
    RootResponse, SearchRequest, SearchResponse, UpdateSkillsRequest,
)
from app.services.analysis_store import AnalysisStore
from app.services.supabase_store import SupabaseAnalysisStore
from app.services.document_parser import parse_document, sanitize_filename
from app.services.embedding_service import SentenceTransformerEmbedder
from app.services.jd_analyzer import JDAnalyzer
from app.services.llm_client import LLMClient, LLMError, build_llm_client
from app.services.vector_store import VectorStore

logger = logging.getLogger("radix.routes")

system_router = APIRouter(tags=["System"])
jd_router = APIRouter(prefix="/api/v1/jds")

SERVICE_NAME = "RADIX JD Analytics API"
SERVICE_VERSION = "1.0.0"
SERVICE_DESCRIPTION = (
    "Role 1: upload a job description (PDF/DOCX), extract skills with an LLM, "
    "and search indexed JD text semantically."
)


# ----------------------------------------------------------------------------------------
# Dependencies. Providers are callables so a failure in the LLM or vector DB only affects
# the step that needs it, and so tests can swap in fakes via app.dependency_overrides.
# ----------------------------------------------------------------------------------------
@lru_cache
def _embedder(model_name: str) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(model_name)


@lru_cache
def _store(path: str, collection: str, model: str, size: int, overlap: int) -> VectorStore:
    return VectorStore(path, collection, _embedder(model), size, overlap)


def get_vector_store_provider(settings: Settings = Depends(get_settings)) -> Callable[[], VectorStore]:
    return lambda: _store(
        str(settings.chroma_path), settings.chroma_collection_name, settings.embedding_model_name,
        settings.chunk_size_chars, settings.chunk_overlap_chars,
    )


_analysis_stores: dict = {}


def get_analysis_store(settings: Settings = Depends(get_settings)):
    """SQLite file by default; Supabase when STORAGE_BACKEND=supabase. Both have the same methods."""
    if settings.storage_backend == "supabase":
        key = ("supabase", settings.supabase_url)
        if key not in _analysis_stores:
            _analysis_stores[key] = SupabaseAnalysisStore(
                settings.supabase_url, settings.supabase_service_role_key.get_secret_value())
    else:
        key = ("sqlite", str(settings.jd_db_path))
        if key not in _analysis_stores:
            _analysis_stores[key] = AnalysisStore(settings.jd_db_path)
    return _analysis_stores[key]


def get_vector_store(provider: Callable[[], VectorStore] = Depends(get_vector_store_provider)) -> VectorStore:
    return provider()


def get_llm_provider(settings: Settings = Depends(get_settings)) -> Callable[[], LLMClient | None]:
    def provide() -> LLMClient | None:
        try:
            return build_llm_client(settings)
        except LLMError as exc:
            if settings.llm_fallback_enabled:
                logger.warning("Gemini unavailable; Role 1 will use deterministic fallback: %s", exc)
                return None
            raise JDAnalyzer._to_app_error(exc) from None
    return provide


# ----------------------------------------------------------------------------------------
# System
# ----------------------------------------------------------------------------------------
@system_router.get("/", response_model=RootResponse, summary="Service information")
def root() -> RootResponse:
    """Returns the service name, version, a short description and the link to Swagger UI.

    **Side effects:** none."""
    return RootResponse(service=SERVICE_NAME, version=SERVICE_VERSION,
                        description=SERVICE_DESCRIPTION, docs_url="/docs")


@system_router.get("/health", response_model=HealthResponse, summary="Application health")
def health() -> HealthResponse:
    """Basic liveness check: answers `{"status": "ok"}` if the app is running.

    It deliberately does **not** call Gemini, open ChromaDB or load the embedding model,
    so it is instant and works without an API key.

    **Side effects:** none."""
    return HealthResponse()


# ----------------------------------------------------------------------------------------
# JD analytics (Role 1)
# NOTE: literal paths (/categories, /search, /index, ...) are declared before /{jd_id}.
# ----------------------------------------------------------------------------------------
def _summary(row: dict) -> JDSummary:
    return JDSummary(
        jd_id=row["jd_id"], source_file=row["source_file"], company=row["company"], role=row["role"],
        skill_count=len(row["skills"]), indexing_status=row["indexing_status"], chunk_count=row["chunk_count"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


def _get_or_404(store, jd_id: UUID) -> dict:
    row = store.get(str(jd_id))
    if row is None:
        raise AppError(404, "JD_NOT_FOUND", "No saved JD analysis with this id.")
    return row


@jd_router.get("/categories", response_model=CategoriesResponse, tags=["JD Analytics"],
               summary="List RADIX skill categories")
def list_categories() -> CategoriesResponse:
    """Every supported `category_code` with its description (the 12 RADIX skill sets plus `OTHER`).

    **Side effects:** none."""
    return CategoriesResponse(categories=[CategoryInfo(code=c, description=d) for c, d in CATEGORY_DESCRIPTIONS.items()])


@jd_router.get("/provider-info", response_model=ProviderInfo, tags=["JD Analytics"],
               summary="Safe configuration info")
def provider_info(settings: Settings = Depends(get_settings)) -> ProviderInfo:
    """Which LLM and embedding model are configured. Never returns API keys or file-system paths.

    **Side effects:** none."""
    return ProviderInfo(
        llm_provider=settings.llm_provider, llm_model=settings.gemini_model,
        llm_api_key_configured=bool(settings.gemini_api_key.get_secret_value()),
        embedding_model=settings.embedding_model_name, chroma_collection=settings.chroma_collection_name,
    )


ANALYZE_DESCRIPTION = """
Upload a job description and get its skills as RADIX-schema JSON, saved under a new `jd_id`.

**What happens, in order**
1. **Validate** the file: extension (.pdf/.docx), real file signature, size (default 10 MB).
2. **Extract text** in memory (pypdf / python-docx). Nothing is written to disk.
3. **LLM extraction** (Gemini): finds company, role and skills, assigns a RADIX category, a short
   evidence quote and a confidence level. The model is told to treat the JD as data only.
4. **Pydantic validation** of the model's JSON; company/role/evidence are checked against the JD text.
5. **Index in ChromaDB**: the text is split into overlapping chunks, embedded locally and stored so it
   can be found later via `POST /api/v1/jds/search`.
6. **Save** the analysis (company, role, skills) under a new `jd_id` and **respond**.

**Storage side effects**
* The original PDF/DOCX is **not** stored.
* The saved analysis (`jd_id`, company, role, skills) is kept in a local SQLite file and survives restarts.
* The extracted text chunks, embeddings and metadata are kept in ChromaDB and survive restarts.
* `DELETE /api/v1/jds/{jd_id}` removes both.

**If analysis succeeds but indexing fails**: you still get `200`, the analysis is saved, and the headers say so
(the shared schema is not changed). The JD simply is not searchable.

| Header | Meaning |
|---|---|
| `X-Indexing-Status` | `indexed` or `failed` |
| `X-Indexed-Chunks` | Number of chunks stored (only when `indexed`) |
| `X-Indexing-Error` | Error code such as `EMBEDDING_UNAVAILABLE` (only when `failed`) |

If the LLM fails, **nothing** is saved or indexed and an error is returned.
"""

_ANALYZE_HEADERS = {
    "X-Indexing-Status": {"description": "`indexed` or `failed`.", "schema": {"type": "string"}},
    "X-Indexed-Chunks": {"description": "Chunks stored (when indexed).", "schema": {"type": "string"}},
    "X-Indexing-Error": {"description": "Error code (when indexing failed).", "schema": {"type": "string"}},
}


@jd_router.post(
    "/analyze", response_model=JDAnalysisResponse, tags=["JD Analytics"],
    summary="Analyze a job description (PDF or DOCX)", description=ANALYZE_DESCRIPTION,
    responses={200: {"description": "Skills extracted and saved. See the X-Indexing-* headers for indexing status.",
                     "headers": _ANALYZE_HEADERS},
               **error_responses(400, 413, 415, 422, 429, 502, 503, 504)},
)
def analyze_jd(
    response: Response,
    file: UploadFile = File(..., description="The job description, as a .pdf or .docx file."),
    settings: Settings = Depends(get_settings),
    llm_provider: Callable[[], LLMClient] = Depends(get_llm_provider),
    store_provider: Callable[[], VectorStore] = Depends(get_vector_store_provider),
    analyses = Depends(get_analysis_store),
) -> JDAnalysisResponse:
    # 1-2. validate + extract (read at most limit+1 bytes so huge uploads are rejected early)
    content = file.file.read(settings.max_upload_bytes + 1)
    parsed = parse_document(file.filename or "", content, settings)
    del content

    # 3-4. LLM extraction + validation (never returns a fake result: errors propagate)
    result = JDAnalyzer(llm_provider(), settings).analyze(parsed.text, sanitize_filename(file.filename))
    jd_id = str(uuid.uuid4())

    # 5. index in ChromaDB; a failure here must not hide the successful analysis
    status, n_chunks = "indexed", 0
    try:
        n_chunks = store_provider().index_document(
            jd_id=jd_id, source_file=result.source_file, text=parsed.text,
            company=result.company, role=result.role,
        )
        response.headers["X-Indexing-Status"] = "indexed"
        response.headers["X-Indexed-Chunks"] = str(n_chunks)
    except Exception as exc:
        code = exc.code if isinstance(exc, AppError) else "INDEXING_FAILED"
        logger.warning("Indexing failed: %s", code if isinstance(exc, AppError) else type(exc).__name__)
        status = "failed"
        response.headers["X-Indexing-Status"] = "failed"
        response.headers["X-Indexing-Error"] = code

    # 6. save the analysis; if that fails, do not leave orphan chunks behind
    try:
        analyses.save(jd_id, result, status, n_chunks)
    except Exception:
        if status == "indexed":
            try:
                store_provider().delete_chunks(jd_id)
            except Exception:
                pass
        raise
    return JDAnalysisResponse(jd_id=jd_id, **result.model_dump())


@jd_router.post(
    "/search", response_model=SearchResponse, tags=["Semantic Search"], summary="Semantic search over indexed JDs",
    responses=error_responses(409, 422, 503),
)
def search_jd(body: SearchRequest, store: VectorStore = Depends(get_vector_store)) -> SearchResponse:
    """Find indexed JD text chunks whose **meaning** is close to your query, even if the wording differs.

    The query is embedded locally with the same model used at indexing time, then ChromaDB returns
    the nearest chunks, each with its `jd_id`. `distance` is the raw cosine distance: **lower = closer**.
    It is not a probability or a percentage; only compare distances within one query's results.
    An empty index returns `results: []`.

    **Side effects:** none (read-only). The query text is not stored."""
    hits = store.search(body.query, body.top_k)
    return SearchResponse(query=body.query, top_k=body.top_k, count=len(hits), results=hits)


@jd_router.delete(
    "/index", response_model=ClearIndexResponse, tags=["Index Management"],
    summary="Clear the search index (destructive, development use)",
    responses=error_responses(400, 503, override={
        400: ("CONFIRMATION_REQUIRED", "Add ?confirm=true to confirm you want to clear the search index.",
              "Missing confirmation.")}),
)
def clear_index(
    confirm: bool = Query(False, description="Must be `true`, otherwise nothing is deleted."),
    store: VectorStore = Depends(get_vector_store),
) -> ClearIndexResponse:
    """**Destructive.** Deletes **every** chunk, embedding and metadata row in the ChromaDB collection.

    Saved analyses and their `jd_id`s are **kept** (other roles can still use them); the JDs just stop
    being searchable. Nothing happens unless you pass `confirm=true`. Cannot be undone."""
    if not confirm:
        raise AppError(400, "CONFIRMATION_REQUIRED",
                       "Add ?confirm=true to confirm you want to clear the search index.")
    return ClearIndexResponse(chunks_deleted=store.clear())


@jd_router.get("", response_model=JDListResponse, tags=["JD Analytics"], summary="List saved JD analyses",
               responses=error_responses(503))
def list_jds(analyses = Depends(get_analysis_store)) -> JDListResponse:
    """All saved analyses, newest first, with their `jd_id`, company, role, skill count and indexing status.

    **Side effects:** none (read-only)."""
    items = [_summary(r) for r in analyses.list_all()]
    return JDListResponse(count=len(items), items=items)


@jd_router.get("/{jd_id}", response_model=JDAnalysisResponse, tags=["JD Analytics"],
               summary="Get a saved JD analysis", responses=error_responses(404, 422, 503))
def get_jd(jd_id: UUID, analyses = Depends(get_analysis_store)) -> JDAnalysisResponse:
    """Returns the saved analysis (including any manual corrections made through `PATCH .../skills`).
    Same shape as the `analyze` response.

    **Side effects:** none (read-only)."""
    row = _get_or_404(analyses, jd_id)
    return JDAnalysisResponse(jd_id=row["jd_id"], source_type="jd", source_file=row["source_file"],
                              company=row["company"], role=row["role"], skills=row["skills"])


@jd_router.get("/{jd_id}/skills", response_model=JDSkillsResponse, tags=["JD Analytics"],
               summary="Get only the skills of a saved JD", responses=error_responses(404, 422, 503))
def get_jd_skills(jd_id: UUID, analyses = Depends(get_analysis_store)) -> JDSkillsResponse:
    """The skill list with its category mapping. Lightweight endpoint for Skill Matching (Role 5).

    **Side effects:** none (read-only)."""
    row = _get_or_404(analyses, jd_id)
    return JDSkillsResponse(jd_id=row["jd_id"], skills=row["skills"])


@jd_router.patch("/{jd_id}/skills", response_model=JDSkillsResponse, tags=["JD Analytics"],
                 summary="Correct the extracted skills", responses=error_responses(404, 422, 503))
def update_jd_skills(jd_id: UUID, body: UpdateSkillsRequest,
                     analyses = Depends(get_analysis_store)) -> JDSkillsResponse:
    """Replace the stored skill list with a corrected one (to fix a wrong category, remove a wrong skill,
    or add a missed one). Send the **complete** new list; every skill is validated against the RADIX schema.

    **Side effects:** overwrites the saved skills of this `jd_id`. The previous list is not kept.
    The searchable text chunks are unchanged (they hold JD text, not skills)."""
    _get_or_404(analyses, jd_id)
    names = [s.skill_name.strip().lower() for s in body.skills]
    if any(not n for n in names) or len(set(names)) != len(names):
        raise AppError(422, "VALIDATION_ERROR", "Skill names must be non-empty and unique (case-insensitive).")
    analyses.replace_skills(str(jd_id), [s.model_copy(update={"skill_name": s.skill_name.strip()}) for s in body.skills])
    return JDSkillsResponse(jd_id=str(jd_id), skills=analyses.get(str(jd_id))["skills"])


@jd_router.delete("/{jd_id}", response_model=DeleteJDResponse, tags=["Index Management"],
                  summary="Delete a saved JD and its indexed text (destructive)",
                  responses=error_responses(404, 422, 503))
def delete_jd(jd_id: UUID, analyses = Depends(get_analysis_store),
              store: VectorStore = Depends(get_vector_store)) -> DeleteJDResponse:
    """**Destructive.** Permanently deletes this JD's saved analysis **and** its chunks, embeddings and
    metadata in ChromaDB. Anything that still refers to this `jd_id` will get `404` afterwards.

    Original uploads are never stored, so there is no file to delete. Cannot be undone."""
    _get_or_404(analyses, jd_id)
    chunks = store.delete_chunks(str(jd_id))
    analyses.delete(str(jd_id))
    return DeleteJDResponse(jd_id=str(jd_id), chunks_deleted=chunks)
