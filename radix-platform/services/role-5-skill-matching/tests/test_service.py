import pytest
from conftest import cand, jd, sk
from skill_matching.service import InvalidInputError, NoJobSkillsError, match_raw, preview_raw

REQUIRED = {"jd_source_file", "match_score", "matched_skills", "missing_skills"}


def test_required_fields_always_present():
    d = match_raw(cand(sk("Python")), jd(sk("Go"))).model_dump()
    assert REQUIRED <= d.keys()
    assert d["jd_source_file"] == "test_jd.json"


def test_empty_jd_rejected():
    with pytest.raises(NoJobSkillsError):
        match_raw(cand(sk("Python")), jd())


def test_missing_skills_key_rejected():
    with pytest.raises(InvalidInputError):
        match_raw(cand(sk("Python")), {"source_file": "x"})


def test_blank_skill_name_rejected():
    with pytest.raises(InvalidInputError):
        match_raw(cand(sk("Python")), jd({"skill_name": "  "}))


def test_unknown_extra_fields_ignored():
    r = match_raw({"name": "x", "email": "e@x.com", "skills": [sk("Python")]},
                  {**jd(sk("Python")), "extra": 1})
    assert r.match_score == 100


def test_every_requirement_accounted_for():
    j = jd(sk("Python"), sk("Algorithms", "DSA"), sk("AWS", "CLOUD"), sk("Go"))
    r = match_raw(cand(sk("Python"), sk("Data Structures", "DSA"), sk("Cloud", "CLOUD")), j)
    total = len(r.matched_skills) + len(r.partial_matches) + len(r.review_required) + len(r.missing_skills)
    assert total == 4


def test_fixtures_differ_across_candidates(load):
    swe, data = load("sample_jd.json"), load("sample_jd_data_role.json")
    a, b = load("sample_candidate.json"), load("sample_candidate_data.json")
    assert match_raw(a, swe).match_score > match_raw(b, swe).match_score
    assert match_raw(b, data).match_score > match_raw(a, data).match_score


def test_preview_has_results():
    p = preview_raw(cand(sk("Python")), jd(sk("Python"), sk("Go")))
    assert len(p.results) == 2
