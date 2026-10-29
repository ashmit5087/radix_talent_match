"""
Role 2 — FastAPI HTTP adapter for resume parsing.

This is a thin wrapper over the existing CLI-based extract_resume() function.
It does NOT duplicate the parsing logic; it merely adds an HTTP boundary
so the frontend can upload resumes via the browser.

Run with:
    uvicorn api_server:app --reload --port 8002
"""

import logging
import os
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Ensure the service's own directory is on sys.path so that
# the original role-2 modules (extract, read_file, schema) are importable.
_SERVICE_DIR = Path(__file__).resolve().parent
if str(_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVICE_DIR))

from extract import extract_resume  # noqa: E402
from schema import ResumeExtract  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("radix.role2")
logger.setLevel(logging.INFO)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}

app = FastAPI(
    title="RADIX Resume Parsing API",
    description=(
        "Role 2: Upload a resume (PDF/DOCX) and receive structured skill extraction "
        "using the existing Groq-powered parser. This adapter wraps the CLI pipeline "
        "as an HTTP service."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/", tags=["System"])
def root():
    return {
        "service": "RADIX Resume Parsing API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
def health():
    """Basic liveness check. Does not call Groq or load models."""
    groq_configured = bool(os.getenv("GROQ_API_KEY", "").strip())
    return {
        "status": "ok",
        "service": "RADIX Resume Parsing",
        "groq_api_key_configured": groq_configured,
    }


@app.post(
    "/api/v1/resumes/parse",
    response_model=ResumeExtract,
    tags=["Resume Parsing"],
    summary="Parse a resume (PDF or DOCX)",
    description=(
        "Upload a resume file. The service extracts text, sends it to the Groq LLM "
        "for structured skill extraction, and returns the result as JSON conforming "
        "to the shared RADIX ResumeExtract schema.\n\n"
        "**Requirements**: GROQ_API_KEY must be set. Supported formats: PDF, DOCX. Max size: 10 MB."
    ),
    responses={
        400: {"description": "Invalid file type, empty file, or unreadable content"},
        413: {"description": "File exceeds the 10 MB limit"},
        422: {"description": "File could not be parsed (e.g. scanned image PDF)"},
        503: {"description": "Groq API unavailable or credentials missing"},
    },
)
async def parse_resume(
    file: UploadFile = File(..., description="Resume file (.pdf or .docx)"),
):
    # --- Validate filename and extension ---
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only PDF and DOCX files are accepted.",
        )

    # --- Validate Groq credentials ---
    if not os.getenv("GROQ_API_KEY", "").strip():
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Resume parsing requires a Groq API key.",
        )

    # --- Read and validate size ---
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
        )

    # --- Write to a secure temp file and invoke the existing parser ---
    tmp_path = None
    try:
        suffix = ext  # .pdf or .docx
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        logger.info("Parsing resume: %s (%d bytes)", file.filename, len(content))
        result: ResumeExtract = extract_resume(tmp_path)

        # Override source_file with the original upload name, not the temp path
        result.source_file = file.filename

        return result

    except ValueError as exc:
        # Raised by read_file.py for unsupported formats or empty/scanned PDFs
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        logger.error("LLM parsing failure: %s", exc)
        err_msg = str(exc)
        if "413" in err_msg or "rate_limit" in err_msg or "too large" in err_msg:
            friendly = "The uploaded file is too large or contains too much non-resume text for the model limit. Please upload a standard 1-2 page resume."
        else:
            friendly = "Could not extract skills from this document. Please ensure it is a valid resume."
        raise HTTPException(
            status_code=422,
            detail=friendly,
        )
    except Exception as exc:
        logger.error("Unexpected error parsing resume: %s", type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while parsing the resume.",
        )
    finally:
        # Guarantee cleanup of the temp file
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=8002, reload=True)
