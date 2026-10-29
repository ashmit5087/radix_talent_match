"""FastAPI integration boundary for Role 5. No UI logic lives here.

Error behavior (documented in the README):
  400  invalid JSON body or contract violation (missing/ill-typed fields)
  422  well-formed request but the JD has no skills to match
  500  unexpected failure (generic message; no stack trace or secrets)
"""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import ALGORITHM_VERSION, SERVICE_NAME
from .schemas import ImprovementPlan, MatchResponse, PreviewResponse
from .service import InvalidInputError, NoJobSkillsError, match_raw, improvement_plan_raw, match_with_talent_check_raw, preview_raw

logger = logging.getLogger("skill_matching")

app = FastAPI(
    title="RADIX Talent Match - Role 5: Skill Matching",
    version=ALGORITHM_VERSION,
    description="Compares a candidate's skills with one extracted JD skill list.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "detail": message})


async def _read_body(request: Request) -> tuple[dict, dict]:
    try:
        body = json.loads((await request.body()) or b"")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise InvalidInputError("request body is not valid JSON")
    if not isinstance(body, dict):
        raise InvalidInputError("request body must be a JSON object")
    for key in ("candidate", "job_description"):
        if not isinstance(body.get(key), dict):
            raise InvalidInputError(f"'{key}' is required and must be a JSON object")
    return body["candidate"], body["job_description"]


@app.exception_handler(Exception)
async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
    # Log the type only: never log candidate data, emails or stack traces to clients.
    logger.error("unexpected failure: %s", type(exc).__name__)
    return _error(500, "internal_error", "Unexpected error while matching skills.")


@app.get("/")
def root() -> dict:
    return {
        "service": SERVICE_NAME,
        "version": ALGORITHM_VERSION,
        "endpoints": {
            "health": "GET /health",
            "match": "POST /api/v1/matches",
            "preview": "POST /api/v1/matches/preview",
            "match_with_talent_check": "POST /api/v1/matches/with-talent-check",
            "improvement_plan": "POST /api/v1/improvement-plan",
            "docs": "GET /docs",
        },
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": SERVICE_NAME, "version": ALGORITHM_VERSION}


@app.post("/api/v1/matches", response_model=MatchResponse)
async def create_match(request: Request):
    try:
        candidate, jd = await _read_body(request)
        return match_raw(candidate, jd)
    except NoJobSkillsError as exc:
        return _error(422, "no_job_skills", str(exc))
    except InvalidInputError as exc:
        return _error(400, "invalid_contract", str(exc))


@app.post("/api/v1/matches/preview", response_model=PreviewResponse)
async def preview_match(request: Request):
    try:
        candidate, jd = await _read_body(request)
        return preview_raw(candidate, jd)
    except NoJobSkillsError as exc:
        return _error(422, "no_job_skills", str(exc))
    except InvalidInputError as exc:
        return _error(400, "invalid_contract", str(exc))


@app.post("/api/v1/matches/with-talent-check", response_model=MatchResponse)
async def create_match_with_talent_check(request: Request):
    """Same as /api/v1/matches plus a Role 4 `talent_check` object in the body."""
    try:
        candidate, jd = await _read_body(request)
        tc = json.loads(await request.body()).get("talent_check")
        if not isinstance(tc, dict):
            raise InvalidInputError("'talent_check' is required and must be a JSON object")
        return match_with_talent_check_raw(candidate, jd, tc)
    except NoJobSkillsError as exc:
        return _error(422, "no_job_skills", str(exc))
    except InvalidInputError as exc:
        return _error(400, "invalid_contract", str(exc))


@app.post("/api/v1/improvement-plan", response_model=ImprovementPlan)
async def create_improvement_plan(request: Request):
    """Ranked what-if gap-closing plan. Body: candidate, job_description, optional
    talent_check, optional use_llm (default false; falls back to the offline plan)."""
    try:
        candidate, jd = await _read_body(request)
        body = json.loads(await request.body())
        tc = body.get("talent_check")
        if tc is not None and not isinstance(tc, dict):
            raise InvalidInputError("'talent_check' must be a JSON object when provided")
        use_llm = body.get("use_llm", False) is True
        _, plan = await run_in_threadpool(improvement_plan_raw, candidate, jd, tc, use_llm)
        return plan
    except NoJobSkillsError as exc:
        return _error(422, "no_job_skills", str(exc))
    except InvalidInputError as exc:
        return _error(400, "invalid_contract", str(exc))
