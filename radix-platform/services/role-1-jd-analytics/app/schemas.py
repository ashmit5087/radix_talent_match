"""Pydantic models: the shared RADIX schema plus the request/response models of this API.

Skill and ExtractedSkillList are the agreed cross-role contract. Do not rename their fields
or make extra fields mandatory.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ----------------------------------------------------------------------------------------
# Shared RADIX schema (source of truth for all five roles)
# ----------------------------------------------------------------------------------------
CategoryCode = Literal[
    "COD", "DSA", "OOD", "APTI", "COMM", "AI",
    "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER",
]

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "COD": "Coding",
    "DSA": "Data Structures & Algorithms",
    "OOD": "Object-Oriented Design",
    "APTI": "Aptitude",
    "COMM": "Communication",
    "AI": "Artificial Intelligence",
    "CLOUD": "Cloud Computing",
    "SQL": "SQL",
    "SWE": "Software Engineering",
    "SYSD": "System Design",
    "NETW": "Networking",
    "OS": "Operating Systems",
    "OTHER": "Anything outside the other categories",
}


class Skill(BaseModel):
    skill_name: str
    category_code: CategoryCode
    evidence: str
    confidence: Literal["high", "medium", "low"]


class ExtractedSkillList(BaseModel):
    source_type: Literal["jd", "resume"]
    source_file: str
    company: Optional[str] = None
    role: Optional[str] = None
    skills: list[Skill] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_type": "jd",
                "source_file": "data_scientist.pdf",
                "company": "Example Company",
                "role": "Data Scientist",
                "skills": [
                    {
                        "skill_name": "Python",
                        "category_code": "COD",
                        "evidence": "Proficiency in Python programming",
                        "confidence": "high",
                    }
                ],
            }
        }
    )


class JDAnalysisResponse(ExtractedSkillList):
    """The shared `ExtractedSkillList` plus the `jd_id` other roles use to refer to this analysis."""
    jd_id: str = Field(description="UUID of the saved analysis. Pass it to GET /jds/{jd_id} or to Skill Matching.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "jd_id": "3f0c6a52-8d3e-4a58-9c1e-2f6f9a1d7b10",
                "source_type": "jd",
                "source_file": "data_scientist.pdf",
                "company": "Example Company",
                "role": "Data Scientist",
                "skills": [{"skill_name": "Python", "category_code": "COD",
                            "evidence": "Proficiency in Python programming", "confidence": "high"}],
            }
        }
    )


class JDSkillsResponse(BaseModel):
    jd_id: str
    skills: list[Skill]


class UpdateSkillsRequest(BaseModel):
    skills: list[Skill] = Field(max_length=200, description="The complete corrected skill list. It replaces the stored list.")

    model_config = ConfigDict(json_schema_extra={"example": {"skills": [
        {"skill_name": "Python", "category_code": "COD", "evidence": "Proficiency in Python programming",
         "confidence": "high"},
        {"skill_name": "System Design", "category_code": "SYSD", "evidence": "Added by reviewer",
         "confidence": "medium"}]}})


class JDSummary(BaseModel):
    jd_id: str
    source_file: str
    company: Optional[str] = None
    role: Optional[str] = None
    skill_count: int
    indexing_status: Literal["indexed", "failed"]
    chunk_count: int
    created_at: str
    updated_at: str


class JDListResponse(BaseModel):
    count: int
    items: list[JDSummary]


# ----------------------------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Human-readable explanation.")
    details: Optional[list | dict | str] = Field(default=None, description="Extra context, if any.")


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ----------------------------------------------------------------------------------------
# System / categories
# ----------------------------------------------------------------------------------------
class RootResponse(BaseModel):
    service: str
    version: str
    description: str
    docs_url: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class CategoryInfo(BaseModel):
    code: CategoryCode
    description: str


class CategoriesResponse(BaseModel):
    categories: list[CategoryInfo]


class ProviderInfo(BaseModel):
    llm_provider: str
    llm_model: str
    llm_api_key_configured: bool = Field(description="True/False only. The key itself is never returned.")
    embedding_model: str
    vector_database: str = "chromadb"
    chroma_collection: str


# ----------------------------------------------------------------------------------------
# Semantic search / index management
# ----------------------------------------------------------------------------------------
MAX_TOP_K = 20


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000, description="Natural-language search text.")
    top_k: int = Field(5, ge=1, le=MAX_TOP_K, description=f"Number of chunks to return (1-{MAX_TOP_K}).")

    @field_validator("query")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be blank")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"query": "machine learning and predictive analytics experience", "top_k": 5}
        }
    )


class SearchHit(BaseModel):
    chunk_text: str
    jd_id: str = Field(description="The saved analysis this chunk belongs to.")
    source_file: str
    company: Optional[str] = None
    role: Optional[str] = None
    chunk_index: int
    distance: float = Field(
        description="Raw ChromaDB cosine distance (0 = same direction, larger = less similar). "
        "Not a probability or a percentage match; use it only to compare results of one query."
    )


class SearchResponse(BaseModel):
    query: str
    top_k: int
    distance_metric: Literal["cosine"] = "cosine"
    count: int
    results: list[SearchHit]


class DeleteJDResponse(BaseModel):
    jd_id: str
    analysis_deleted: bool = True
    chunks_deleted: int
    note: str = ("Deleted the saved analysis and all indexed text chunks, embeddings and metadata for this JD. "
                 "No original upload was ever stored, so there is no file to delete.")


class ClearIndexResponse(BaseModel):
    chunks_deleted: int
    note: str = ("The ChromaDB search index was emptied. Saved analyses (and their jd_ids) are NOT deleted; "
                 "they simply are no longer searchable.")
