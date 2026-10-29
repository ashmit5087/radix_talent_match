import json
import os
from talent_check.backend.levels import (
    get_candidate_levels_with_points,
    points_to_level,
    derive_evidence_points,
    DEFAULT_K
)
from talent_check.backend.scoring import score

def test_saturating_curve_math():
    """Verify exact points-to-level mapping against user specification (with k=4)."""
    expected_curve = [
        (0.0, 0),
        (1.0, 2),
        (3.0, 5),
        (5.0, 7),
        (8.0, 9),
        (12.0, 10),
    ]
    for pts, expected_lvl in expected_curve:
        calculated = points_to_level(pts, k=4.0)
        assert calculated == expected_lvl, (
            f"Curve mismatch at {pts} pts: got {calculated}, expected {expected_lvl}"
        )
    print("[PASSED] Saturating curve formula verified (0->0, 1->2, 3->5, 5->7, 8->9, 12->10).")

def test_benchmark_sanity_checks():
    test_saturating_curve_math()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    companies_path = os.path.join(data_dir, "companies.json")
    
    with open(companies_path, "r", encoding="utf-8") as f:
        companies = json.load(f)
    
    google = next(c for c in companies if "Google" in c["company"])
    msft = next(c for c in companies if "Microsoft Corporation" in c["company"])
    oracle_fss = next(c for c in companies if "Oracle Financial Services" in c["company"])

    mock_profiles = ["ananya_rao.json", "karthik_subramaniam.json", "priya_menon.json", "rohan_verma.json"]
    
    print(f"\n================== BENCHMARK SANITY CHECKS (k={DEFAULT_K}) ==================")
    for filename in mock_profiles:
        profile_path = os.path.join(data_dir, "mock_profiles", filename)
        with open(profile_path, "r", encoding="utf-8") as pf:
            profile = json.load(pf)
        
        levels, pts = get_candidate_levels_with_points(profile, k=DEFAULT_K)
        
        g_res = score(levels, google, pts)
        m_res = score(levels, msft, pts)
        o_res = score(levels, oracle_fss, pts)
        
        print(f"\nCandidate: {profile['name']} ({profile['headline'][:50]}...)")
        print(f"  -> Google LLC score:       {g_res['readiness_score']}/100 [{g_res['verdict']}] (Met: {g_res['summary']['met_count']}/12, Gaps: {g_res['summary']['gap_count']})")
        print(f"  -> Microsoft Corp score:  {m_res['readiness_score']}/100 [{m_res['verdict']}] (Met: {m_res['summary']['met_count']}/12, Gaps: {m_res['summary']['gap_count']})")
        print(f"  -> Oracle FSS score:      {o_res['readiness_score']}/100 [{o_res['verdict']}] (Met: {o_res['summary']['met_count']}/12, Gaps: {o_res['summary']['gap_count']})")

    # Priya Sanity Check: Priya should score higher on Oracle FSS than on Google
    with open(os.path.join(data_dir, "mock_profiles", "priya_menon.json"), "r", encoding="utf-8") as pf:
        priya = json.load(pf)
    p_levels, p_pts = get_candidate_levels_with_points(priya, k=DEFAULT_K)
    p_google = score(p_levels, google, p_pts)["readiness_score"]
    p_oracle = score(p_levels, oracle_fss, p_pts)["readiness_score"]
    assert p_oracle > p_google, f"Priya vs Oracle ({p_oracle}) should be higher than Priya vs Google ({p_google})"
    print(f"\n[PASSED] Priya vs Oracle FSS score ({p_oracle}%) is noticeably higher than Google LLC ({p_google}%)!")

if __name__ == "__main__":
    test_benchmark_sanity_checks()


def test_default_k_curve():
    """Default k=2.0: 1 pt -> 4, 2 -> 6, 3 -> 8, 4 -> 9 (a strong profile can reach real company bars of 7-9)."""
    assert DEFAULT_K == 2.0
    for pts, lvl in [(0.0, 0), (1.0, 4), (2.0, 6), (3.0, 8), (4.0, 9)]:
        assert points_to_level(pts) == lvl, (pts, points_to_level(pts), lvl)


def _all_tens_except(code, level):
    from talent_check.backend.scoring import CATEGORIES_META
    levels = {c: 10 for c in CATEGORIES_META}
    levels[code] = level
    return levels


def test_critical_gap_threshold_is_four_and_exposed():
    """gap 3 is a scored gap, gap 4 is critical; the threshold is returned for downstream consumers."""
    from talent_check.backend.scoring import CRITICAL_GAP_MIN
    company = {"company": "X", "id": 1, "skills": {"COD": {"required_level": 8, "tier": "AP"}}}
    gap3 = score(_all_tens_except("COD", 5), company)
    gap4 = score(_all_tens_except("COD", 4), company)
    assert CRITICAL_GAP_MIN == 4
    assert gap3["summary"]["critical_categories"] == [] and gap3["summary"]["critical_gap_min"] == 4
    assert gap4["summary"]["critical_categories"] == ["COD"] and gap4["summary"]["critical_gap_count"] == 1
