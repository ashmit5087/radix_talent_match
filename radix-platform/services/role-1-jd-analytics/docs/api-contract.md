# RADIX JD Analytics (Role 1): API Reference

Base URL (local): `http://127.0.0.1:8000`  |  Interactive docs: `/docs`  |  ReDoc: `/redoc`  |  OpenAPI JSON: `/openapi.json`

All endpoints return JSON. There is no authentication (local service). Paths for Role 1 are under `/api/v1/jds`.
The examples below were produced by running the real application code with a mocked LLM and a test-only embedder, so the
field names and shapes are exact; the skill values and the search `distance` numbers are illustrative.

## 1. Concepts

**jd_id.** Every successful analysis is saved under a new UUID, the `jd_id`. Other roles (Skill Matching) and the frontend
should store this id and fetch the analysis with `GET /api/v1/jds/{jd_id}` instead of re-uploading the file.

**Shared schema.** The analyze response is the agreed `ExtractedSkillList` plus one extra field, `jd_id`.
Consumers that only know `ExtractedSkillList` can ignore `jd_id`.

| Field | Type | Notes |
|---|---|---|
| `source_type` | `"jd"` | Always `"jd"` in this module |
| `source_file` | string | Original file name only, never a path |
| `company` | string or null | Only set if the name appears in the JD text |
| `role` | string or null | Only set if the title appears in the JD text |
| `skills[]` | list of Skill | See below |

Skill: `skill_name` (string), `category_code` (one of the codes below), `evidence` (short quote or reason),
`confidence` (`high` / `medium` / `low`).

Category codes: `COD` Coding, `DSA` Data Structures & Algorithms, `OOD` Object-Oriented Design, `APTI` Aptitude,
`COMM` Communication, `AI` Artificial Intelligence, `CLOUD` Cloud Computing, `SQL` SQL, `SWE` Software Engineering,
`SYSD` System Design, `NETW` Networking, `OS` Operating Systems, `OTHER` anything else.

**Where data lives.** Original uploads: never stored. Saved analysis (jd_id, file name, company, role, skills):
SQLite file `data/jd_analyses.sqlite3`. JD text chunks + embeddings: ChromaDB in `data/chroma/`. Both survive restarts.

**Error format** (all errors):
```json
{"error": {"code": "STRING_CODE", "message": "Human readable text", "details": null}}
```
`details` is a list for validation errors (`location`, `message`, `type`) and `null` otherwise.

## 2. Endpoint index

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/jds/analyze` | Upload a JD, extract skills, save, index |
| GET | `/api/v1/jds` | List saved analyses |
| GET | `/api/v1/jds/{jd_id}` | Get one saved analysis |
| GET | `/api/v1/jds/{jd_id}/skills` | Get its skills only |
| PATCH | `/api/v1/jds/{jd_id}/skills` | Replace skills with a corrected list |
| DELETE | `/api/v1/jds/{jd_id}` | Delete analysis and indexed text (destructive) |
| POST | `/api/v1/jds/search` | Semantic search over indexed JD text |
| DELETE | `/api/v1/jds/index?confirm=true` | Clear the search index (destructive) |
| GET | `/api/v1/jds/categories` | Category codes and descriptions |
| GET | `/api/v1/jds/provider-info` | Configured models (no secrets) |
| GET | `/` | Service info |
| GET | `/health` | Liveness |

---

## 3. POST /api/v1/jds/analyze

Upload a job description and get its skills. This is the main endpoint.

**Request:** `multipart/form-data` with one field, `file` (.pdf or .docx, default max 10 MB).

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jds/analyze -F "file=@data_scientist.pdf"
```

**Pipeline:** validate file -> extract text in memory -> Gemini extraction -> Pydantic validation and grounding checks ->
chunk + embed + index in ChromaDB -> save analysis -> respond. If the LLM fails nothing is saved or indexed.

**Response 200**

```json
{
  "source_type": "jd",
  "source_file": "data_scientist.pdf",
  "company": "Acme Analytics",
  "role": "Data Scientist",
  "skills": [
    {
      "skill_name": "Python",
      "category_code": "COD",
      "evidence": "strong Python programming",
      "confidence": "high"
    },
    {
      "skill_name": "SQL",
      "category_code": "SQL",
      "evidence": "SQL skills",
      "confidence": "high"
    },
    {
      "skill_name": "Machine Learning",
      "category_code": "AI",
      "evidence": "build machine learning models",
      "confidence": "high"
    }
  ],
  "jd_id": "304cd76a-90ed-4dda-924c-3c64f5bb62a6"
}
```

**Response headers (indexing status).** The body never changes shape; indexing outcome is reported in headers:

| Header | When | Value |
|---|---|---|
| `X-Indexing-Status` | always | `indexed` or `failed` |
| `X-Indexed-Chunks` | indexed | number of chunks stored (this example: `1`) |
| `X-Indexing-Error` | failed | error code, e.g. `EMBEDDING_UNAVAILABLE` |

If indexing fails the analysis is still returned and saved (status `failed`), but the JD will not appear in search.

**Behaviour you can rely on**
- `company` / `role` are `null` unless they literally appear in the JD.
- Duplicate skills (case-insensitive) are merged.
- If neither the evidence nor the skill name appears in the JD text, `confidence` is lowered to `low`.
- Text inside the JD cannot change the extraction rules (it is passed as delimited data).
- Transient LLM errors (429, timeout, 5xx) are retried up to `LLM_MAX_RETRIES` times; other errors are not.

**Errors**

| Status | Code | Cause |
|---|---|---|
| 400 | EMPTY_FILE / CORRUPT_DOCUMENT / ENCRYPTED_DOCUMENT / NO_TEXT_FOUND | Unusable file |
| 413 | FILE_TOO_LARGE / EXTRACTED_TEXT_TOO_LARGE / TOO_MANY_PAGES / DOCUMENT_TOO_LARGE | A limit was exceeded |
| 415 | UNSUPPORTED_FILE_TYPE | Not .pdf or .docx |
| 422 | VALIDATION_ERROR | `file` missing |
| 429 | LLM_RATE_LIMITED | Gemini rate limit (after retries) |
| 502 | LLM_BAD_RESPONSE | Malformed or invalid LLM output |
| 503 | LLM_NOT_CONFIGURED / LLM_AUTH_FAILED / LLM_UNAVAILABLE / STORAGE_ERROR | Key missing/rejected, provider down, or saved-analysis DB failure |
| 504 | LLM_TIMEOUT | Gemini timed out |

Example (415):
```json
{
  "error": {
    "code": "UNSUPPORTED_FILE_TYPE",
    "message": "Upload a PDF or DOCX file.",
    "details": null
  }
}
```

---

## 4. GET /api/v1/jds

List saved analyses, newest first. Read-only.

```json
{
  "count": 1,
  "items": [
    {
      "jd_id": "304cd76a-90ed-4dda-924c-3c64f5bb62a6",
      "source_file": "data_scientist.pdf",
      "company": "Acme Analytics",
      "role": "Data Scientist",
      "skill_count": 3,
      "indexing_status": "indexed",
      "chunk_count": 1,
      "created_at": "2026-10-25T09:28:01+00:00",
      "updated_at": "2026-10-25T09:28:01+00:00"
    }
  ]
}
```

`indexing_status` is `indexed` or `failed`; `chunk_count` is the number of searchable chunks (0 if failed).

---

## 5. GET /api/v1/jds/{jd_id}

Return one saved analysis in the same shape as the analyze response (including any PATCH corrections).

```bash
curl http://127.0.0.1:8000/api/v1/jds/304cd76a-90ed-4dda-924c-3c64f5bb62a6
```

```json
{
  "source_type": "jd",
  "source_file": "data_scientist.pdf",
  "company": "Acme Analytics",
  "role": "Data Scientist",
  "skills": [
    {
      "skill_name": "Python",
      "category_code": "COD",
      "evidence": "strong Python programming",
      "confidence": "high"
    },
    {
      "skill_name": "SQL",
      "category_code": "SQL",
      "evidence": "SQL skills",
      "confidence": "high"
    },
    {
      "skill_name": "Machine Learning",
      "category_code": "AI",
      "evidence": "build machine learning models",
      "confidence": "high"
    }
  ],
  "jd_id": "304cd76a-90ed-4dda-924c-3c64f5bb62a6"
}
```

Errors: `404 JD_NOT_FOUND`, `422 VALIDATION_ERROR` (id is not a UUID), `503 STORAGE_ERROR`.

```json
{
  "error": {
    "code": "JD_NOT_FOUND",
    "message": "No saved JD analysis with this id.",
    "details": null
  }
}
```

---

## 6. GET /api/v1/jds/{jd_id}/skills

Return only the skills. Intended for Skill Matching (Role 5).

```json
{
  "jd_id": "304cd76a-90ed-4dda-924c-3c64f5bb62a6",
  "skills": [
    {
      "skill_name": "Python",
      "category_code": "COD",
      "evidence": "strong Python programming",
      "confidence": "high"
    },
    {
      "skill_name": "SQL",
      "category_code": "SQL",
      "evidence": "SQL skills",
      "confidence": "high"
    },
    {
      "skill_name": "Machine Learning",
      "category_code": "AI",
      "evidence": "build machine learning models",
      "confidence": "high"
    }
  ]
}
```

Errors: same as section 5.

---

## 7. PATCH /api/v1/jds/{jd_id}/skills

Correct the extracted skills. Send the **complete** new list; it **replaces** the stored list (the old list is not kept).
Every skill is validated against the shared schema. Skill names must be non-empty and unique (case-insensitive).
Searchable text chunks are not affected.

Request:
```json
{
  "skills": [
    {
      "skill_name": "Python",
      "category_code": "COD",
      "evidence": "strong Python programming",
      "confidence": "high"
    },
    {
      "skill_name": "System Design",
      "category_code": "SYSD",
      "evidence": "Added by reviewer",
      "confidence": "medium"
    }
  ]
}
```

Response 200:
```json
{
  "jd_id": "304cd76a-90ed-4dda-924c-3c64f5bb62a6",
  "skills": [
    {
      "skill_name": "Python",
      "category_code": "COD",
      "evidence": "strong Python programming",
      "confidence": "high"
    },
    {
      "skill_name": "System Design",
      "category_code": "SYSD",
      "evidence": "Added by reviewer",
      "confidence": "medium"
    }
  ]
}
```

Errors: `404 JD_NOT_FOUND`; `422 VALIDATION_ERROR` for an invalid `category_code`/`confidence`, duplicate names,
a missing `skills` field, or more than 200 skills; `503 STORAGE_ERROR`.

---

## 8. DELETE /api/v1/jds/{jd_id}  (destructive)

Permanently deletes the saved analysis and all its indexed chunks, embeddings and metadata. Cannot be undone.
No original file exists, so none is deleted. Afterwards `GET` on this id returns 404.

```json
{
  "jd_id": "304cd76a-90ed-4dda-924c-3c64f5bb62a6",
  "analysis_deleted": true,
  "chunks_deleted": 1,
  "note": "Deleted the saved analysis and all indexed text chunks, embeddings and metadata for this JD. No original upload was ever stored, so there is no file to delete."
}
```

Errors: `404 JD_NOT_FOUND`, `422`, `503`.

---

## 9. POST /api/v1/jds/search

Semantic search: finds indexed JD text whose meaning is close to the query, even with different wording.

Request body:

| Field | Type | Rules |
|---|---|---|
| `query` | string | 1-1000 characters, not blank |
| `top_k` | integer | 1-20, default 5 |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jds/search -H "Content-Type: application/json" \
  -d '{"query": "experience building predictive models", "top_k": 2}'
```

Response 200 (example values come from the test embedder; real MiniLM distances differ):

```json
{
  "query": "experience building predictive models",
  "top_k": 2,
  "distance_metric": "cosine",
  "count": 1,
  "results": [
    {
      "chunk_text": "Acme Analytics is hiring a Data Scientist. Key Responsibilities: build machine learning\nmodels for forecasting and predictive analytics. We are looking for strong Python\nprogramming and SQL skills. Good communication with stakeholders is expected.",
      "jd_id": "304cd76a-90ed-4dda-924c-3c64f5bb62a6",
      "source_file": "data_scientist.pdf",
      "company": "Acme Analytics",
      "role": "Data Scientist",
      "chunk_index": 0,
      "distance": 0.8492442965507507
    }
  ]
}
```

- Results are ordered nearest first. `count` can be lower than `top_k`; an empty index returns `"results": []`.
- `distance` is the raw cosine distance: 0 means same direction, bigger means less similar. It is **not** a
  probability or percentage. Only compare distances within one query.
- The query is embedded locally with the same model used at indexing time; it is not stored or sent to Gemini.

Errors: `422 VALIDATION_ERROR` (bad `query`/`top_k`), `409 EMBEDDING_MODEL_MISMATCH` (index built with another model),
`503 EMBEDDING_UNAVAILABLE` (model cannot load) or `VECTOR_STORE_ERROR`.

---

## 10. DELETE /api/v1/jds/index?confirm=true  (destructive)

Deletes **every** chunk in the ChromaDB collection (development reset). Saved analyses and their `jd_id`s are kept;
the JDs just stop being searchable. Without `confirm=true` nothing is deleted:

```json
{
  "error": {
    "code": "CONFIRMATION_REQUIRED",
    "message": "Add ?confirm=true to confirm you want to clear the search index.",
    "details": null
  }
}
```

With `confirm=true`:

```json
{
  "chunks_deleted": 0,
  "note": "The ChromaDB search index was emptied. Saved analyses (and their jd_ids) are NOT deleted; they simply are no longer searchable."
}
```

(The count is 0 here only because the previous example already deleted the single indexed JD.)

---

## 11. Utility endpoints

`GET /api/v1/jds/categories`: all 13 codes, e.g. `{"code": "COD", "description": "Coding"}`. Full response:

```json
{
  "categories": [
    {
      "code": "COD",
      "description": "Coding"
    },
    {
      "code": "DSA",
      "description": "Data Structures & Algorithms"
    },
    {
      "code": "OOD",
      "description": "Object-Oriented Design"
    },
    {
      "code": "APTI",
      "description": "Aptitude"
    },
    {
      "code": "COMM",
      "description": "Communication"
    },
    {
      "code": "AI",
      "description": "Artificial Intelligence"
    },
    {
      "code": "CLOUD",
      "description": "Cloud Computing"
    },
    {
      "code": "SQL",
      "description": "SQL"
    },
    {
      "code": "SWE",
      "description": "Software Engineering"
    },
    {
      "code": "SYSD",
      "description": "System Design"
    },
    {
      "code": "NETW",
      "description": "Networking"
    },
    {
      "code": "OS",
      "description": "Operating Systems"
    },
    {
      "code": "OTHER",
      "description": "Anything outside the other categories"
    }
  ]
}
```

`GET /api/v1/jds/provider-info` (never returns keys or paths):

```json
{
  "llm_provider": "gemini",
  "llm_model": "gemini-2.5-flash",
  "llm_api_key_configured": true,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "vector_database": "chromadb",
  "chroma_collection": "jd_chunks"
}
```

`GET /`:

```json
{
  "service": "RADIX JD Analytics API",
  "version": "1.0.0",
  "description": "Role 1: upload a job description (PDF/DOCX), extract skills with an LLM, and search indexed JD text semantically.",
  "docs_url": "/docs"
}
```

`GET /health` (does not call Gemini, open ChromaDB or load the embedding model):

```json
{
  "status": "ok"
}
```

---

## 12. Using it from Python (other roles)

```python
import requests

BASE = "http://127.0.0.1:8000/api/v1/jds"

# 1. Analyze once
with open("data_scientist.pdf", "rb") as f:
    r = requests.post(f"{BASE}/analyze", files={"file": f}, timeout=120)
r.raise_for_status()
jd = r.json()                 # ExtractedSkillList fields + jd_id
jd_id = jd["jd_id"]

# 2. Later (e.g. Skill Matching): fetch by id, no re-upload
skills = requests.get(f"{BASE}/{jd_id}/skills", timeout=30).json()["skills"]

# 3. Handle errors uniformly
resp = requests.get(f"{BASE}/00000000-0000-0000-0000-000000000000")
if resp.status_code != 200:
    print(resp.json()["error"]["code"])   # JD_NOT_FOUND
```

## 13. Status code summary

| Code | Meaning in this API |
|---|---|
| 200 | Success |
| 400 | Unusable document, or missing `confirm=true` |
| 404 | `jd_id` not found |
| 409 | Index was built with a different embedding model |
| 413 | Upload / extracted text / page count over its limit |
| 415 | Unsupported file type |
| 422 | Invalid request (fields, UUID, `top_k`, skills) |
| 429 | Gemini rate limit |
| 500 | Unexpected error (no internal details exposed) |
| 502 | Unusable LLM output |
| 503 | LLM/embedding/vector DB/saved-analysis DB unavailable or not configured |
| 504 | Gemini timeout |
