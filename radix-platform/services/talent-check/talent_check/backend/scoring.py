"""
scoring.py - Layer B of Talent Check
Compares candidate skill levels against company requirements across the 12 RADIX skillsets.
Pure deterministic scoring and gap analysis (no LLM).
"""

from typing import Dict, Any, List, Optional

CATEGORIES_META = {
    "COD": "Coding",
    "DSA": "Data Structures & Algorithms",
    "OOD": "Object-Oriented Design",
    "APTI": "Aptitude & Problem Solving",
    "COMM": "Communication Skills",
    "AI": "AI Native Engineering",
    "CLOUD": "DevOps & Cloud",
    "SQL": "SQL & Design",
    "SWE": "Software Engineering",
    "SYSD": "System Design & Architecture",
    "NETW": "Computer Networking",
    "OS": "Operating Systems",
}

# Single definition of a critical gap: required_level - candidate_level >= CRITICAL_GAP_MIN.
# Role 5 reads summary.critical_categories / summary.critical_gap_min instead of re-deriving this.
# Gaps of 1..CRITICAL_GAP_MIN-1 are 'scored' gaps (partial credit downstream).
CRITICAL_GAP_MIN = 4

TIER_NAMES = {
    "CU": "Conceptual Understanding",
    "AP": "Application",
    "AS": "Analysis & Assessment",
    "EV": "Evaluation & Optimization",
    "CR": "Creation & Architecture",
}

def determine_readiness_verdict(readiness_score: int, critical_gaps_count: int) -> Dict[str, str]:
    """
    Returns high-level readiness category and description.
    """
    if readiness_score >= 88 and critical_gaps_count == 0:
        return {
            "verdict": "Ready",
            "badge_color": "success",
            "message": "Candidate meets or exceeds the company's expected bar across core competencies."
        }
    elif readiness_score >= 70 and critical_gaps_count <= 2:
        return {
            "verdict": "Close",
            "badge_color": "warning",
            "message": "Candidate is a competitive match with a few targeted skill gaps to bridge."
        }
    elif readiness_score >= 70 and critical_gaps_count > 2:
        return {
            "verdict": "Needs Work",
            "badge_color": "warning",
            "message": f"Candidate demonstrates competitive overall alignment ({readiness_score}%), but has {critical_gaps_count} critical competency gaps requiring targeted remediation."
        }
    else:
        return {
            "verdict": "Needs Work",
            "badge_color": "danger",
            "message": "Significant preparation needed in multiple foundational or high-weight areas."
        }

def score(
    candidate_levels: Dict[str, int],
    company: Dict[str, Any],
    evidence_points: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Layer B Scoring Function:
    Input:
      candidate_levels: Dict mapping 12 category codes to int (0-10)
      company: Company dict with 'company', 'id', 'skills'
      evidence_points: Optional Dict mapping 12 category codes to float raw points
    Output:
      Standard RADIX Talent Check result contract + enriched breakdown.
    """
    company_name = company.get("company", "Unknown Company")
    company_id = company.get("id")
    company_skills = company.get("skills", {})

    skillset_gap: List[Dict[str, Any]] = []
    total_weighted_ratio = 0.0
    total_weight = 0.0

    met_count = 0
    gap_count = 0
    critical_gaps = []

    for code, cat_name in CATEGORIES_META.items():
        req_info = company_skills.get(code, {})
        req_level = req_info.get("required_level", 5)
        req_tier = req_info.get("tier", "AP")
        tier_name = req_info.get("tier_name", TIER_NAMES.get(req_tier, req_tier))

        cand_level = candidate_levels.get(code, 0)
        # Ratio capped at 1.0 for score percentage
        ratio = min(cand_level / req_level, 1.0) if req_level > 0 else 1.0
        
        weight = float(req_level)
        total_weighted_ratio += ratio * weight
        total_weight += weight

        has_gap = cand_level < req_level
        gap_size = max(req_level - cand_level, 0)

        if has_gap:
            gap_count += 1
            if gap_size >= CRITICAL_GAP_MIN:
                critical_gaps.append(code)
        else:
            met_count += 1

        gap_item = {
            "category_code": code,
            "category_name": cat_name,
            "required_level": req_level,
            "required_tier": req_tier,
            "tier_name": tier_name,
            "candidate_level": cand_level,
            "gap": has_gap,
            "gap_size": gap_size,
            "ratio": round(ratio, 3),
        }
        if evidence_points is not None:
            gap_item["evidence_points"] = round(float(evidence_points.get(code, 0.0)), 2)

        skillset_gap.append(gap_item)

    # Calculate weighted readiness score
    readiness_score = int(round((total_weighted_ratio / total_weight) * 100)) if total_weight > 0 else 0
    readiness_score = max(0, min(100, readiness_score))

    verdict_info = determine_readiness_verdict(readiness_score, len(critical_gaps))

    # Priority focus areas (sorted by gap_size descending, then required_level descending)
    focus_areas = sorted(
        [item for item in skillset_gap if item["gap"]],
        key=lambda x: (x["gap_size"], x["required_level"]),
        reverse=True
    )

    return {
        # Exact contract fields required by Section 3 & 4
        "company": company_name,
        "company_id": company_id,
        "readiness_score": readiness_score,
        "skillset_gap": skillset_gap,
        
        # Enriched fields for UI presentation
        "verdict": verdict_info["verdict"],
        "verdict_badge": verdict_info["badge_color"],
        "verdict_message": verdict_info["message"],
        "summary": {
            "total_categories": len(CATEGORIES_META),
            "met_count": met_count,
            "gap_count": gap_count,
            "critical_gap_count": len(critical_gaps),
            "critical_gap_min": CRITICAL_GAP_MIN,
            "critical_categories": critical_gaps,
        },
        "focus_areas": [
            {
                "code": f["category_code"],
                "name": f["category_name"],
                "required": f["required_level"],
                "current": f["candidate_level"],
                "gap": f["gap_size"],
                "target_tier": f"{f['required_tier']} ({f['tier_name']})",
            }
            for f in focus_areas[:4]
        ]
    }
