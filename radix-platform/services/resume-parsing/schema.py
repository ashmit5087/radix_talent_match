"""
Shared data structure for JD Analytics (Role 1) and Resume Parsing (Role 2).
Both roles import from this one file so the output always matches.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# The 12 RADIX skill categories + OTHER
CategoryCode = Literal[
    "COD", "DSA", "OOD", "APTI", "COMM", "AI",
    "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER",
]

CATEGORY_NAMES = {
    "COD": "Coding",
    "DSA": "Data Structures & Algorithms",
    "OOD": "Object-Oriented Design",
    "APTI": "Aptitude",
    "COMM": "Communication",
    "AI": "AI",
    "CLOUD": "Cloud",
    "SQL": "SQL",
    "SWE": "Software Engineering",
    "SYSD": "System Design",
    "NETW": "Networking",
    "OS": "Operating Systems",
    "OTHER": "Anything outside the 12",
}


# One skill — same for JD and resume
class Skill(BaseModel):
    skill_name: str
    category_code: CategoryCode
    evidence: str                      # short quote or reason
    confidence: Literal["high", "medium", "low"]


# The common output — both roles hand this off
class ExtractedSkillList(BaseModel):
    source_type: Literal["jd", "resume"]
    source_file: str                   # original filename only, e.g. "anya_rao.pdf" — never a full local path
    company: Optional[str] = None      # JD fills this; resume leaves None
    role: Optional[str] = None         # JD fills this; resume leaves None
    skills: List[Skill]


# Resume Parsing only — adds extra fields on top of the common output
class ResumeExtract(ExtractedSkillList):
    source_type: Literal["resume"] = "resume"
    education: Optional[str] = None
    projects: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
