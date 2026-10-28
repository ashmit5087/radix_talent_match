import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional
from ..database import get_supabase_client
from ..schemas.profile import CandidateProfileResponse
from ..schemas.skill import SkillSchema

logger = logging.getLogger(__name__)


class DatabasePersistenceError(RuntimeError):
    """Raised when an active database operation fails, preventing false-positive success responses."""
    pass


class BaseProfileRepository(ABC):
    @abstractmethod
    async def create(self, profile: CandidateProfileResponse) -> CandidateProfileResponse:
        pass

    @abstractmethod
    async def get_by_id(self, profile_id: str) -> Optional[CandidateProfileResponse]:
        pass

    @abstractmethod
    async def update(
        self, profile_id: str, updated_profile: CandidateProfileResponse
    ) -> Optional[CandidateProfileResponse]:
        pass

    @abstractmethod
    async def list_all(self, limit: int = 50, offset: int = 0) -> List[CandidateProfileResponse]:
        pass

    @abstractmethod
    async def delete(self, profile_id: str) -> bool:
        pass


class ProfileRepository(BaseProfileRepository):
    """
    Unified repository with Supabase integration and in-memory development fallback.
    - If Supabase credentials are not configured, runs safely in local in-memory mode.
    - If Supabase IS configured, failures raise DatabasePersistenceError to prevent
      false-positive HTTP 200/201 success responses.
    """

    def __init__(self):
        self._memory_store: Dict[str, CandidateProfileResponse] = {}

    async def create(self, profile: CandidateProfileResponse) -> CandidateProfileResponse:
        client = get_supabase_client()
        if client:
            try:
                # 1. Persist master profile record with full JSON document
                profile_payload = {
                    "profile_id": profile.profile_id,
                    "full_name": profile.personal_info.full_name,
                    "email": profile.personal_info.email,
                    "profile_data": profile.model_dump(mode="json"),
                    "created_at": profile.created_at.isoformat(),
                    "updated_at": profile.updated_at.isoformat(),
                }
                client.table("profiles").upsert(profile_payload).execute()

                # 2. Persist individual skills relational rows for fast querying by Roles 4 & 5
                if profile.skills:
                    skills_rows = [
                        {
                            "profile_id": profile.profile_id,
                            "skill_name": s.skill_name,
                            "category_code": str(s.category_code.value if hasattr(s.category_code, "value") else s.category_code),
                            "evidence": s.evidence,
                            "confidence": str(s.confidence),
                            "source": s.source or "manual",
                        }
                        for s in profile.skills
                    ]
                    client.table("profile_skills").delete().eq("profile_id", profile.profile_id).execute()
                    client.table("profile_skills").insert(skills_rows).execute()

                logger.info(f"Persisted profile {profile.profile_id} to Supabase.")
            except Exception as e:
                logger.error(f"Supabase upsert failure for profile {profile.profile_id}: {e}")
                # DO NOT return false success: explicitly raise error
                raise DatabasePersistenceError(f"Failed to persist profile to database: {str(e)}") from e

        # Store in memory cache
        self._memory_store[profile.profile_id] = profile
        return profile

    async def get_by_id(self, profile_id: str) -> Optional[CandidateProfileResponse]:
        client = get_supabase_client()
        if client:
            try:
                response = (
                    client.table("profiles")
                    .select("profile_data")
                    .eq("profile_id", profile_id)
                    .limit(1)
                    .execute()
                )
                if response.data and len(response.data) > 0:
                    raw_data = response.data[0]["profile_data"]
                    profile = CandidateProfileResponse(**raw_data)
                    self._memory_store[profile_id] = profile
                    return profile
                return None
            except Exception as e:
                logger.error(f"Failed to query profile {profile_id} from Supabase: {e}")
                raise DatabasePersistenceError(f"Failed to query profile from database: {str(e)}") from e

        # Check in-memory store in local fallback mode
        return self._memory_store.get(profile_id)

    async def update(
        self, profile_id: str, updated_profile: CandidateProfileResponse
    ) -> Optional[CandidateProfileResponse]:
        existing = await self.get_by_id(profile_id)
        if not existing:
            return None

        # Guarantee profile_id remains unchanged
        updated_profile.profile_id = profile_id
        updated_profile.updated_at = datetime.now(timezone.utc)

        client = get_supabase_client()
        if client:
            try:
                profile_payload = {
                    "profile_id": profile_id,
                    "full_name": updated_profile.personal_info.full_name,
                    "email": updated_profile.personal_info.email,
                    "profile_data": updated_profile.model_dump(mode="json"),
                    "updated_at": updated_profile.updated_at.isoformat(),
                }
                client.table("profiles").upsert(profile_payload).execute()

                # Re-sync skills
                client.table("profile_skills").delete().eq("profile_id", profile_id).execute()
                if updated_profile.skills:
                    skills_rows = [
                        {
                            "profile_id": profile_id,
                            "skill_name": s.skill_name,
                            "category_code": str(s.category_code.value if hasattr(s.category_code, "value") else s.category_code),
                            "evidence": s.evidence,
                            "confidence": str(s.confidence),
                            "source": s.source or "manual",
                        }
                        for s in updated_profile.skills
                    ]
                    client.table("profile_skills").insert(skills_rows).execute()

                logger.info(f"Updated profile {profile_id} in Supabase.")
            except Exception as e:
                logger.error(f"Supabase update failure for profile {profile_id}: {e}")
                raise DatabasePersistenceError(f"Failed to update profile in database: {str(e)}") from e

        self._memory_store[profile_id] = updated_profile
        return updated_profile

    async def list_all(self, limit: int = 50, offset: int = 0) -> List[CandidateProfileResponse]:
        profiles = list(self._memory_store.values())
        return profiles[offset : offset + limit]

    async def delete(self, profile_id: str) -> bool:
        client = get_supabase_client()
        if client:
            try:
                client.table("profile_skills").delete().eq("profile_id", profile_id).execute()
                client.table("profiles").delete().eq("profile_id", profile_id).execute()
            except Exception as e:
                logger.error(f"Supabase delete failure for profile {profile_id}: {e}")
                raise DatabasePersistenceError(f"Failed to delete profile from database: {str(e)}") from e

        existed = profile_id in self._memory_store
        if existed:
            del self._memory_store[profile_id]
        return existed


# Global repository instance
_repo_instance: Optional[ProfileRepository] = None


def get_profile_repository() -> ProfileRepository:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = ProfileRepository()
    return _repo_instance
