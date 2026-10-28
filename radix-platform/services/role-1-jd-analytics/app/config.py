"""Application settings, read from environment variables / a local .env file."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_provider: Literal["gemini"] = "gemini"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-2.5-flash"
    llm_timeout_seconds: float = Field(60, gt=0, le=600)
    llm_max_retries: int = Field(2, ge=0, le=5)
    llm_retry_backoff_seconds: float = Field(1.0, ge=0, le=30)
    llm_fallback_enabled: bool = False

    # Upload / extraction limits
    max_upload_size_mb: float = Field(10, gt=0, le=100)
    max_extracted_text_chars: int = Field(60_000, ge=1_000, le=1_000_000)
    max_pdf_pages: int = Field(200, ge=1, le=2000)

    # ChromaDB
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = Field("jd_chunks", min_length=3, max_length=63)

    # Saved JD analyses: local SQLite file (default) or Supabase (shared database)
    storage_backend: Literal["sqlite", "supabase"] = "sqlite"
    jd_database_path: str = "./data/jd_analyses.sqlite3"
    supabase_url: str = ""
    supabase_service_role_key: SecretStr = SecretStr("")

    # Browser access (React dev servers). Comma-separated list of exact origins.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Embeddings / chunking
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size_chars: int = Field(1000, ge=200, le=5000)
    chunk_overlap_chars: int = Field(200, ge=0, le=1000)

    @model_validator(mode="after")
    def _check_chunking(self) -> "Settings":
        if self.storage_backend == "supabase" and not (
            self.supabase_url and self.supabase_service_role_key.get_secret_value()
        ):
            raise ValueError("STORAGE_BACKEND=supabase requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than CHUNK_SIZE_CHARS")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_size_mb * 1024 * 1024)

    @staticmethod
    def _resolve(value: str) -> Path:
        """Relative paths are resolved against the project root, not the current directory."""
        p = Path(value)
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()

    @property
    def chroma_path(self) -> Path:
        return self._resolve(self.chroma_persist_directory)

    @property
    def jd_db_path(self) -> Path:
        return self._resolve(self.jd_database_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
