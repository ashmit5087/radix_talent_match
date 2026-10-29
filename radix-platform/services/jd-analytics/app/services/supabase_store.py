"""Saved JD analyses in Supabase (Postgres) via its REST API (PostgREST).

Same interface as AnalysisStore (SQLite), so the routes do not care which one is used.
Tables/functions are created by supabase/migrations/001_role1_jd_tables.sql.
The service-role key is used from the backend only and never returned or logged.
"""
import logging

import httpx

from app.errors import AppError
from app.schemas import ExtractedSkillList, Skill

logger = logging.getLogger("radix.supabase")


def _storage_error() -> AppError:
    return AppError(503, "STORAGE_ERROR", "The saved-analysis database is unavailable or failed.")


def _to_dict(r: dict) -> dict:
    skills = sorted(r.get("jd_skills") or [], key=lambda s: s.get("position", 0))
    return {
        "jd_id": r["id"], "source_file": r["source_file"], "company": r["company"], "role": r["role"],
        "skills": [Skill(skill_name=s["skill_name"], category_code=s["category_code"],
                         evidence=s["evidence"], confidence=s["confidence"]) for s in skills],
        "indexing_status": r["indexing_status"], "chunk_count": r["chunk_count"],
        "created_at": r["created_at"], "updated_at": r["updated_at"],
    }


def _skills_payload(skills: list[Skill]) -> list[dict]:
    return [s.model_dump() for s in skills]


class SupabaseAnalysisStore:
    def __init__(self, url: str, service_role_key: str, timeout: float = 15.0, transport=None):
        self._client = httpx.Client(
            base_url=url.rstrip("/") + "/rest/v1",
            headers={"apikey": service_role_key, "Authorization": f"Bearer {service_role_key}",
                     "Content-Type": "application/json"},
            timeout=timeout, transport=transport,
        )

    def _call(self, method: str, path: str, **kw) -> httpx.Response:
        try:
            r = self._client.request(method, path, **kw)
        except httpx.HTTPError as exc:
            logger.error("Supabase request failed: %s", type(exc).__name__)
            raise _storage_error() from None
        if r.status_code >= 400:
            logger.error("Supabase returned HTTP %s for %s %s", r.status_code, method, path)
            raise _storage_error()
        return r

    def save(self, jd_id: str, result: ExtractedSkillList, indexing_status: str, chunk_count: int) -> None:
        self._call("POST", "/rpc/save_jd_analysis", json={
            "p_id": jd_id, "p_source_file": result.source_file, "p_company": result.company,
            "p_role": result.role, "p_status": indexing_status, "p_chunks": chunk_count,
            "p_skills": _skills_payload(result.skills),
        })

    def get(self, jd_id: str) -> dict | None:
        rows = self._call("GET", "/jd_analyses", params={"id": f"eq.{jd_id}", "select": "*,jd_skills(*)"}).json()
        return _to_dict(rows[0]) if rows else None

    def list_all(self) -> list[dict]:
        rows = self._call("GET", "/jd_analyses", params={"select": "*,jd_skills(*)", "order": "created_at.desc"}).json()
        return [_to_dict(r) for r in rows]

    def replace_skills(self, jd_id: str, skills: list[Skill]) -> bool:
        return bool(self._call("POST", "/rpc/replace_jd_skills",
                               json={"p_jd_id": jd_id, "p_skills": _skills_payload(skills)}).json())

    def delete(self, jd_id: str) -> bool:
        rows = self._call("DELETE", "/jd_analyses", params={"id": f"eq.{jd_id}"},
                          headers={"Prefer": "return=representation"}).json()
        return len(rows) > 0  # jd_skills rows are removed by ON DELETE CASCADE

    def count(self) -> int:
        return len(self._call("GET", "/jd_analyses", params={"select": "id"}).json())
