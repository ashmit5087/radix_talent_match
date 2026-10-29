import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from ..adapters.resume_adapter import BaseResumeAdapter, get_resume_adapter
from ..repositories.profile_repository import ProfileRepository, get_profile_repository
from ..schemas.profile import (
    CandidateProfileCreate,
    CandidateProfileResponse,
    CandidateProfileUpdate,
    CvUploadResponse,
    ProfileCompletenessResponse,
)
from ..schemas.skill import CategoryCode, SkillListResponse

logger = logging.getLogger(__name__)

ALLOWED_CV_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_CV_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class ProfileService:
    def __init__(
        self,
        repository: Optional[ProfileRepository] = None,
        upload_dir: Optional[Path] = None,
    ):
        self.repository = repository or get_profile_repository()
        if upload_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.upload_dir = base_dir / "uploads" / "cvs"
        else:
            self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def create_profile(self, data: CandidateProfileCreate) -> CandidateProfileResponse:
        """
        Creates a new candidate profile, generating a stable UUID on the backend.
        """
        profile_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        profile = CandidateProfileResponse(
            profile_id=profile_id,
            personal_info=data.personal_info,
            education=data.education,
            skills=data.skills,
            projects=data.projects,
            hackathons=data.hackathons,
            internships=data.internships,
            certifications=data.certifications,
            preferred_roles=data.preferred_roles,
            cv_file=data.cv_file,
            created_at=now,
            updated_at=now,
        )

        return await self.repository.create(profile)

    async def get_profile(self, profile_id: str) -> Optional[CandidateProfileResponse]:
        """Retrieves a candidate profile by profile_id."""
        return await self.repository.get_by_id(profile_id)

    async def update_profile(
        self, profile_id: str, data: CandidateProfileUpdate
    ) -> Optional[CandidateProfileResponse]:
        """
        Updates an existing candidate profile.
        GUARANTEE: The profile_id is immutable and strictly preserved.
        """
        existing = await self.repository.get_by_id(profile_id)
        if not existing:
            return None

        # Build merged personal info if provided
        updated_personal = existing.personal_info
        if data.personal_info is not None:
            updated_personal = data.personal_info

        # Create updated response instance, preserving created_at and profile_id
        updated = CandidateProfileResponse(
            profile_id=profile_id,
            personal_info=updated_personal,
            education=data.education if data.education is not None else existing.education,
            skills=data.skills if data.skills is not None else existing.skills,
            projects=data.projects if data.projects is not None else existing.projects,
            hackathons=data.hackathons if data.hackathons is not None else existing.hackathons,
            internships=data.internships if data.internships is not None else existing.internships,
            certifications=data.certifications if data.certifications is not None else existing.certifications,
            preferred_roles=data.preferred_roles if data.preferred_roles is not None else existing.preferred_roles,
            cv_file=data.cv_file if data.cv_file is not None else existing.cv_file,
            created_at=existing.created_at,
            updated_at=datetime.now(timezone.utc),
        )

        return await self.repository.update(profile_id, updated)

    async def create_from_resume(
        self, resume_id: str, adapter: Optional[BaseResumeAdapter] = None
    ) -> CandidateProfileResponse:
        """
        Prefills a full candidate profile from parsed resume data provided by Role 2.
        All prefilled fields carry source='extracted'.
        """
        active_adapter = adapter or get_resume_adapter()
        profile_create_payload = await active_adapter.adapt_to_profile(resume_id)
        return await self.create_profile(profile_create_payload)

    async def get_profile_skills(self, profile_id: str) -> Optional[SkillListResponse]:
        """
        Exposes profile skills consumed by Role 4 (Talent Check) and Role 5 (Skill Matching).
        Preserves canonical fields: skill_name, category_code, evidence, confidence.
        """
        profile = await self.repository.get_by_id(profile_id)
        if not profile:
            return None

        unique_categories: List[CategoryCode] = []
        for s in profile.skills:
            if s.category_code not in unique_categories:
                unique_categories.append(s.category_code)

        return SkillListResponse(
            profile_id=profile.profile_id,
            skills=profile.skills,
            total_skills=len(profile.skills),
            categories_covered=unique_categories,
        )

    async def get_completeness(self, profile_id: str) -> Optional[ProfileCompletenessResponse]:
        """
        Measures candidate Profile Authoring Completeness (data coverage).
        Explicit design note:
          - Does NOT measure company readiness (owned by Role 4: Talent Check).
          - Does NOT measure candidate skill proficiency.
          - Does NOT measure job-matching likelihood (owned by Role 5: Skill Matching).
          - Measures whether the candidate has authored sufficient profile metadata
            for downstream analysis across all 7 sections.

        Weighting matrix (Total: 100 points):
          1. Personal Info:  20 pts (name & email: 12 pts, contact/location: 4 pts, summary: 4 pts)
          2. Education:      15 pts (>= 1 degree entry)
          3. Skills:         25 pts (>= 5 skills: 25 pts, >= 3: 18 pts, >= 1: 10 pts)
          4. Projects:       15 pts (>= 2 projects: 15 pts, 1 project: 10 pts)
          5. Experience:     10 pts (>= 1 internship or hackathon entry)
          6. Certifications: 10 pts (>= 1 certification entry)
          7. Preferred Roles: 5 pts (>= 1 target role)
        """
        profile = await self.repository.get_by_id(profile_id)
        if not profile:
            return None

        section_scores: Dict[str, int] = {}
        completed: List[str] = []
        incomplete: List[str] = []
        recommendations: List[str] = []

        # 1. Personal Info (20)
        p = profile.personal_info
        p_score = 0
        if p.full_name and p.email:
            p_score += 12
        if p.phone or p.location:
            p_score += 4
        if p.summary:
            p_score += 4
        section_scores["personal_info"] = p_score
        if p_score >= 16:
            completed.append("personal_info")
        else:
            incomplete.append("personal_info")
            recommendations.append("Complete personal information with a bio summary and phone/location.")

        # 2. Education (15)
        if len(profile.education) > 0:
            section_scores["education"] = 15
            completed.append("education")
        else:
            section_scores["education"] = 0
            incomplete.append("education")
            recommendations.append("Add at least one educational qualification or university degree.")

        # 3. Skills (25)
        s_count = len(profile.skills)
        if s_count >= 5:
            s_score = 25
        elif s_count >= 3:
            s_score = 18
        elif s_count >= 1:
            s_score = 10
        else:
            s_score = 0
        section_scores["skills"] = s_score
        if s_score >= 18:
            completed.append("skills")
        else:
            incomplete.append("skills")
            recommendations.append("Add at least 3 to 5 verified skills with concrete evidence.")

        # 4. Projects (15)
        proj_count = len(profile.projects)
        if proj_count >= 2:
            proj_score = 15
        elif proj_count == 1:
            proj_score = 10
        else:
            proj_score = 0
        section_scores["projects"] = proj_score
        if proj_score >= 10:
            completed.append("projects")
        else:
            incomplete.append("projects")
            recommendations.append("Showcase at least 1 to 2 technical projects with descriptions.")

        # 5. Experience (10) - internships or hackathons
        exp_count = len(profile.internships) + len(profile.hackathons)
        if exp_count >= 1:
            section_scores["experience"] = 10
            completed.append("experience")
        else:
            section_scores["experience"] = 0
            incomplete.append("experience")
            recommendations.append("Add relevant internship work experience or hackathon participations.")

        # 6. Certifications (10)
        cert_count = len(profile.certifications)
        if cert_count >= 1:
            section_scores["certifications"] = 10
            completed.append("certifications")
        else:
            section_scores["certifications"] = 0
            incomplete.append("certifications")
            recommendations.append("Add industry certifications or credentials.")

        # 7. Preferred Roles (5)
        roles_count = len(profile.preferred_roles)
        if roles_count >= 1:
            section_scores["preferred_roles"] = 5
            completed.append("preferred_roles")
        else:
            section_scores["preferred_roles"] = 0
            incomplete.append("preferred_roles")
            recommendations.append("Select at least 1 preferred target career role.")

        overall = sum(section_scores.values())

        return ProfileCompletenessResponse(
            profile_id=profile_id,
            overall_percentage=min(100, overall),
            section_scores=section_scores,
            completed_sections=completed,
            incomplete_sections=incomplete,
            missing_recommendations=recommendations,
        )

    async def save_cv_file(
        self,
        profile_id: str,
        original_filename: str,
        content: bytes,
        content_type: str,
    ) -> CvUploadResponse:
        """
        Validates, sanitizes, and persists an uploaded candidate CV document.
        Updates the profile record with the stored CV file reference.
        """
        profile = await self.repository.get_by_id(profile_id)
        if not profile:
            raise KeyError(f"Candidate profile '{profile_id}' not found.")

        # 1. Validate file extension
        clean_ext = Path(original_filename).suffix.lower()
        if clean_ext not in ALLOWED_CV_EXTENSIONS:
            raise ValueError(
                f"Unsupported CV file extension '{clean_ext}'. Allowed formats: {', '.join(sorted(ALLOWED_CV_EXTENSIONS))}"
            )

        # 2. Validate file size
        size_bytes = len(content)
        if size_bytes == 0:
            raise ValueError("Uploaded CV file is empty.")
        if size_bytes > MAX_CV_SIZE_BYTES:
            raise ValueError(
                f"CV file size ({size_bytes} bytes) exceeds maximum allowable limit of {MAX_CV_SIZE_BYTES // (1024 * 1024)} MB."
            )

        # 3. Sanitize filename to prevent path traversal
        raw_name = Path(original_filename).stem
        sanitized_stem = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", raw_name)[:50]
        stored_filename = f"{profile_id}_{sanitized_stem}{clean_ext}"
        destination_path = self.upload_dir / stored_filename

        # Write to disk
        destination_path.write_bytes(content)
        logger.info(f"Saved uploaded CV to {destination_path} ({size_bytes} bytes)")

        # 4. Update profile record
        await self.update_profile(profile_id, CandidateProfileUpdate(cv_file=original_filename))

        return CvUploadResponse(
            profile_id=profile_id,
            cv_file=original_filename,
            stored_filename=stored_filename,
            size_bytes=size_bytes,
            content_type=content_type or "application/octet-stream",
            uploaded_at=datetime.now(timezone.utc),
            message="CV uploaded and attached to profile successfully.",
        )

    async def get_cv_file(self, profile_id: str) -> Tuple[Path, str, str]:
        """
        Returns (file_path, original_filename, content_type) for downloading CV.
        """
        profile = await self.repository.get_by_id(profile_id)
        if not profile or not profile.cv_file:
            raise FileNotFoundError(f"No CV document found for profile '{profile_id}'.")

        # Find matching stored file by profile_id prefix
        matches = list(self.upload_dir.glob(f"{profile_id}_*"))
        if not matches:
            raise FileNotFoundError(f"CV physical file for profile '{profile_id}' not found in storage.")

        target_file = matches[0]
        ext = target_file.suffix.lower()
        content_type = "application/pdf" if ext == ".pdf" else "application/octet-stream"

        return target_file, profile.cv_file, content_type


# Global service instance
_service_instance: Optional[ProfileService] = None


def get_profile_service() -> ProfileService:
    global _service_instance
    if _service_instance is None:
        _service_instance = ProfileService()
    return _service_instance
