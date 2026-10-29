from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from .skill import SkillSchema


class PersonalInfo(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150, description="Full candidate name")
    email: EmailStr = Field(..., description="Candidate contact email")
    phone: Optional[str] = Field(None, max_length=30, description="Candidate phone number")
    location: Optional[str] = Field(None, max_length=100, description="City, State, Country")
    summary: Optional[str] = Field(None, max_length=2000, description="Professional or biographical summary")
    linkedin_url: Optional[str] = Field(None, max_length=255, description="LinkedIn profile URL")
    github_url: Optional[str] = Field(None, max_length=255, description="GitHub profile URL")
    portfolio_url: Optional[str] = Field(None, max_length=255, description="Personal portfolio or website URL")
    source: Optional[Literal["extracted", "manual"]] = "manual"

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("full_name cannot be empty or whitespace.")
        return stripped


class EducationEntry(BaseModel):
    institution: str = Field(..., min_length=1, max_length=200, description="College or University name")
    degree: str = Field(..., min_length=1, max_length=150, description="Degree name, e.g. B.Tech, B.S., M.S.")
    field_of_study: Optional[str] = Field(None, max_length=150, description="Major, e.g. Computer Science")
    start_date: Optional[str] = Field(None, description="Start year or date (e.g. '2022' or '2022-08')")
    end_date: Optional[str] = Field(None, description="End year or date (e.g. '2026' or 'Expected 2026')")
    currently_studying: bool = Field(default=False, description="Whether currently enrolled")
    grade: Optional[str] = Field(None, max_length=50, description="GPA or percentage, e.g. '8.9/10' or '3.8/4.0'")
    details: Optional[str] = Field(None, max_length=1000, description="Relevant coursework or honors")
    source: Optional[Literal["extracted", "manual"]] = "manual"


class ProjectEntry(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Project title")
    description: str = Field(..., min_length=1, max_length=2000, description="Brief project description and impact")
    technologies: List[str] = Field(default_factory=list, description="Technologies or tools used")
    link: Optional[str] = Field(None, max_length=255, description="Project repository or live demo URL")
    start_date: Optional[str] = Field(None, max_length=50)
    end_date: Optional[str] = Field(None, max_length=50)
    source: Optional[Literal["extracted", "manual"]] = "manual"


class ExperienceEntry(BaseModel):
    entry_type: Literal["internship", "hackathon", "other"] = Field(
        ...,
        description="Type of experience entry"
    )
    organization: str = Field(..., min_length=1, max_length=200, description="Company, organizer or sponsor")
    title: str = Field(..., min_length=1, max_length=150, description="Role title or project/hackathon track")
    start_date: Optional[str] = Field(None, max_length=50)
    end_date: Optional[str] = Field(None, max_length=50)
    currently_active: bool = Field(default=False)
    description: Optional[str] = Field(None, max_length=2000, description="Key deliverables and learnings")
    source: Optional[Literal["extracted", "manual"]] = "manual"


class CertificationEntry(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Certification title")
    issuer: str = Field(..., min_length=1, max_length=150, description="Issuing organization, e.g. AWS, Coursera")
    issue_date: Optional[str] = Field(None, max_length=50, description="Date issued")
    credential_url: Optional[str] = Field(None, max_length=255, description="Verification or badge URL")
    source: Optional[Literal["extracted", "manual"]] = "manual"


class CandidateProfileCreate(BaseModel):
    personal_info: PersonalInfo
    education: List[EducationEntry] = Field(default_factory=list)
    skills: List[SkillSchema] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    hackathons: List[ExperienceEntry] = Field(default_factory=list)
    internships: List[ExperienceEntry] = Field(default_factory=list)
    certifications: List[CertificationEntry] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    cv_file: Optional[str] = Field(None, description="Original uploaded CV filename or storage path")


class CandidateProfileUpdate(BaseModel):
    personal_info: Optional[PersonalInfo] = None
    education: Optional[List[EducationEntry]] = None
    skills: Optional[List[SkillSchema]] = None
    projects: Optional[List[ProjectEntry]] = None
    hackathons: Optional[List[ExperienceEntry]] = None
    internships: Optional[List[ExperienceEntry]] = None
    certifications: Optional[List[CertificationEntry]] = None
    preferred_roles: Optional[List[str]] = None
    cv_file: Optional[str] = None


class CandidateProfileResponse(BaseModel):
    profile_id: str = Field(..., description="Stable, backend-generated unique profile UUID")
    personal_info: PersonalInfo
    education: List[EducationEntry] = Field(default_factory=list)
    skills: List[SkillSchema] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    hackathons: List[ExperienceEntry] = Field(default_factory=list)
    internships: List[ExperienceEntry] = Field(default_factory=list)
    certifications: List[CertificationEntry] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    cv_file: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProfileCompletenessResponse(BaseModel):
    profile_id: str
    overall_percentage: int = Field(..., ge=0, le=100)
    section_scores: Dict[str, int]
    completed_sections: List[str]
    incomplete_sections: List[str]
    missing_recommendations: List[str]


class CvUploadResponse(BaseModel):
    profile_id: str
    cv_file: str = Field(..., description="Original filename of the uploaded CV")
    stored_filename: str = Field(..., description="Sanitized unique filename in storage")
    size_bytes: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME content type")
    uploaded_at: datetime
    message: str = "CV uploaded successfully"
