"""Local, open-source text embeddings (Sentence Transformers).

The model is loaded lazily on the first embed() call, so starting the server and calling
/health never loads it. There is no fallback: if the model cannot load we raise a clear
error instead of producing fake vectors.
"""
import logging
import threading
from typing import Protocol

from app.errors import AppError

logger = logging.getLogger("radix.embeddings")


class Embedder(Protocol):
    model_name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise AppError(
                    503, "EMBEDDING_UNAVAILABLE",
                    "sentence-transformers is not installed. Run: pip install sentence-transformers",
                ) from None
            try:
                logger.info("Loading embedding model %s (first run downloads it)", self.model_name)
                self._model = SentenceTransformer(self.model_name)
            except Exception:
                raise AppError(
                    503, "EMBEDDING_UNAVAILABLE",
                    f"Could not load embedding model '{self.model_name}'. On first use it must be "
                    "downloaded from Hugging Face (needs internet); afterwards it runs from the local cache.",
                ) from None
            return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        try:
            vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        except Exception:
            raise AppError(503, "EMBEDDING_UNAVAILABLE", "Embedding generation failed.") from None
        return [v.tolist() for v in vectors]
