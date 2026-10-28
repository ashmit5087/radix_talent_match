import logging
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile, status
from fastapi.responses import FileResponse
from ..adapters.resume_adapter import BaseResumeAdapter, get_resume_adapter
from ..repositories.profile_repository import DatabasePersistenceError
from ..schemas.profile import (
    CandidateProfileCreate,
    CandidateProfileResponse,
    CandidateProfileUpdate,
    CvUploadResponse,
    ProfileCompletenessResponse,
)
from ..schemas.skill import SkillListResponse
from ..services.profile_service import ProfileService, get_profile_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["Candidate Profiles (Role 3)"])


@router.post(
    "",
    response_model=CandidateProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new candidate profile",
    description="Creates a candidate profile with manual form entry. Generates and returns a stable profile_id.",
)
async def create_profile(
    payload: CandidateProfileCreate,
    service: ProfileService = Depends(get_profile_service),
) -> CandidateProfileResponse:
    try:
        profile = await service.create_profile(payload)
        return profile
    except DatabasePersistenceError as dbe:
        logger.error(f"Database persistence failure in create_profile: {dbe}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database persistence error: {str(dbe)}",
        )
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {str(e)}",
        )


@router.get(
    "/{profile_id}",
    response_model=CandidateProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve full candidate profile",
    description="Loads a candidate profile by its unique profile_id.",
)
async def get_profile(
    profile_id: str = Path(..., description="Unique UUID of the candidate profile"),
    service: ProfileService = Depends(get_profile_service),
) -> CandidateProfileResponse:
    try:
        profile = await service.get_profile(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate profile with id '{profile_id}' not found.",
            )
        return profile
    except DatabasePersistenceError as dbe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(dbe)}",
        )


@router.put(
    "/{profile_id}",
    response_model=CandidateProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update candidate profile",
    description="Updates candidate details, skills, education, and experience. Guarantees profile_id is preserved.",
)
async def update_profile(
    profile_id: str = Path(..., description="Unique UUID of the candidate profile to update"),
    payload: CandidateProfileUpdate = ...,
    service: ProfileService = Depends(get_profile_service),
) -> CandidateProfileResponse:
    try:
        updated = await service.update_profile(profile_id, payload)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate profile with id '{profile_id}' not found for update.",
            )
        return updated
    except DatabasePersistenceError as dbe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database update error: {str(dbe)}",
        )


@router.post(
    "/from-resume/{resume_id}",
    response_model=CandidateProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prefill and create candidate profile from parsed resume",
    description="Adapts parsed resume JSON (Role 2 contract) into a prefilled profile with source='extracted' tags.",
)
async def create_profile_from_resume(
    resume_id: str = Path(..., description="Mock resume identifier (e.g. 'mock-001', 'mock-002')"),
    service: ProfileService = Depends(get_profile_service),
    adapter: BaseResumeAdapter = Depends(get_resume_adapter),
) -> CandidateProfileResponse:
    try:
        profile = await service.create_from_resume(resume_id, adapter=adapter)
        return profile
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DatabasePersistenceError as dbe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database persistence error: {str(dbe)}",
        )
    except Exception as e:
        logger.error(f"Error adapting resume to profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prefill profile from resume: {str(e)}",
        )


@router.get(
    "/{profile_id}/skills",
    response_model=SkillListResponse,
    status_code=status.HTTP_200_OK,
    summary="Expose profile skills for Roles 4 & 5",
    description="Returns the structured skill list conforming to the agreed shared contract (skill_name, category_code, evidence, confidence).",
)
async def get_profile_skills(
    profile_id: str = Path(..., description="Unique UUID of the candidate profile"),
    service: ProfileService = Depends(get_profile_service),
) -> SkillListResponse:
    try:
        skills_response = await service.get_profile_skills(profile_id)
        if not skills_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate profile with id '{profile_id}' not found.",
            )
        return skills_response
    except DatabasePersistenceError as dbe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(dbe)}",
        )


@router.get(
    "/{profile_id}/completeness",
    response_model=ProfileCompletenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get profile completeness and missing recommendations",
    description="Calculates authoring completeness percentage and reports completed vs incomplete sections with suggestions.",
)
async def get_profile_completeness(
    profile_id: str = Path(..., description="Unique UUID of the candidate profile"),
    service: ProfileService = Depends(get_profile_service),
) -> ProfileCompletenessResponse:
    try:
        completeness = await service.get_completeness(profile_id)
        if not completeness:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate profile with id '{profile_id}' not found.",
            )
        return completeness
    except DatabasePersistenceError as dbe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(dbe)}",
        )


@router.post(
    "/{profile_id}/cv",
    response_model=CvUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and attach CV file to candidate profile",
    description="Uploads a PDF or DOCX CV document (max 10MB), sanitizes filename, and associates it with the candidate profile.",
)
async def upload_cv(
    profile_id: str = Path(..., description="Unique UUID of the candidate profile"),
    file: UploadFile = File(..., description="CV document file (.pdf, .docx, .doc)"),
    service: ProfileService = Depends(get_profile_service),
) -> CvUploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.",
        )

    try:
        content = await file.read()
        cv_response = await service.save_cv_file(
            profile_id=profile_id,
            original_filename=file.filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
        return cv_response
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except DatabasePersistenceError as dbe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database update error while saving CV: {str(dbe)}",
        )
    except Exception as e:
        logger.error(f"Error handling CV upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload CV: {str(e)}",
        )


@router.get(
    "/{profile_id}/cv",
    status_code=status.HTTP_200_OK,
    summary="Download attached CV file",
    description="Streams the stored candidate CV file.",
)
async def download_cv(
    profile_id: str = Path(..., description="Unique UUID of the candidate profile"),
    service: ProfileService = Depends(get_profile_service),
):
    try:
        file_path, original_filename, content_type = await service.get_cv_file(profile_id)
        return FileResponse(
            path=file_path,
            filename=original_filename,
            media_type=content_type,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error downloading CV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve CV: {str(e)}",
        )
