import pytest
from conftest import cand, jd, sk
from skill_matching.scorer import compute_score
from skill_matching.service import match_raw


def test_empty_candidate_scores_zero():
    r = match_raw(cand(), jd(sk("Python"), sk("SQL", "SQL")))
    assert r.match_score == 0 and len(r.missing_skills) == 2
    assert any("no skills" in w for w in r.warnings)


def test_score_in_range_and_formula():
    r = match_raw(cand(sk("Python")), jd(sk("Python"), sk("Go"), sk("Rust")))
    assert 0 <= r.match_score <= 100 and r.match_score == 33


def test_perfect_score():
    assert match_raw(cand(sk("Python")), jd(sk("Python"))).match_score == 100


def test_unrelated_skills_do_not_boost():
    base = match_raw(cand(sk("Python")), jd(sk("Python"), sk("Go")))
    more = match_raw(cand(sk("Python"), sk("Cooking", "OTHER"), sk("Painting", "OTHER")), jd(sk("Python"), sk("Go")))
    assert base.match_score == more.match_score == 50


def test_importance_weights_supported():
    j = jd({**sk("Python"), "importance": 3}, sk("Go"))
    r = match_raw(cand(sk("Python")), j)
    assert r.match_score == 75 and r.score_breakdown.total_required_weight == 4.0


def test_compute_score_rejects_empty():
    with pytest.raises(ValueError):
        compute_score([])


def test_deterministic():
    a = match_raw(cand(sk("Python"), sk("Algorithms", "DSA")), jd(sk("Python"), sk("Data Structures and Algorithms", "DSA")))
    b = match_raw(cand(sk("Python"), sk("Algorithms", "DSA")), jd(sk("Python"), sk("Data Structures and Algorithms", "DSA")))
    assert a.model_dump() == b.model_dump()


def test_stronger_candidate_scores_higher():
    j = jd(sk("Python"), sk("SQL", "SQL"), sk("Git", "SWE"), sk("Docker", "CLOUD"))
    strong = match_raw(cand(sk("Python"), sk("SQL", "SQL"), sk("Git", "SWE")), j)
    weak = match_raw(cand(sk("Python")), j)
    assert strong.match_score > weak.match_score
