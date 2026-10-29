import asyncio
import pytest
from app.adapters.resume_adapter import MockResumeAdapter


def test_adapt_mock_001_rohan():
    async def _test():
        adapter = MockResumeAdapter()
        profile_create = await adapter.adapt_to_profile("mock-001")

        assert profile_create.personal_info.full_name == "Rohan Verma"
        assert profile_create.personal_info.email == "rohan.verma@example.com"
        assert profile_create.personal_info.source == "extracted"

        # Verify skills
        assert len(profile_create.skills) >= 6
        for s in profile_create.skills:
            assert s.source == "extracted"
            assert s.category_code in [
                "COD", "DSA", "OOD", "APTI", "COMM", "AI",
                "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER"
            ]
            assert s.evidence
            assert s.confidence

        # Verify education
        assert len(profile_create.education) >= 1
        assert profile_create.education[0].source == "extracted"

        # Verify hackathons and internships split
        assert len(profile_create.hackathons) >= 1
        assert profile_create.hackathons[0].entry_type == "hackathon"
        assert len(profile_create.internships) >= 1
        assert profile_create.internships[0].entry_type == "internship"

    asyncio.run(_test())


def test_adapt_mock_002_ananya():
    async def _test():
        adapter = MockResumeAdapter()
        profile_create = await adapter.adapt_to_profile("mock-002")

        assert profile_create.personal_info.full_name == "Ananya Rao"
        assert profile_create.personal_info.email == "ananya.rao@example.com"
        assert "NETW" in [s.category_code for s in profile_create.skills]
        assert "OS" in [s.category_code for s in profile_create.skills]

    asyncio.run(_test())


def test_adapt_unknown_resume_raises_error():
    async def _test():
        adapter = MockResumeAdapter()
        with pytest.raises(KeyError):
            await adapter.adapt_to_profile("non_existent_resume_999")

    asyncio.run(_test())
