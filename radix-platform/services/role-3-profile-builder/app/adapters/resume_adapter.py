import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..schemas.profile import (
    CandidateProfileCreate,
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    PersonalInfo,
    ProjectEntry,
)
from ..schemas.resume import ParsedResumeData
from ..schemas.skill import SkillSchema

logger = logging.getLogger(__name__)


class BaseResumeAdapter(ABC):
    """
    Abstract adapter interface for converting parsed resume payloads
    (from Role 2: Resume Parsing) into canonical CandidateProfileCreate objects.
    This interface ensures Role 3 remains completely independent of Role 2's
    internal parsing implementation and can swap from mock data to real HTTP/gRPC
    endpoints with zero changes to business logic.
    """

    @abstractmethod
    async def get_parsed_resume(self, resume_id: str) -> Optional[ParsedResumeData]:
        """Fetch or load parsed resume data for a given resume_id."""
        pass

    @abstractmethod
    async def adapt_to_profile(self, resume_id: str) -> CandidateProfileCreate:
        """Convert parsed resume data into a canonical candidate profile creation model."""
        pass


class MockResumeAdapter(BaseResumeAdapter):
    """
    Loads mock parsed resume JSON data and translates it into canonical profile models.
    Marks all prefilled fields with source="extracted" so the candidate can visually
    distinguish them from manually entered data.
    """

    def __init__(self, mock_file_path: Optional[Path] = None):
        if mock_file_path is None:
            # Default to backend/mock_data/mock_parsed_resume.json
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.mock_file_path = base_dir / "mock_data" / "mock_parsed_resume.json"
        else:
            self.mock_file_path = Path(mock_file_path)

        self._data_cache: Dict[str, Any] = {}
        self._load_mock_data()

    def _load_mock_data(self) -> None:
        if self.mock_file_path.exists():
            try:
                with open(self.mock_file_path, "r", encoding="utf-8") as f:
                    self._data_cache = json.load(f)
                logger.info(f"Loaded {len(self._data_cache)} mock resume records from {self.mock_file_path}")
            except Exception as e:
                logger.error(f"Error loading mock resume file {self.mock_file_path}: {e}")
                self._data_cache = {}
        else:
            logger.warning(f"Mock resume file not found at {self.mock_file_path}")

    async def get_parsed_resume(self, resume_id: str) -> Optional[ParsedResumeData]:
        # Support aliases like 'rohan' -> 'mock-001', 'ananya' -> 'mock-002'
        lookup_id = resume_id.lower().strip()
        record = self._data_cache.get(lookup_id)

        if not record:
            for key, val in self._data_cache.items():
                cand = val.get("candidate", {})
                cand_name = cand.get("name", "").lower()
                if lookup_id in key.lower() or lookup_id in cand_name:
                    record = val
                    break

        if not record:
            return None

        return ParsedResumeData(**record)

    async def adapt_to_profile(self, resume_id: str) -> CandidateProfileCreate:
        parsed = await self.get_parsed_resume(resume_id)
        if not parsed:
            raise KeyError(f"Mock parsed resume not found for identifier: '{resume_id}'")

        candidate = parsed.candidate or {}
        if isinstance(candidate, dict):
            c_name = candidate.get("name", "Unknown Candidate")
            c_email = candidate.get("email", "candidate@example.com")
            c_phone = candidate.get("phone")
            c_location = candidate.get("location")
            c_summary = candidate.get("summary")
            c_linkedin = candidate.get("linkedin")
            c_github = candidate.get("github")
            c_portfolio = candidate.get("portfolio")
        else:
            c_name = candidate.name or "Unknown Candidate"
            c_email = candidate.email or "candidate@example.com"
            c_phone = candidate.phone
            c_location = candidate.location
            c_summary = candidate.summary
            c_linkedin = candidate.linkedin
            c_github = candidate.github
            c_portfolio = candidate.portfolio

        personal_info = PersonalInfo(
            full_name=c_name,
            email=c_email,
            phone=c_phone,
            location=c_location,
            summary=c_summary,
            linkedin_url=c_linkedin,
            github_url=c_github,
            portfolio_url=c_portfolio,
            source="extracted",
        )

        # Map skills
        adapted_skills: List[SkillSchema] = []
        for sk in parsed.skills:
            adapted_skills.append(
                SkillSchema(
                    skill_name=sk.skill_name,
                    category_code=sk.category_code,
                    evidence=sk.evidence,
                    confidence=sk.confidence,
                    source="extracted",
                )
            )

        # Map education
        adapted_education: List[EducationEntry] = []
        for edu in parsed.education:
            adapted_education.append(
                EducationEntry(
                    institution=edu.institution,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    start_date=edu.start_date,
                    end_date=edu.end_date,
                    grade=edu.grade,
                    details=edu.details,
                    source="extracted",
                )
            )

        # Map projects
        adapted_projects: List[ProjectEntry] = []
        for proj in parsed.projects:
            adapted_projects.append(
                ProjectEntry(
                    name=proj.name,
                    description=proj.description,
                    technologies=proj.technologies,
                    link=proj.link,
                    start_date=proj.start_date,
                    end_date=proj.end_date,
                    source="extracted",
                )
            )

        # Map experience (split into hackathons vs internships)
        adapted_hackathons: List[ExperienceEntry] = []
        adapted_internships: List[ExperienceEntry] = []
        for exp in parsed.experience:
            entry_type = (exp.entry_type or "internship").lower()
            norm_type = "hackathon" if "hackathon" in entry_type else "internship"
            entry = ExperienceEntry(
                entry_type=norm_type,
                organization=exp.organization,
                title=exp.title,
                start_date=exp.start_date,
                end_date=exp.end_date,
                description=exp.description,
                source="extracted",
            )
            if norm_type == "hackathon":
                adapted_hackathons.append(entry)
            else:
                adapted_internships.append(entry)

        # Map certifications
        adapted_certifications: List[CertificationEntry] = []
        for cert in parsed.certifications:
            adapted_certifications.append(
                CertificationEntry(
                    name=cert.name,
                    issuer=cert.issuer,
                    issue_date=cert.issue_date,
                    credential_url=cert.credential_url,
                    source="extracted",
                )
            )

        return CandidateProfileCreate(
            personal_info=personal_info,
            education=adapted_education,
            skills=adapted_skills,
            projects=adapted_projects,
            hackathons=adapted_hackathons,
            internships=adapted_internships,
            certifications=adapted_certifications,
            preferred_roles=parsed.preferred_roles,
            cv_file=parsed.source_file,
        )


# Global adapter instance and FastAPI dependency factory
_mock_adapter_instance: Optional[MockResumeAdapter] = None


def get_resume_adapter() -> BaseResumeAdapter:
    """FastAPI dependency to provide the active resume adapter."""
    global _mock_adapter_instance
    if _mock_adapter_instance is None:
        _mock_adapter_instance = MockResumeAdapter()
    return _mock_adapter_instance
