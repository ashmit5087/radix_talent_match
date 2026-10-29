from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .skill import SkillSchema


class ParsedCandidateInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


class ParsedEducation(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    grade: Optional[str] = None
    details: Optional[str] = None


class ParsedProject(BaseModel):
    name: str
    description: str
    technologies: List[str] = Field(default_factory=list)
    link: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ParsedExperience(BaseModel):
    entry_type: Optional[str] = "internship"  # internship, hackathon, work
    organization: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ParsedCertification(BaseModel):
    name: str
    issuer: str
    issue_date: Optional[str] = None
    credential_url: Optional[str] = None


class ParsedResumeData(BaseModel):
    resume_id: Optional[str] = None
    source_type: str = "resume"
    source_file: Optional[str] = None
    candidate: Optional[ParsedCandidateInfo] = None
    skills: List[SkillSchema] = Field(default_factory=list)
    education: List[ParsedEducation] = Field(default_factory=list)
    projects: List[ParsedProject] = Field(default_factory=list)
    experience: List[ParsedExperience] = Field(default_factory=list)
    certifications: List[ParsedCertification] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    raw_metadata: Optional[Dict[str, Any]] = None
