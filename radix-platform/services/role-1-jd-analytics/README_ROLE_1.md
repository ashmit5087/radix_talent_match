# RADIX JD Analytics (Role 1)

A standalone backend that reads a job description (PDF or DOCX), uses an LLM to extract the skills it requires, labels each skill with a RADIX category, saves the result under a `jd_id`, and returns validated JSON. The extracted text is also indexed in a local ChromaDB so previously analysed JDs can be searched by meaning.

Full endpoint reference with request/response examples: [docs/api-contract.md](docs/api-contract.md). Live, interactive version: `/docs`.

Backend only: there is no frontend here, and the other four RADIX roles are not implemented.

---

## 1. Features and non-goals

Features
- Upload PDF/DOCX, validate it, extract text in memory.
- Gemini-based skill extraction with Pydantic validation and anti-fabrication checks.
- Optional deterministic fallback extraction when Gemini is unavailable. Enable it with `LLM_FALLBACK_ENABLED=true`.
- Output in the agreed RADIX schema (`ExtractedSkillList`) plus a `jd_id`, so Skill Matching (Role 5) and the frontend can fetch the analysis later.
- Saved analyses can be listed, read, corrected (PATCH) and deleted.
- Local persistent vector index (ChromaDB) with local open-source embeddings.
- Semantic search, listing, single-document delete, full index reset.
- Swagger UI / ReDoc / OpenAPI generated from the code.
- Pytest suite that needs no API key, no network and no model download.

Non-goals
- No frontend, no resume parsing, no profile/readiness/matching logic (other roles).
- No OCR: scanned image-only PDFs are rejected.
- No RAG: search results are never sent to an LLM.
- No authentication (local development service).

## 2. Request lifecycle

```
PDF/DOCX upload -> file validation -> text extraction -> LLM skill extraction
 -> Pydantic validation -> ChromaDB chunking and indexing -> JSON response
```

What happens on `POST /api/v1/jds/analyze`:

1. Validate: extension (.pdf/.docx), real file signature, size (default 10 MB). Errors: 415 / 400 / 413.
2. Extract text from the bytes in memory (pypdf for PDF, python-docx for DOCX including tables). Nothing is executed and no temp file is created, so there is nothing to clean up. Encrypted, corrupt, empty and textless files get a clear 400; text over the limit gets 413.
3. LLM extraction: the text is sent to Gemini inside `<job_description>` tags with rules saying it is data only. Gemini returns JSON constrained by a schema (company, role, skills).
4. Validation and grounding (`app/services/jd_analyzer.py`):
   - JSON must parse and match the Pydantic models, otherwise 502 `LLM_BAD_RESPONSE`.
   - `company` and `role` are kept only if they literally appear in the JD text.
   - Duplicate skills are merged. If neither the evidence quote nor the skill name appears in the JD, confidence is capped at `low`.
5. Index: the text is cut into overlapping chunks (default 1000 chars, 200 overlap), embedded locally and stored in ChromaDB with metadata.
6. Save the analysis (company, role, skills) under a new `jd_id` in a local SQLite file and respond with the `ExtractedSkillList` fields plus `jd_id`. The vector step stores chunks and embeddings; the response itself only uses the shared skill schema (and `jd_id`).

How evidence and confidence work: the LLM must return a short quote as `evidence` and a `confidence` of `high` (explicitly required), `medium` (implied or "preferred") or `low` (weak). Step 4 then downgrades skills the text does not support.

If analysis succeeds but indexing fails: you still get `200`, the analysis is saved, and headers say `X-Indexing-Status: failed` and `X-Indexing-Error: <code>` (the JD is just not searchable). On success the headers are `X-Indexing-Status: indexed` and `X-Indexed-Chunks`. The shared schema is unchanged. If the LLM fails, nothing is saved or indexed and an error is returned.

## 3. Folder structure

```
radix-jd-analytics/
  app/
    main.py                     FastAPI app, Swagger metadata
    config.py                   Settings from environment / .env (validated)
    schemas.py                  Shared RADIX schema + API models
    errors.py                   Error format, handlers, Swagger error examples
    api/routes.py               All endpoints
    services/
      document_parser.py        Validate and extract text (PDF/DOCX)
      llm_client.py             Gemini integration + typed errors (swap providers here)
      jd_analyzer.py            Prompt, retries, validation, grounding
      analysis_store.py         Saved analyses (SQLite, default): jd_id, company, role, skills
      supabase_store.py         Same interface, stored in Supabase (optional)
      embedding_service.py      Local Sentence Transformers embeddings (lazy loaded)
      vector_store.py           ChromaDB: chunking, index, search, list, delete, clear
  data/chroma/                  Local index (generated, git-ignored)
  docs/api-contract.md          Endpoint reference with examples
  contracts/                    JSON schemas generated from the models (skill, jd-analysis)
  supabase/migrations/          SQL for the Supabase tables (optional backend)
  tests/                        Pytest suite
  .env.example  .gitignore  requirements.txt  README.md
```

## 4. Setup (Windows PowerShell)

Prerequisites: Python 3.10+ (3.11/3.12 recommended), about 2 GB free disk for PyTorch plus the model, and internet for the first run.

```powershell
cd radix-jd-analytics
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If activation is blocked:  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env        # set GEMINI_API_KEY
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs. Other URLs: http://127.0.0.1:8000/openapi.json and http://127.0.0.1:8000/redoc.

Get a Gemini key at https://aistudio.google.com/apikey. Never commit `.env`.

### Environment variables (`.env.example`)

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | gemini | Only `gemini` is implemented |
| `GEMINI_API_KEY` | (empty) | Required for `/analyze` |
| `GEMINI_MODEL` | gemini-2.5-flash | Any Gemini model id your key can use |
| `LLM_TIMEOUT_SECONDS` | 60 | Per-call timeout |
| `LLM_MAX_RETRIES` | 2 | Retries for transient errors only (429, timeout, 5xx) |
| `LLM_RETRY_BACKOFF_SECONDS` | 1.0 | Doubles each retry |
| `MAX_UPLOAD_SIZE_MB` | 10 | Upload limit |
| `MAX_EXTRACTED_TEXT_CHARS` | 60000 | Extracted-text limit |
| `MAX_PDF_PAGES` | 200 | PDF page limit |
| `CHROMA_PERSIST_DIRECTORY` | ./data/chroma | Index location (relative to the project folder) |
| `CHROMA_COLLECTION_NAME` | jd_chunks | Collection name |
| `CORS_ORIGINS` | http://localhost:5173,http://localhost:3000 | Browser origins allowed to call the API (comma-separated, exact) |
| `STORAGE_BACKEND` | sqlite | `sqlite` or `supabase` for saved analyses |
| `JD_DATABASE_PATH` | ./data/jd_analyses.sqlite3 | SQLite file (when `sqlite`) |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | (empty) | Required when `supabase` |
| `EMBEDDING_MODEL_NAME` | sentence-transformers/all-MiniLM-L6-v2 | Local embedding model |
| `CHUNK_SIZE_CHARS` / `CHUNK_OVERLAP_CHARS` | 1000 / 200 | Chunking |

Invalid values stop the server at startup with a clear message.

## 5. Try it in Swagger UI

1. Open `/docs`, expand `POST /api/v1/jds/analyze`, click Try it out.
2. Choose a PDF or DOCX in `file`, click Execute. Copy the `jd_id` from the JSON; check `x-indexing-status` under Response headers.
3. `GET /api/v1/jds/{jd_id}` and `GET /api/v1/jds/{jd_id}/skills` read it back; `GET /api/v1/jds` lists everything saved.
4. `PATCH /api/v1/jds/{jd_id}/skills` to correct skills; `POST /api/v1/jds/search` with `{"query": "experience building predictive models", "top_k": 5}`.
5. `DELETE /api/v1/jds/{jd_id}` removes one JD (analysis and indexed text). `DELETE /api/v1/jds/index?confirm=true` clears the search index only.

## 6. Endpoints

Summary (details, examples and error bodies: [docs/api-contract.md](docs/api-contract.md)).

| Method and path | Purpose | Main status codes |
|---|---|---|
| `GET /` | Service name, version, link to /docs | 200 |
| `GET /health` | Liveness only. Does not call Gemini, open ChromaDB or load the model | 200 |
| `POST /api/v1/jds/analyze` | Multipart `file` (PDF/DOCX) -> `jd_id` + `ExtractedSkillList`; saves and indexes | 200, 400, 413, 415, 422, 429, 502, 503, 504 |
| `GET /api/v1/jds` | List saved analyses | 200, 503 |
| `GET /api/v1/jds/{jd_id}` | One saved analysis | 200, 404, 422, 503 |
| `GET /api/v1/jds/{jd_id}/skills` | Only the skills of one analysis | 200, 404, 422, 503 |
| `PATCH /api/v1/jds/{jd_id}/skills` | Replace the skill list with a corrected one | 200, 404, 422, 503 |
| `DELETE /api/v1/jds/{jd_id}` | Delete the analysis and its indexed text (destructive) | 200, 404, 422, 503 |
| `POST /api/v1/jds/search` | Body `{query (1-1000 chars), top_k (1-20, default 5)}` -> nearest chunks | 200, 409, 422, 503 |
| `DELETE /api/v1/jds/index?confirm=true` | Clear the search index; saved analyses stay (destructive) | 200, 400, 503 |
| `GET /api/v1/jds/categories` | All 13 category codes with descriptions | 200 |
| `GET /api/v1/jds/provider-info` | Configured models, whether a key is set (never the key) | 200 |

Error format (every error):

```json
{"error": {"code": "UNSUPPORTED_FILE_TYPE", "message": "Upload a PDF or DOCX file.", "details": null}}
```

| Status | Codes |
|---|---|
| 400 | EMPTY_FILE, CORRUPT_DOCUMENT, ENCRYPTED_DOCUMENT, NO_TEXT_FOUND, CONFIRMATION_REQUIRED |
| 404 | JD_NOT_FOUND (also NOT_FOUND for unknown routes) |
| 409 | EMBEDDING_MODEL_MISMATCH |
| 413 | FILE_TOO_LARGE, EXTRACTED_TEXT_TOO_LARGE, TOO_MANY_PAGES, DOCUMENT_TOO_LARGE |
| 415 | UNSUPPORTED_FILE_TYPE |
| 422 | VALIDATION_ERROR (details lists field and reason, never your input) |
| 429 | LLM_RATE_LIMITED |
| 502 | LLM_BAD_RESPONSE |
| 503 | LLM_NOT_CONFIGURED, LLM_AUTH_FAILED, LLM_UNAVAILABLE, EMBEDDING_UNAVAILABLE, VECTOR_STORE_ERROR, STORAGE_ERROR |
| 504 | LLM_TIMEOUT |
| 500 | INTERNAL_ERROR (no internals; traceback only in the server log) |

## 7. RADIX shared schema

No shared schema file existed in the workspace, so the models in `app/schemas.py` follow the agreed definition exactly. If your team already has `shared_schema.py`, replace `Skill`, `ExtractedSkillList`, `CategoryCode` and `CATEGORY_DESCRIPTIONS` with imports from it.

Categories: COD Coding, DSA Data Structures & Algorithms, OOD Object-Oriented Design, APTI Aptitude, COMM Communication, AI Artificial Intelligence, CLOUD Cloud Computing, SQL SQL, SWE Software Engineering, SYSD System Design, NETW Networking, OS Operating Systems, OTHER anything else.

`source_type` is always `"jd"`. `source_file` is the bare file name, never a path.

Sample response (illustrative):

```json
{
  "source_type": "jd",
  "source_file": "data_scientist.pdf",
  "company": "Example Company",
  "role": "Data Scientist",
  "skills": [
    {"skill_name": "Python", "category_code": "COD",
     "evidence": "Proficiency in Python programming", "confidence": "high"}
  ]
}
```

## 8. ChromaDB, embeddings and search in plain language

Why a vector database: keyword search misses paraphrases. An embedding model turns a piece of text into a list of numbers (a vector, 384 numbers for MiniLM) so that texts with similar meaning get nearby vectors. ChromaDB stores those vectors and quickly finds the nearest ones to a query vector.

What is stored, per chunk, in collection `jd_chunks`:
- the chunk text
- its embedding vector
- metadata: jd_id, source_file, company, role, chunk_index, chunk_count, indexed_at

How search works: your query is embedded with the same model, ChromaDB returns the nearest chunks by cosine distance, and the API returns them with their source document. Distance guide: 0 means identical direction, larger means less similar. It is not a probability or percentage; only compare distances within one query. The collection records its embedding model name and the app refuses to open it with a different model (409) so vectors are never mixed.

Search is separate from extraction: `/analyze` always returns the RADIX schema, whether or not search is ever used.

Embedding model: `sentence-transformers/all-MiniLM-L6-v2`, runs on your CPU. First use downloads about 90 MB from Hugging Face (internet needed once); afterwards it loads from the local cache (on Windows under `C:\Users\<you>\.cache\huggingface`). Expect roughly 0.5 GB of RAM and a few seconds for the first load; each request after that is fast. It loads on first index/search, not at startup. If it cannot load you get 503 `EMBEDDING_UNAVAILABLE`; the app never substitutes fake vectors.

## 9. Where data lives and what survives a restart

| Data | Where | Survives restart? |
|---|---|---|
| Original PDF/DOCX | Nowhere (parsed in memory, discarded) | Never stored |
| Extracted text chunks | ChromaDB (`data/chroma/`) | Yes |
| Embeddings and metadata | ChromaDB (`data/chroma/`) | Yes |
| Saved analysis (jd_id, source file name, company, role, skills) | SQLite file (`data/jd_analyses.sqlite3`) | Yes (holds no JD text) |
| API keys | `.env` / environment | n/a |
| Embedding model files | Hugging Face cache | Yes |

Important: the indexed chunks contain the JD text. Not saving the upload does not remove that text; use `DELETE /api/v1/jds/{jd_id}`, which removes both the saved analysis and its chunks.

Inspect: `GET /api/v1/jds` (saved analyses), or the vector index in Python:

```python
import chromadb
c = chromadb.PersistentClient(path="data/chroma").get_collection("jd_chunks")
print(c.count()); print(c.peek(2))
```

Delete one JD: `DELETE /api/v1/jds/{jd_id}`. Reset the search index: `DELETE /api/v1/jds/index?confirm=true` (saved analyses stay), or stop the server and delete the contents of `data/chroma/`. Reset saved analyses: stop the server and delete `data/jd_analyses.sqlite3`. Use a different location by setting `CHROMA_PERSIST_DIRECTORY` (relative to the project folder, or absolute). `.gitignore` excludes everything in `data/chroma/` except `.gitkeep`, and `*.sqlite3`.

### Using Supabase for saved analyses (shared database)

By default saved analyses live in a local SQLite file. The team architecture uses Supabase as the shared source of truth, so Role 1 can store them there instead. ChromaDB (search index) stays local either way.

Tables (Role 1 owns them): `jd_analyses` (id, source_file, company, role, indexing_status, chunk_count, created_at, updated_at) and `jd_skills` (id, jd_id -> jd_analyses.id with ON DELETE CASCADE, skill_name, category_code, evidence, confidence, position). Category and confidence are enforced by CHECK constraints, skill names are unique per JD, and row-level security is on with no public policies, so only the backend's service-role key can access them. `save_jd_analysis` and `replace_jd_skills` are SQL functions so an analysis and its skills are written in one transaction.

Setup:
1. Create a Supabase project. In Project Settings > API copy the project URL and the `service_role` key.
2. Open the SQL Editor, paste the contents of `supabase/migrations/001_role1_jd_tables.sql`, and run it.
3. In `.env` set `STORAGE_BACKEND=supabase`, `SUPABASE_URL=...`, `SUPABASE_SERVICE_ROLE_KEY=...` and restart the server.
4. Analyze a JD, then check the Table Editor: one row in `jd_analyses`, its skills in `jd_skills`.

The service-role key bypasses security rules: keep it in `.env` on the backend only, never in the React app or Git. The API responses do not change. Verified by unit tests against a fake of Supabase's REST API; not yet run against a real Supabase project.

### Frontend access (CORS) and shared contract files

- A React app on another port can call this API because CORS is enabled for the origins in `CORS_ORIGINS` (default: Vite `localhost:5173` and `localhost:3000`). Add your frontend's exact origin there if it differs. The `X-Indexing-*` response headers are exposed so JavaScript can read them.
- `contracts/skill.schema.json` and `contracts/jd-analysis.schema.json` are generated from the Pydantic models. After changing `app/schemas.py`, run `python -m app.utils.contracts`; a test fails if the committed files are out of date.

## 10. What is sent where, and privacy

- Sent to Gemini (Google): the full extracted JD text plus the extraction instructions. The file itself is not uploaded. Google's handling and retention follow your API plan's terms, so do not upload confidential documents unless that is acceptable.
- Embedded locally: JD chunks and search queries. These never leave your machine.
- Logs: file name, type and character counts, error codes. Document text and API keys are not logged.
- API responses never include API keys, file-system paths or stack traces.

## 11. Tests

```powershell
python -m pytest -q
```

The suite uses a fake LLM and a deterministic test embedder (word hashing) with a temporary ChromaDB per test; it needs no key, no network and never touches `data/chroma`. It covers: root/health/docs/OpenAPI, categories, PDF and DOCX extraction, bad/empty/corrupt/encrypted/textless/oversized files, successful analysis, malformed LLM output, rate-limit/timeout/retry behaviour, fabricated-detail removal, prompt-injection handling, indexing, search, empty-index search, list/delete/clear, persistence across a reopened store, model-mismatch detection, validation errors, JSON serializability, schema consistency, no stored uploads, and no secret or path leaks.

Result in the environment where this was built: `65 passed`.

Because the test embedder is lexical, the tests prove the plumbing (index, rank, persist, delete) but not MiniLM's semantic quality. Check that with the real model (section 5).

## 12. Troubleshooting

| Problem | Fix |
|---|---|
| 503 `LLM_NOT_CONFIGURED` | Set `GEMINI_API_KEY` in `.env`, restart the server |
| 503 `LLM_AUTH_FAILED` | Key invalid or lacks access; create a new key |
| 429 `LLM_RATE_LIMITED` | Free-tier quota hit (retried automatically 2 times). Wait a minute, or use a model/key with more quota |
| 504 `LLM_TIMEOUT` | Raise `LLM_TIMEOUT_SECONDS`; try again |
| 502 `LLM_BAD_RESPONSE` | Model returned unusable output; retry, or try another `GEMINI_MODEL` |
| `X-Indexing-Status: failed` / `EMBEDDING_UNAVAILABLE` | Run `pip install sentence-transformers`; make sure the first run has internet to download the model; check disk space |
| 409 `EMBEDDING_MODEL_MISMATCH` | You changed `EMBEDDING_MODEL_NAME`. Clear the index or use a new `CHROMA_COLLECTION_NAME` |
| 400 `CORRUPT_DOCUMENT` / `NO_TEXT_FOUND` | Re-export the file; scanned images need OCR first |
| 503 `STORAGE_ERROR` | `data/jd_analyses.sqlite3` is locked or not writable; check the folder permissions |
| 503 `VECTOR_STORE_ERROR` | Check the folder is writable and not used by another process; reset it if corrupted |
| PowerShell blocks activation | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |

## 13. Using the API from another RADIX role

```python
import requests

with open("data_scientist.pdf", "rb") as f:
    r = requests.post("http://127.0.0.1:8000/api/v1/jds/analyze", files={"file": f}, timeout=120)
r.raise_for_status()
jd_skills = r.json()          # ExtractedSkillList fields + jd_id, ready for Role 5
jd_id = jd_skills["jd_id"]    # later: GET /api/v1/jds/{jd_id}/skills
print(r.headers.get("X-Indexing-Status"))   # optional; ignore if you do not care about search
```

Role 5 can consume `jd_skills["skills"]` and `jd_skills["source_file"]` directly, or store `jd_id` and fetch `GET /api/v1/jds/{jd_id}/skills` when needed. Other roles do not need to know about ChromaDB.

## 14. Limitations and ideas

- No OCR; no authentication; single-process local service.
- Skill extraction quality depends on the Gemini model; JDs over the character limit are rejected rather than truncated.
- The Gemini call is exercised only through mocks in the automated tests; verify with a real key.
- Possible next steps: OCR, more LLM providers (add a class in `llm_client.py`), section-aware chunking, authentication, a re-index endpoint.
# Role 1 — JD Analytics

## LLM fallback

Gemini remains the primary extractor. To enable the bundled deterministic
fallback when Gemini is not configured, rate-limited, unavailable, times out,
or returns invalid output, set this in the service `.env`:

```env
LLM_FALLBACK_ENABLED=true
```

The fallback extracts grounded company, role, and known skills directly from
the uploaded JD text. It does not call an external provider and does not infer
skills that are absent from the document. Keep it disabled when strict
provider-failure responses are required.
