import asyncio
import uuid
import pytest
from app.schemas.profile import (
    CandidateProfileCreate,
    CandidateProfileUpdate,
    PersonalInfo,
    EducationEntry,
)
from app.schemas.skill import SkillSchema
from app.services.profile_service import ProfileService, MAX_CV_SIZE_BYTES


def test_service_create_and_get_profile(sample_profile_payload):
    async def _test():
        service = ProfileService()
        create_model = CandidateProfileCreate(**sample_profile_payload)

        profile = await service.create_profile(create_model)

        assert profile.profile_id is not None
        uuid_obj = uuid.UUID(profile.profile_id)
        assert str(uuid_obj) == profile.profile_id
        assert profile.personal_info.full_name == "Karthik Subramaniam"

        retrieved = await service.get_profile(profile.profile_id)
        assert retrieved is not None
        assert retrieved.profile_id == profile.profile_id
        assert retrieved.personal_info.email == "karthik.sub@example.com"

    asyncio.run(_test())


def test_service_update_preserves_profile_id(sample_profile_payload):
    async def _test():
        service = ProfileService()
        create_model = CandidateProfileCreate(**sample_profile_payload)
        profile = await service.create_profile(create_model)

        original_id = profile.profile_id
        original_created_at = profile.created_at

        # Update personal info and add a new preferred role
        update_data = CandidateProfileUpdate(
            personal_info=PersonalInfo(
                full_name="Karthik S. Subramaniam",
                email="karthik.updated@example.com",
                phone="+91 99999 88888",
            ),
            preferred_roles=["Senior Data Engineer"],
        )

        updated = await service.update_profile(original_id, update_data)

        assert updated is not None
        # CRITICAL INVARIANT: profile_id must be strictly preserved
        assert updated.profile_id == original_id
        assert updated.personal_info.full_name == "Karthik S. Subramaniam"
        assert updated.personal_info.email == "karthik.updated@example.com"
        assert updated.preferred_roles == ["Senior Data Engineer"]
        assert updated.created_at == original_created_at
        assert updated.updated_at >= original_created_at

    asyncio.run(_test())


def test_service_get_skills_for_roles_4_and_5(sample_profile_payload):
    async def _test():
        service = ProfileService()
        create_model = CandidateProfileCreate(**sample_profile_payload)
        profile = await service.create_profile(create_model)

        skills_resp = await service.get_profile_skills(profile.profile_id)

        assert skills_resp is not None
        assert skills_resp.profile_id == profile.profile_id
        assert skills_resp.total_skills == 3
        assert set(skills_resp.categories_covered) == {"COD", "SQL", "DSA"}
        for s in skills_resp.skills:
            assert s.skill_name
            assert s.category_code
            assert s.evidence
            assert s.confidence in ["high", "medium", "low"]

    asyncio.run(_test())


def test_service_completeness_calculation(sample_profile_payload):
    async def _test():
        service = ProfileService()
        # 1. Full profile
        create_model = CandidateProfileCreate(**sample_profile_payload)
        profile = await service.create_profile(create_model)

        completeness = await service.get_completeness(profile.profile_id)
        assert completeness is not None
        assert completeness.overall_percentage >= 80
        assert "skills" in completeness.completed_sections
        assert "education" in completeness.completed_sections

        # 2. Bare minimum profile
        bare_profile_create = CandidateProfileCreate(
            personal_info=PersonalInfo(
                full_name="Minimal User",
                email="minimal@example.com"
            )
        )
        bare_profile = await service.create_profile(bare_profile_create)
        bare_completeness = await service.get_completeness(bare_profile.profile_id)

        assert bare_completeness is not None
        assert bare_completeness.overall_percentage < 30
        assert "skills" in bare_completeness.incomplete_sections
        assert len(bare_completeness.missing_recommendations) > 0

    asyncio.run(_test())


def test_cv_file_upload_and_retrieval(sample_profile_payload, tmp_path):
    async def _test():
        service = ProfileService(upload_dir=tmp_path)
        create_model = CandidateProfileCreate(**sample_profile_payload)
        profile = await service.create_profile(create_model)

        pdf_bytes = b"%PDF-1.4 mock pdf content"
        cv_resp = await service.save_cv_file(
            profile_id=profile.profile_id,
            original_filename="sample_resume.pdf",
            content=pdf_bytes,
            content_type="application/pdf",
        )

        assert cv_resp.profile_id == profile.profile_id
        assert cv_resp.cv_file == "sample_resume.pdf"
        assert cv_resp.size_bytes == len(pdf_bytes)

        # Retrieve file
        path, orig_name, c_type = await service.get_cv_file(profile.profile_id)
        assert path.exists()
        assert orig_name == "sample_resume.pdf"
        assert c_type == "application/pdf"

    asyncio.run(_test())


def test_cv_file_upload_rejects_invalid_extension(sample_profile_payload, tmp_path):
    async def _test():
        service = ProfileService(upload_dir=tmp_path)
        create_model = CandidateProfileCreate(**sample_profile_payload)
        profile = await service.create_profile(create_model)

        with pytest.raises(ValueError) as exc_info:
            await service.save_cv_file(
                profile_id=profile.profile_id,
                original_filename="malicious.exe",
                content=b"malicious content",
                content_type="application/x-msdownload",
            )
        assert "Unsupported CV file extension" in str(exc_info.value)

    asyncio.run(_test())


def test_cv_file_upload_rejects_oversized_file(sample_profile_payload, tmp_path):
    async def _test():
        service = ProfileService(upload_dir=tmp_path)
        create_model = CandidateProfileCreate(**sample_profile_payload)
        profile = await service.create_profile(create_model)

        oversized_bytes = b"0" * (MAX_CV_SIZE_BYTES + 10)
        with pytest.raises(ValueError) as exc_info:
            await service.save_cv_file(
                profile_id=profile.profile_id,
                original_filename="huge_file.pdf",
                content=oversized_bytes,
                content_type="application/pdf",
            )
        assert "exceeds maximum allowable limit" in str(exc_info.value)

    asyncio.run(_test())
