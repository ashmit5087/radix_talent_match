from conftest import cand, jd, sk
from skill_matching.service import match_raw


def run(c, j):
    return match_raw(c, j)


def statuses(resp):
    return {r.skill_name: r.status for r in
            resp.matched_skills + resp.partial_matches + resp.review_required + resp.missing_skills}


def test_exact_match():
    r = run(cand(sk("Python")), jd(sk("Python")))
    assert statuses(r) == {"Python": "matched"}
    assert r.matched_skills[0].match_method == "exact"


def test_alias_match():
    r = run(cand(sk("Postgres", "SQL")), jd(sk("PostgreSQL", "SQL")))
    assert r.matched_skills[0].match_method == "alias"


def test_java_not_javascript():
    r = run(cand(sk("JavaScript")), jd(sk("Java")))
    assert statuses(r) == {"Java": "missing"}


def test_sql_not_automatically_postgresql():
    r = run(cand(sk("PostgreSQL", "SQL")), jd(sk("SQL", "SQL")))
    assert statuses(r)["SQL"] != "matched"
    r2 = run(cand(sk("SQL", "SQL")), jd(sk("PostgreSQL", "SQL")))
    assert statuses(r2)["PostgreSQL"] != "matched"


def test_missing_listed():
    r = run(cand(sk("Python")), jd(sk("Python"), sk("Go")))
    assert [m.skill_name for m in r.missing_skills] == ["Go"]


def test_partial_labeled_partial():
    r = run(cand(sk("Algorithms", "DSA")), jd(sk("Data Structures and Algorithms", "DSA")))
    assert len(r.partial_matches) == 1 and not r.matched_skills
    assert r.partial_matches[0].contribution == 0.5
    assert r.match_score == 50


def test_composite_dsa_full_match():
    r = run(cand(sk("Data Structures", "DSA"), sk("Algorithms", "DSA")),
            jd(sk("Data Structures and Algorithms", "DSA")))
    assert statuses(r) == {"Data Structures and Algorithms": "matched"}


def test_aws_vs_generic_cloud_needs_review():
    r = run(cand(sk("Cloud", "CLOUD")), jd(sk("AWS", "CLOUD")))
    assert len(r.review_required) == 1 and r.match_score == 0


def test_duplicates_do_not_inflate():
    r = run(cand(sk("Python"), sk("python"), sk("Python programming")), jd(sk("Python"), sk("Go")))
    assert r.match_score == 50


def test_multiple_candidate_skills_count_once():
    r = run(cand(sk("Python"), sk("Python3"), sk("py")), jd(sk("Python")))
    assert len(r.matched_skills) == 1 and r.match_score == 100
    assert r.matched_skills[0].contribution == 1.0


def test_one_candidate_skill_many_requirements_warns_not_inflates():
    r = run(cand(sk("Algorithms", "DSA")),
            jd(sk("Algorithms", "DSA"), sk("Data Structures and Algorithms", "DSA")))
    assert r.match_score == 75  # 1.0 + 0.5 over 2
    assert any("supports 2 JD requirements" in w for w in r.warnings)


def test_low_confidence_candidate_is_review_not_match():
    r = run(cand(sk("Python", conf="low")), jd(sk("Python")))
    assert statuses(r) == {"Python": "review_required"} and r.match_score == 0


def test_missing_evidence_not_fabricated():
    r = run(cand(sk("Python", evidence=None)), jd(sk("Python", evidence=None)))
    m = r.matched_skills[0]
    assert m.candidate_evidence is None and m.candidate_evidence_present is False
    assert "no evidence" in m.rationale


def test_evidence_preserved_verbatim():
    r = run(cand(sk("Python", evidence="Built a Python ETL")), jd(sk("Python", evidence="Needs Python")))
    m = r.matched_skills[0]
    assert m.candidate_evidence == "Built a Python ETL" and m.jd_evidence == "Needs Python"


def test_short_terms_do_not_phrase_match():
    r = run(cand(sk("Go to market strategy", "OTHER")), jd(sk("Go", "COD")))
    assert statuses(r) == {"Go": "missing"}


def test_duplicate_jd_requirements_merged():
    r = run(cand(sk("Python")), jd(sk("Python"), sk("python programming")))
    assert r.score_breakdown.total_required_weight == 1.0
    assert any("Duplicate JD requirement" in w for w in r.warnings)


def test_low_confidence_jd_warns():
    r = run(cand(sk("Python")), jd(sk("Python", conf="low")))
    assert any("low confidence" in w for w in r.warnings)


def test_common_resume_evidence_is_partial_for_analytics_requirements():
    r = run(
        cand(
            sk("Power BI", "OTHER"),
            sk("Presentation", "COMM"),
            sk("Statistics", "APTI"),
            sk("Normalized schema", "SQL"),
        ),
        jd(
            sk("Data Visualization", "OTHER"),
            sk("Communication", "COMM"),
            sk("Quantitative Reasoning", "APTI"),
            sk("Schema Design", "SQL"),
        ),
    )
    assert r.match_score == 50
    assert {item.skill_name for item in r.partial_matches} == {
        "Data Visualization",
        "Communication",
        "Quantitative Reasoning",
        "Schema Design",
    }


def test_programming_requirement_gets_partial_credit_from_language():
    r = run(cand(sk("Python")), jd(sk("Programming")))
    assert r.match_score == 50
    assert r.partial_matches[0].skill_name == "Programming"
