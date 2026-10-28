"""LLM provider integration (isolated).

The rest of the app only knows the small `LLMClient` interface and the `LLM*Error` classes.
To add another provider, write a class with `generate_json(...)` that raises these same
errors, and register it in `build_llm_client`.
"""
import logging
from typing import Protocol

import httpx
from pydantic import BaseModel

from app.config import Settings

logger = logging.getLogger("radix.llm")


class LLMError(Exception):
    """Base class. Messages are safe to show; they never contain keys or stack traces."""


class LLMNotConfiguredError(LLMError): ...
class LLMAuthError(LLMError): ...
class LLMRateLimitError(LLMError): ...   # transient
class LLMTimeoutError(LLMError): ...     # transient
class LLMUnavailableError(LLMError): ... # transient
class LLMBadResponseError(LLMError): ...

TRANSIENT_ERRORS = (LLMRateLimitError, LLMTimeoutError, LLMUnavailableError)


class LLMClient(Protocol):
    provider_name: str
    model_name: str

    def generate_json(self, system_prompt: str, user_prompt: str, response_model: type[BaseModel]) -> str:
        """Return the model's reply as a JSON string matching `response_model`."""
        ...


class GeminiClient:
    provider_name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: float):
        from google import genai
        from google.genai import types

        self.model_name = model
        self._types = types
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )

    def generate_json(self, system_prompt: str, user_prompt: str, response_model: type[BaseModel]) -> str:
        from google.genai import errors as genai_errors

        config = self._types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_model,  # provider-side structured output
            temperature=0.0,
        )
        try:
            response = self._client.models.generate_content(
                model=self.model_name, contents=user_prompt, config=config
            )
        except genai_errors.APIError as exc:
            raise self._map_api_error(exc) from None
        except (httpx.TimeoutException, TimeoutError):
            raise LLMTimeoutError("The LLM provider timed out.") from None
        except httpx.HTTPError:
            raise LLMUnavailableError("Could not reach the LLM provider.") from None
        except Exception as exc:  # unknown SDK failure: log the type only, not the message
            logger.error("Unexpected LLM client failure: %s", type(exc).__name__)
            raise LLMUnavailableError("The LLM provider call failed unexpectedly.") from None

        text = getattr(response, "text", None)
        if not text:
            raise LLMBadResponseError("The LLM returned an empty or blocked response.")
        return text

    @staticmethod
    def _map_api_error(exc) -> LLMError:
        code = getattr(exc, "code", None)
        message = str(getattr(exc, "message", "") or "").lower()
        if code in (401, 403) or (code == 400 and "api key" in message):
            return LLMAuthError("The LLM provider rejected the API key.")
        if code == 429:
            return LLMRateLimitError("The LLM provider rate limit was hit.")
        if code in (408, 504):
            return LLMTimeoutError("The LLM provider timed out.")
        if isinstance(code, int) and code >= 500:
            return LLMUnavailableError("The LLM provider is temporarily unavailable.")
        return LLMBadResponseError("The LLM provider rejected the request.")


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "gemini":
        key = settings.gemini_api_key.get_secret_value()
        if not key:
            raise LLMNotConfiguredError("GEMINI_API_KEY is not set. Add it to your .env file.")
        return GeminiClient(key, settings.gemini_model, settings.llm_timeout_seconds)
    raise LLMNotConfiguredError(f"Unsupported LLM provider: {settings.llm_provider}")
