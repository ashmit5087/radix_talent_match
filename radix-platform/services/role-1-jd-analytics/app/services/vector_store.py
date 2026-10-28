"""ChromaDB persistence and semantic search for JD text chunks.

What is stored (per chunk): the chunk text, its embedding vector, and metadata
(document_id, source_file, company, role, chunk_index, ...). Original PDF/DOCX files are NOT stored.
"""
import logging
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.errors import AppError
from app.services.embedding_service import Embedder

logger = logging.getLogger("radix.vectorstore")


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks of about `size` characters, breaking at whitespace."""
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(" ", start + size // 2, end)  # prefer a word boundary
            nl = text.rfind("\n", start + size // 2, end)
            cut = max(cut, nl)
            if cut > start:
                end = cut
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


@contextmanager
def _guard():
    """Turn unexpected ChromaDB failures into a clean 503 (AppErrors pass through untouched)."""
    try:
        yield
    except AppError:
        raise
    except Exception as exc:
        logger.error("ChromaDB error: %s", type(exc).__name__)
        raise AppError(503, "VECTOR_STORE_ERROR", "The vector database is unavailable or failed.") from None


class VectorStore:
    def __init__(self, persist_dir, collection_name: str, embedder: Embedder,
                 chunk_size: int = 1000, chunk_overlap: int = 200):
        self._name = collection_name
        self._embedder = embedder
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._lock = threading.RLock()
        with _guard():
            # PersistentClient creates the directory if needed and keeps data across restarts.
            self._client = chromadb.PersistentClient(
                path=str(persist_dir), settings=ChromaSettings(anonymized_telemetry=False)
            )
            self._collection = self._open_collection()

    # -- collection -----------------------------------------------------------------------
    def _open_collection(self):
        meta = {"hnsw:space": "cosine", "embedding_model": self._embedder.model_name}
        try:
            col = self._client.get_collection(self._name)
        except Exception:
            return self._client.create_collection(self._name, metadata=meta)
        existing = (col.metadata or {}).get("embedding_model")
        if existing and existing != self._embedder.model_name:
            raise AppError(
                409, "EMBEDDING_MODEL_MISMATCH",
                f"Collection '{self._name}' was built with embedding model '{existing}' but the app is "
                f"configured for '{self._embedder.model_name}'. Clear the index or change CHROMA_COLLECTION_NAME.",
            )
        return col

    # -- write ----------------------------------------------------------------------------
    def index_document(self, *, jd_id: str, source_file: str, text: str,
                       company: str | None, role: str | None) -> int:
        """Chunk -> embed -> store under `jd_id`. Returns the chunk count. All-or-nothing."""
        chunks = chunk_text(text, self._chunk_size, self._chunk_overlap)
        if not chunks:
            raise AppError(400, "NO_TEXT_FOUND", "Nothing to index.")
        vectors = self._embedder.embed(chunks)  # may raise EMBEDDING_UNAVAILABLE
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        base = {"jd_id": jd_id, "source_file": source_file, "company": company or "",
                "role": role or "", "chunk_count": len(chunks), "indexed_at": now}
        with self._lock, _guard():
            try:
                self._collection.add(
                    ids=[f"{jd_id}:{i}" for i in range(len(chunks))],
                    documents=chunks,
                    embeddings=vectors,
                    metadatas=[{**base, "chunk_index": i} for i in range(len(chunks))],
                )
            except Exception:
                self._collection.delete(where={"jd_id": jd_id})  # no half-indexed documents
                raise
        return len(chunks)

    def delete_chunks(self, jd_id: str) -> int:
        """Remove every chunk of one JD. Returns how many were removed (0 if none)."""
        with self._lock, _guard():
            ids = self._collection.get(where={"jd_id": jd_id}, include=[])["ids"]
            if ids:
                self._collection.delete(ids=ids)
            return len(ids)

    def clear(self) -> int:
        with self._lock, _guard():
            n = self._collection.count()
            self._client.delete_collection(self._name)
            self._collection = self._open_collection()
            return n

    # -- read -----------------------------------------------------------------------------
    def count(self) -> int:
        with _guard():
            return self._collection.count()

    def search(self, query: str, top_k: int) -> list[dict]:
        with _guard():
            total = self._collection.count()
        if total == 0:
            return []
        qvec = self._embedder.embed([query])[0]
        with self._lock, _guard():
            res = self._collection.query(
                query_embeddings=[qvec], n_results=min(top_k, total),
                include=["documents", "metadatas", "distances"],
            )
        hits = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            hits.append({
                "chunk_text": doc,
                "jd_id": meta["jd_id"],
                "source_file": meta["source_file"],
                "company": meta.get("company") or None,
                "role": meta.get("role") or None,
                "chunk_index": int(meta["chunk_index"]),
                "distance": float(dist),
            })
        return hits
