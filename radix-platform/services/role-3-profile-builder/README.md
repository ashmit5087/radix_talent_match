# RADIX Talent Match — Role 3: Profile Builder (Backend)

The **Profile Builder** module serves as the central candidate profile repository in the RADIX Talent Match platform. It is responsible for prefilling candidate profiles from resume parsing data (Role 2), supporting manual profile authoring/editing, calculating completeness metrics, managing CV file uploads, persisting data to Supabase, and exposing canonical skillset schemas for **Role 4: Talent Check** and **Role 5: Skill Matching**.

---

## 🏛️ Architecture Overview

The backend is built with **FastAPI**, **Pydantic v2**, and **Supabase (PostgreSQL)** following clean architecture principles:

```
backend/
├── app/
│   ├── config.py              # Environment configuration via Pydantic BaseSettings
│   ├── database.py            # Supabase client lifecycle & fallback management
│   ├── schemas/               # Canonical Pydantic v2 validation contracts
│   │   ├── skill.py           # Shared 12-category skillset schema & confidence normalization
│   │   ├── profile.py         # Full candidate profile, CV upload models & completeness
│   │   └── resume.py          # Parsed resume ingestion models (Role 2 contract)
│   ├── adapters/              # Replaceable adapter layer for external resume input
│   │   └── resume_adapter.py  # MockResumeAdapter mapping mock resumes to profile models
│   ├── repositories/          # Persistence layer
│   │   └── profile_repository.py # Unified repository (Supabase + in-memory store)
│   ├── services/              # Pure business logic
│   │   └── profile_service.py # UUID assignment, immutability, CV uploads, completeness
│   └── routers/               # HTTP REST endpoints
│       └── profiles.py        # /api/v1/profiles endpoints
├── mock_data/
│   └── mock_parsed_resume.json # Realistic sample resumes (Rohan Verma, Ananya Rao)
├── uploads/cvs/               # Uploaded CV storage directory
├── tests/                     # Automated pytest suite (29 unit & integration tests)
├── main.py                    # Application entrypoint & CORS middleware
├── requirements.txt           # Python package dependencies
├── .env.example               # Environment template (no secrets committed)
├── pytest.ini                 # Pytest configuration with third-party warning filters
└── README.md                  # This documentation
```

---

## 🔑 Key Engineering Invariants & Guarantees

1. **Independent Local Operation**: Works 100% out-of-the-box in local development and CI. If Supabase credentials are not configured or unreachable, the repository automatically operates in local in-memory fallback.
2. **Database Failure Honesty**: If Supabase credentials ARE configured, any failed database operation explicitly raises `DatabasePersistenceError` and returns `HTTP 503 Service Unavailable`, preventing false-positive HTTP 200/201 success responses.
3. **Strict Profile ID Immutability**: The backend generates a stable UUID `profile_id` on creation and strictly preserves it during subsequent `PUT` updates.
4. **Agreed 12 RADIX Skill Categories**: Strictly validates against the 12 agreed categories:
   `COD`, `DSA`, `OOD`, `APTI`, `COMM`, `AI`, `CLOUD`, `SQL`, `SWE`, `SYSD`, `NETW`, `OS`, plus `OTHER` as explicit fallback.
5. **Canonical Confidence Alignment**: Strictly aligns with the RADIX brief requiring `"high" | "medium" | "low"`.
   - Numeric inputs are mapped deterministically at the boundary:
     - `confidence >= 0.80` $\rightarrow$ `"high"`
     - `confidence >= 0.50` $\rightarrow$ `"medium"`
     - `confidence < 0.50`  $\rightarrow$ `"low"`
   - Numeric certainty is preserved in `raw_confidence` for provenance tracking.
6. **Dedicated CV File Upload & Validation**: Dedicated `POST /api/v1/profiles/{profile_id}/cv` endpoint with extension whitelist (`.pdf`, `.docx`, `.doc`), 10MB size limit, path-traversal sanitization, and streaming retrieval via `GET /api/v1/profiles/{profile_id}/cv`.
7. **Profile Authoring Completeness vs. Readiness**: Profile completeness measures candidate authoring completeness across all 7 profile sections, **not** company readiness or job matching likelihood.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Pip

### 2. Setup Environment
```bash
cd backend

# Create virtual environment (optional)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the API Server
```bash
python main.py
# Or with uvicorn directly:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger documentation is available at: **http://localhost:8000/docs**

### 4. Run the Full Test Suite
```bash
python -m pytest tests -v -c pytest.ini
```

---

## 📡 API Specification & Consumed Contracts

### Base URL: `http://localhost:8000/api/v1`

### 1. Prefill Profile from Mock Resume (Role 2 Handoff)
- **Method**: `POST`
- **Route**: `/api/v1/profiles/from-resume/{resume_id}`
- **Sample IDs**: `mock-001` (Rohan Verma), `mock-002` (Ananya Rao)
- **Response** (`201 Created`): Returns full profile with `profile_id` and `source="extracted"`.

---

### 2. Create Candidate Profile Manually
- **Method**: `POST`
- **Route**: `/api/v1/profiles`
- **Response** (`201 Created`): Full profile object containing generated `profile_id`.

---

### 3. Retrieve Candidate Profile
- **Method**: `GET`
- **Route**: `/api/v1/profiles/{profile_id}`
- **Response** (`200 OK`): Full profile object.

---

### 4. Update Candidate Profile
- **Method**: `PUT`
- **Route**: `/api/v1/profiles/{profile_id}`
- **Behavior**: Preserves existing `profile_id` and `created_at`; updates `updated_at`.
- **Response** (`200 OK`): Updated full profile object.

---

### 5. Expose Skills for Role 4 (Talent Check) & Role 5 (Skill Matching)
- **Method**: `GET`
- **Route**: `/api/v1/profiles/{profile_id}/skills`
- **Response** (`200 OK`):
```json
{
  "profile_id": "7fcea683-500d-4f34-924b-6f3cd43580ee",
  "total_skills": 8,
  "categories_covered": ["COD", "DSA", "SYSD", "SQL", "CLOUD", "OOD", "OS", "SWE"],
  "skills": [
    {
      "skill_name": "Python",
      "category_code": "COD",
      "evidence": "Developed async backend microservices with FastAPI",
      "confidence": "high",
      "raw_confidence": 0.95,
      "source": "extracted"
    }
  ]
}
```

---

### 6. Profile Completeness Metrics
- **Method**: `GET`
- **Route**: `/api/v1/profiles/{profile_id}/completeness`
- **Response** (`200 OK`):
```json
{
  "profile_id": "7fcea683-500d-4f34-924b-6f3cd43580ee",
  "overall_percentage": 96,
  "section_scores": {
    "personal_info": 20,
    "education": 15,
    "skills": 25,
    "projects": 15,
    "experience": 10,
    "certifications": 10,
    "preferred_roles": 5
  },
  "completed_sections": [
    "personal_info",
    "education",
    "skills",
    "projects",
    "experience",
    "certifications",
    "preferred_roles"
  ],
  "incomplete_sections": [],
  "missing_recommendations": []
}
```

---

### 7. CV File Upload
- **Method**: `POST`
- **Route**: `/api/v1/profiles/{profile_id}/cv`
- **Content-Type**: `multipart/form-data`
- **File constraints**: `.pdf`, `.docx`, `.doc` $\le$ 10MB
- **Response** (`200 OK`):
```json
{
  "profile_id": "7fcea683-500d-4f34-924b-6f3cd43580ee",
  "cv_file": "Rohan_Verma_CV.pdf",
  "stored_filename": "7fcea683-500d-4f34-924b-6f3cd43580ee_Rohan_Verma_CV.pdf",
  "size_bytes": 46,
  "content_type": "application/pdf",
  "uploaded_at": "2026-10-25T17:35:34Z",
  "message": "CV uploaded and attached to profile successfully."
}
```

---

### 8. CV File Download
- **Method**: `GET`
- **Route**: `/api/v1/profiles/{profile_id}/cv`
- **Response** (`200 OK`): Binary stream of the attached CV document.
