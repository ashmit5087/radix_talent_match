"""One consistent error format for the whole API.

Every error response looks like:
    {"error": {"code": "SOME_CODE", "message": "...", "details": null}}
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas import ErrorResponse

logger = logging.getLogger("radix.errors")


class AppError(Exception):
    """An error we raise on purpose; it maps directly onto an HTTP response."""

    def __init__(self, status_code: int, code: str, message: str, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def _body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


# Examples shown in Swagger UI for each status code.
_EXAMPLES = {
    400: ("INVALID_DOCUMENT", "The file is empty, corrupt, encrypted, or contains no extractable text.",
          "Invalid or unusable document / request."),
    404: ("JD_NOT_FOUND", "No saved JD analysis with this id.", "Saved JD analysis not found."),
    409: ("EMBEDDING_MODEL_MISMATCH", "The index was built with a different embedding model.",
          "Index/embedding model conflict."),
    413: ("FILE_TOO_LARGE", "Upload exceeds the 10 MB limit.", "Upload or extracted text exceeds its limit."),
    415: ("UNSUPPORTED_FILE_TYPE", "Upload a PDF or DOCX file.", "Unsupported file type."),
    422: ("VALIDATION_ERROR", "Request validation failed.", "Invalid request parameters or body."),
    429: ("LLM_RATE_LIMITED", "The LLM provider rate limit was hit. Try again shortly.",
          "Upstream LLM rate limit."),
    500: ("INTERNAL_ERROR", "An unexpected error occurred.", "Unexpected internal error."),
    502: ("LLM_BAD_RESPONSE", "The LLM returned an unusable response.", "Invalid LLM response."),
    503: ("LLM_UNAVAILABLE", "The LLM provider or a required service is temporarily unavailable.",
          "Provider or required service unavailable."),
    504: ("LLM_TIMEOUT", "The LLM provider timed out.", "Upstream timeout."),
}


def error_responses(*statuses: int, override: dict | None = None) -> dict:
    """Build the `responses=` dict for a route so Swagger shows these error shapes.

    `override` maps status -> (code, message, description) to replace the generic example.
    """
    out = {}
    for s in statuses:
        code, message, description = (override or {}).get(s) or _EXAMPLES[s]
        out[s] = {
            "model": ErrorResponse,
            "description": description,
            "content": {"application/json": {"example": _body(code, message)}},
        }
    return out


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        # Keep only where/what went wrong; never echo the submitted values back.
        details = [
            {"location": ".".join(str(p) for p in e.get("loc", [])), "message": e.get("msg"), "type": e.get("type")}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422, content=_body("VALIDATION_ERROR", "Request validation failed.", details)
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)))

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        # Full traceback goes to the server log only, never to the client.
        logger.error("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500, content=_body("INTERNAL_ERROR", "An unexpected error occurred.")
        )
