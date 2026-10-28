"""
api.py - FastAPI service for RADIX Talent Check (Role 4)
Exposes endpoints to query company skill benchmarks, mock candidate profiles,
and run real-time deterministic talent checks.
"""

import os
import json
import glob
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from talent_check.backend.levels import get_candidate_levels, get_candidate_levels_with_points, CATEGORIES
from talent_check.backend.scoring import score, CATEGORIES_META, TIER_NAMES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
COMPANIES_FILE = os.path.join(DATA_DIR, "companies.json")
MOCK_DIR = os.path.join(DATA_DIR, "mock_profiles")

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

class DirectScoreRequest(BaseModel):
    company_id: int
    skill_levels: Dict[str, int] = Field(..., description="Dict of category codes to levels (1-10)")

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "company_count": len(companies_db),
        "available_categories": list(CATEGORIES_META.keys())
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
    limit: int = Query(120, ge=1, le=200)
):
    if not q:
        filtered = companies_db[:limit]
    else:
        query_lower = q.lower().strip()
        filtered = [c for c in companies_db if query_lower in c["company"].lower()][:limit]

    # Return summary format for dropdowns and lists
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
        # Load from mock profiles
        mock_path = os.path.join(MOCK_DIR, f"{payload.candidate_id}.json")
        if not os.path.exists(mock_path):
            raise HTTPException(status_code=404, detail=f"Mock candidate '{payload.candidate_id}' not found")
        with open(mock_path, "r", encoding="utf-8") as f:
            profile = json.load(f)

    if not profile:
        raise HTTPException(status_code=400, detail="Either 'candidate_profile' or 'candidate_id' must be provided")

    # 3. Layer A: extract or derive candidate levels using evidence points & saturating curve
    candidate_levels, evidence_points = get_candidate_levels_with_points(profile)

    # 4. Layer B: score against company
    result = score(candidate_levels, company, evidence_points=evidence_points)

    # Attach candidate metadata for response presentation
    result["candidate_name"] = profile.get("name", "Candidate")
    result["candidate_headline"] = profile.get("headline", "")
    result["candidate_levels"] = candidate_levels
    result["evidence_points"] = evidence_points

    return result

@app.post("/api/talent-check/direct")
def run_direct_talent_check(payload: DirectScoreRequest):
    """
    Direct simulation endpoint for testing or client integrations.
    Allows candidates or evaluators to test hypothetical skill levels (1-10) and see immediate readiness impact.
    """
    company = companies_by_id.get(payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company ID {payload.company_id} not found")

    result = score(payload.skill_levels, company)
    result["candidate_name"] = "Interactive Simulation"
    result["candidate_levels"] = payload.skill_levels
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("talent_check.backend.api:app", host="0.0.0.0", port=8000, reload=True)
