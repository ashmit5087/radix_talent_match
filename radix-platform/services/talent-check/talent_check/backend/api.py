"""
api.py - FastAPI service for RADIX Talent Check (Role 4)
Exposes endpoints to query company skill benchmarks, mock candidate profiles,
run real-time deterministic talent checks, and audit candidate public web footprints (GitHub & LeetCode).
"""

import os
import sys
import json
import glob
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from talent_check.backend.levels import (
    get_candidate_levels,
    get_candidate_levels_with_points,
    augment_evidence_with_web_audit,
    points_to_level,
    CATEGORIES
)
from talent_check.backend.scoring import score, CATEGORIES_META, TIER_NAMES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
COMPANIES_FILE = os.path.join(DATA_DIR, "companies.json")
MOCK_DIR = os.path.join(DATA_DIR, "mock_profiles")

# Import Role 4 web-level-scrapping modules
ROLE4_ROOT = os.path.dirname(BASE_DIR)
SCRAPING_DIR = os.path.join(ROLE4_ROOT, "web-level-scrapping")
if SCRAPING_DIR not in sys.path:
    sys.path.insert(0, SCRAPING_DIR)

try:
    from github_scraper import GitHubScraper
    from leetcode_scraper import LeetCodeScraper
    from skill_matcher import SkillMatcher
    SCRAPING_AVAILABLE = True
except Exception as e:
    print(f"Warning: web-level-scrapping not loaded: {e}")
    SCRAPING_AVAILABLE = False


def clean_handle(val: Optional[str]) -> Optional[str]:
    """
    Cleans raw handles or full URLs (e.g. 'https://github.com/torvalds' -> 'torvalds')
    """
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    for prefix in [
        "https://github.com/", "http://github.com/",
        "https://www.github.com/", "http://www.github.com/",
        "https://leetcode.com/u/", "http://leetcode.com/u/",
        "https://leetcode.com/", "http://leetcode.com/",
        "https://www.leetcode.com/u/", "http://www.leetcode.com/u/",
        "https://www.leetcode.com/", "http://www.leetcode.com/",
    ]:
        if s.lower().startswith(prefix):
            s = s[len(prefix):]
            break
    s = s.strip("/").strip()
    s = s.split("?")[0].split("#")[0]
    if s.startswith("@"):
        s = s[1:]
    return s.strip() if s.strip() else None


app = FastAPI(
    title="RADIX Talent Check API",
    description="Role 4 feature: Compare candidate skill profiles against company benchmark bars across 12 skillsets",
    version="1.0.0"
)

# Enable CORS for local development and integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory company store
companies_db: List[Dict[str, Any]] = []
companies_by_id: Dict[int, Dict[str, Any]] = {}

def load_data():
    global companies_db, companies_by_id
    if os.path.exists(COMPANIES_FILE):
        with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
            companies_db = json.load(f)
            companies_by_id = {c["id"]: c for c in companies_db}
    else:
        print(f"Warning: {COMPANIES_FILE} not found. Run loader.py first.")

load_data()

class TalentCheckRequest(BaseModel):
    company_id: int = Field(..., description="Target company ID from staging_company_skill_levels")
    candidate_profile: Optional[Dict[str, Any]] = Field(None, description="Full candidate profile JSON (from Role 3)")
    candidate_id: Optional[str] = Field(None, description="Key of built-in mock profile (e.g. 'ananya_rao')")
    enable_web_audit: Optional[bool] = Field(False, description="Whether to include GitHub & LeetCode web footprint audit (Beta)")
    github_handle: Optional[str] = Field(None, description="GitHub username or profile URL")
    leetcode_handle: Optional[str] = Field(None, description="LeetCode username or profile URL")

class DirectScoreRequest(BaseModel):
    company_id: int
    skill_levels: Dict[str, int] = Field(..., description="Dict of category codes to levels (1-10)")

class WebAuditRequest(BaseModel):
    github_handle: Optional[str] = None
    leetcode_handle: Optional[str] = None
    claimed_skills: Optional[List[Any]] = Field(default_factory=list)
    claimed_projects: Optional[List[Any]] = Field(default_factory=list)

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "company_count": len(companies_db),
        "available_categories": list(CATEGORIES_META.keys()),
        "scraping_available": SCRAPING_AVAILABLE
    }

@app.get("/api/categories")
def get_categories():
    return [
        {
            "code": code,
            "name": name,
            "tier_guide": TIER_NAMES
        }
        for code, name in CATEGORIES_META.items()
    ]

@app.get("/api/companies")
def list_companies(
    q: Optional[str] = Query(None, description="Search company name"),
    limit: int = Query(300, ge=1, le=1000)
):
    if not q:
        filtered = companies_db[:limit]
    else:
        query_lower = q.lower().strip()
        filtered = [c for c in companies_db if query_lower in c["company"].lower()][:limit]

    return [
        {
            "id": c["id"],
            "company": c["company"],
            "skills": c.get("skills", {})
        }
        for c in filtered
    ]

@app.get("/api/companies/{company_id}")
def get_company(company_id: int):
    if company_id not in companies_by_id:
        raise HTTPException(status_code=404, detail=f"Company ID {company_id} not found")
    return companies_by_id[company_id]

@app.get("/api/candidates")
def list_mock_candidates():
    candidates = []
    for filepath in sorted(glob.glob(os.path.join(MOCK_DIR, "*.json"))):
        cid = os.path.splitext(os.path.basename(filepath))[0]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                candidates.append({
                    "id": cid,
                    "name": data.get("name", cid),
                    "headline": data.get("headline", ""),
                    "education": data.get("education", ""),
                    "preferred_roles": data.get("preferred_roles", []),
                    "skill_levels": data.get("skill_levels", {}),
                    "full_profile": data
                })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    return candidates

@app.post("/api/talent-check")
def run_talent_check(payload: TalentCheckRequest):
    # 1. Resolve company
    company = companies_by_id.get(payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company ID {payload.company_id} not found")

    # 2. Resolve candidate profile
    profile = payload.candidate_profile
    if not profile and payload.candidate_id:
        mock_path = os.path.join(MOCK_DIR, f"{payload.candidate_id}.json")
        if not os.path.exists(mock_path):
            raise HTTPException(status_code=404, detail=f"Mock candidate '{payload.candidate_id}' not found")
        with open(mock_path, "r", encoding="utf-8") as f:
            profile = json.load(f)

    if not profile:
        raise HTTPException(status_code=400, detail="Either 'candidate_profile' or 'candidate_id' must be provided")

    # 3. Layer A: extract candidate levels using evidence points & saturating curve
    candidate_levels, evidence_points = get_candidate_levels_with_points(profile)

    web_audit_result = None
    if payload.enable_web_audit and SCRAPING_AVAILABLE:
        gh_clean = clean_handle(payload.github_handle)
        lc_clean = clean_handle(payload.leetcode_handle)

        claimed_skills = []
        for s in profile.get("skills", []):
            if isinstance(s, dict):
                sname = s.get("skill_name") or s.get("name") or s.get("skill") or ""
                if sname:
                    claimed_skills.append(sname)
            elif isinstance(s, str) and s:
                claimed_skills.append(s)

        claimed_projects = profile.get("projects", [])

        gh_data = {}
        lc_data = {}

        if gh_clean:
            try:
                gh_data = GitHubScraper().audit_user(
                    gh_clean,
                    claimed_skills=claimed_skills,
                    claimed_projects=claimed_projects
                )
            except Exception as e:
                gh_data = {"username": gh_clean, "exists": False, "error": str(e)}

        if lc_clean:
            try:
                lc_data = LeetCodeScraper().audit_user(
                    lc_clean,
                    claimed_skills=claimed_skills
                )
            except Exception as e:
                lc_data = {"username": lc_clean, "exists": False, "error": str(e)}

        if gh_data or lc_data:
            match_eval = SkillMatcher.evaluate_candidate(
                claimed_skills=claimed_skills,
                claimed_projects=claimed_projects,
                github_data=gh_data,
                leetcode_data=lc_data
            )
            web_audit_payload = {
                "github": gh_data,
                "leetcode": lc_data,
                "audit": match_eval
            }
            # Augment candidate evidence points with verified public footprint!
            evidence_points = augment_evidence_with_web_audit(evidence_points, web_audit_payload)
            # Recompute candidate levels based on augmented evidence points
            candidate_levels = {cat: points_to_level(evidence_points[cat]) for cat in CATEGORIES}

            web_audit_result = {
                "enabled": True,
                "github_handle": gh_clean,
                "leetcode_handle": lc_clean,
                "composite_reality_score": match_eval.get("composite_reality_score", 0),
                "candidate_level": match_eval.get("candidate_level", 0.0),
                "level_designation": match_eval.get("level_designation", ""),
                "level_explanation": match_eval.get("level_explanation", ""),
                "sub_scores": match_eval.get("sub_scores", {}),
                "skills_breakdown": match_eval.get("skills_breakdown", {}),
                "github_summary": match_eval.get("github_summary", {}),
                "leetcode_summary": match_eval.get("leetcode_summary", {})
            }

    # 4. Layer B: score against company
    result = score(candidate_levels, company, evidence_points=evidence_points)

    result["candidate_name"] = profile.get("name", "Candidate")
    result["candidate_headline"] = profile.get("headline", "")
    result["candidate_levels"] = candidate_levels
    result["evidence_points"] = evidence_points
    if web_audit_result:
        result["web_audit"] = web_audit_result

    return result

@app.post("/api/talent-check/direct")
def run_direct_talent_check(payload: DirectScoreRequest):
    company = companies_by_id.get(payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company ID {payload.company_id} not found")

    result = score(payload.skill_levels, company)
    result["candidate_name"] = "Interactive Simulation"
    result["candidate_levels"] = payload.skill_levels
    return result

@app.post("/api/audit/web-footprint")
def audit_web_footprint(payload: WebAuditRequest):
    gh_clean = clean_handle(payload.github_handle)
    lc_clean = clean_handle(payload.leetcode_handle)

    if not gh_clean and not lc_clean:
        raise HTTPException(status_code=400, detail="Provide at least one of github_handle or leetcode_handle")

    claimed_skills = []
    for s in (payload.claimed_skills or []):
        if isinstance(s, dict):
            sname = s.get("skill_name") or s.get("name") or s.get("skill") or ""
            if sname:
                claimed_skills.append(sname)
        elif isinstance(s, str) and s:
            claimed_skills.append(s)

    claimed_projects = payload.claimed_projects or []

    gh_data = {}
    lc_data = {}

    if gh_clean:
        try:
            gh_data = GitHubScraper().audit_user(
                gh_clean,
                claimed_skills=claimed_skills,
                claimed_projects=claimed_projects
            )
        except Exception as e:
            gh_data = {"username": gh_clean, "exists": False, "error": str(e)}

    if lc_clean:
        try:
            lc_data = LeetCodeScraper().audit_user(
                lc_clean,
                claimed_skills=claimed_skills
            )
        except Exception as e:
            lc_data = {"username": lc_clean, "exists": False, "error": str(e)}

    match_evaluation = SkillMatcher.evaluate_candidate(
        claimed_skills=claimed_skills,
        claimed_projects=claimed_projects,
        github_data=gh_data,
        leetcode_data=lc_data
    )

    return {
        "github": gh_data,
        "leetcode": lc_data,
        "audit": match_evaluation
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("talent_check.backend.api:app", host="0.0.0.0", port=8000, reload=True)
