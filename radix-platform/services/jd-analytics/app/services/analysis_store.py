"""Saved JD analyses (SQLite). This is what makes a `jd_id` reusable by other roles.

Stores only the structured result (company, role, skills). It does NOT store the JD text
(that lives only as chunks in ChromaDB) and never the original file.
"""
import json
import sqlite3
import threading
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.errors import AppError
from app.schemas import ExtractedSkillList, Skill

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jd_analyses (
    jd_id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    company TEXT,
    role TEXT,
    skills_json TEXT NOT NULL,
    indexing_status TEXT NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _guard():
    try:
        yield
    except AppError:
        raise
    except sqlite3.Error:
        raise AppError(503, "STORAGE_ERROR", "The saved-analysis database is unavailable or failed.") from None


def _row_to_dict(r: sqlite3.Row) -> dict:
    return {
        "jd_id": r["jd_id"], "source_file": r["source_file"], "company": r["company"], "role": r["role"],
        "skills": [Skill.model_validate(x) for x in json.loads(r["skills_json"])],
        "indexing_status": r["indexing_status"], "chunk_count": r["chunk_count"],
        "created_at": r["created_at"], "updated_at": r["updated_at"],
    }


class AnalysisStore:
    def __init__(self, db_path):
        self._path = Path(db_path)
        self._lock = threading.Lock()
        with _guard():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._conn() as c:
                c.execute(_SCHEMA)

    @contextmanager
    def _conn(self):
        with closing(sqlite3.connect(str(self._path), timeout=10)) as c:
            c.row_factory = sqlite3.Row
            with c:  # commit on success, roll back on error
                yield c

    def save(self, jd_id: str, result: ExtractedSkillList, indexing_status: str, chunk_count: int) -> None:
        now = _now()
        with self._lock, _guard(), self._conn() as c:
            c.execute(
                "INSERT INTO jd_analyses VALUES (?,?,?,?,?,?,?,?,?)",
                (jd_id, result.source_file, result.company, result.role,
                 json.dumps([s.model_dump() for s in result.skills]), indexing_status, chunk_count, now, now),
            )

    def get(self, jd_id: str) -> dict | None:
        with _guard(), self._conn() as c:
            r = c.execute("SELECT * FROM jd_analyses WHERE jd_id=?", (jd_id,)).fetchone()
        return _row_to_dict(r) if r else None

    def list_all(self) -> list[dict]:
        with _guard(), self._conn() as c:
            rows = c.execute("SELECT * FROM jd_analyses ORDER BY created_at DESC, rowid DESC").fetchall()
        return [_row_to_dict(r) for r in rows]

    def replace_skills(self, jd_id: str, skills: list[Skill]) -> bool:
        with self._lock, _guard(), self._conn() as c:
            cur = c.execute(
                "UPDATE jd_analyses SET skills_json=?, updated_at=? WHERE jd_id=?",
                (json.dumps([s.model_dump() for s in skills]), _now(), jd_id),
            )
            return cur.rowcount > 0

    def delete(self, jd_id: str) -> bool:
        with self._lock, _guard(), self._conn() as c:
            return c.execute("DELETE FROM jd_analyses WHERE jd_id=?", (jd_id,)).rowcount > 0

    def count(self) -> int:
        with _guard(), self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM jd_analyses").fetchone()[0]
