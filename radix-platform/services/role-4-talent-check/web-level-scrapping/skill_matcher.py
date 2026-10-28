from typing import Dict, Any, List, Tuple


class SkillMatcher:
    """
    Cross-references candidate resume claims against GitHub and LeetCode signals.
    Calculates verification metrics and strict corporate candidate engineering levels (0.0 - 10.0).
    """

    @staticmethod
    def evaluate_candidate(
        claimed_skills: List[str],
        claimed_projects: List[Any],
        github_data: Dict[str, Any],
        leetcode_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Normalize skills whether provided as strings or dicts (e.g. {"skill_name": "..."})
        normalized_skills = []
        for s in claimed_skills:
            if isinstance(s, str) and s.strip():
                normalized_skills.append(s.strip())
            elif isinstance(s, dict):
                sname = s.get("skill_name") or s.get("name") or s.get("skill") or ""
                if isinstance(sname, str) and sname.strip():
                    normalized_skills.append(sname.strip())
        claimed_skills = normalized_skills

        # 1. Gather all verified technical skills
        gh_verified = set(github_data.get("verified_skills", []))
        lc_verified = set(leetcode_data.get("verified_skills", []))
        all_verified_set = gh_verified.union(lc_verified)

        verified_skills = [s for s in claimed_skills if s in all_verified_set]
        unverified_skills = [s for s in claimed_skills if s not in all_verified_set]

        # 2. Identify bonus skills present in codebases/LeetCode but NOT claimed on resume
        gh_languages = set(github_data.get("languages", {}).keys())
        lc_languages = set(leetcode_data.get("languages_solved", []))
        active_ecosystem_skills = gh_languages.union(lc_languages)

        claimed_lower = {s.lower() for s in claimed_skills}
        bonus_skills = [s for s in active_ecosystem_skills if s.lower() not in claimed_lower]

        # 3. Component Scores (0 - 100)
        github_score = float(github_data.get("score", 0.0))
        leetcode_score = float(leetcode_data.get("score", 0.0))

        # Skill Corroboration Score
        if claimed_skills:
            skills_score = round((len(verified_skills) / len(claimed_skills)) * 100.0, 1)
        else:
            skills_score = 50.0 if all_verified_set else 0.0

        # Project Verification Score
        verified_projects = github_data.get("verified_projects", [])
        if claimed_projects:
            projects_score = round((len(verified_projects) / len(claimed_projects)) * 100.0, 1)
        else:
            projects_score = 50.0 if github_data.get("original_repos") else 0.0

        # 4. Composite Reality Score (0 - 100)
        has_leetcode = bool(leetcode_data.get("exists") and leetcode_data.get("total_solved", 0) > 0)
        has_github = bool(github_data.get("exists"))

        if has_github and has_leetcode:
            composite_score = (
                (github_score * 0.35) +
                (skills_score * 0.30) +
                (leetcode_score * 0.20) +
                (projects_score * 0.15)
            )
        elif has_github:
            composite_score = (
                (github_score * 0.50) +
                (skills_score * 0.35) +
                (projects_score * 0.15)
            )
        elif has_leetcode:
            composite_score = (
                (leetcode_score * 0.55) +
                (skills_score * 0.45)
            )
        else:
            composite_score = 0.0

        composite_score = round(max(0.0, min(100.0, composite_score)), 1)

        # 5. Strict Corporate Candidate Level (0.0 - 10.0)
        candidate_level, level_designation, level_explanation = SkillMatcher.calculate_strict_level(
            composite_score=composite_score,
            github_data=github_data,
            leetcode_data=leetcode_data,
            skills_score=skills_score,
            claimed_skills_count=len(claimed_skills),
            verified_skills_count=len(verified_skills)
        )

        return {
            "candidate_level": candidate_level,              # float between 0.0 and 10.0
            "level_designation": level_designation,          # e.g., "L3 - Senior Software Engineer"
            "level_explanation": level_explanation,
            "composite_reality_score": composite_score,      # 0.0 - 100.0
            "sub_scores": {
                "github_authenticity": github_score,
                "leetcode_problem_solving": leetcode_score,
                "skills_corroboration": skills_score,
                "project_authenticity": projects_score
            },
            "skills_breakdown": {
                "total_claimed": len(claimed_skills),
                "total_verified": len(verified_skills),
                "verified_skills": verified_skills,
                "unverified_skills": unverified_skills,
                "bonus_discovered_skills": bonus_skills
            },
            "github_summary": {
                "exists": github_data.get("exists", False),
                "original_repos": len(github_data.get("original_repos", [])),
                "forked_repos": len(github_data.get("forked_repos", [])),
                "stars": github_data.get("total_stars", 0),
                "recent_active_repos": len(github_data.get("recent_active_repos", []))
            },
            "leetcode_summary": {
                "exists": leetcode_data.get("exists", False),
                "total_solved": leetcode_data.get("total_solved", 0),
                "easy": leetcode_data.get("easy_solved", 0),
                "medium": leetcode_data.get("medium_solved", 0),
                "hard": leetcode_data.get("hard_solved", 0),
                "contest_rating": leetcode_data.get("contest_rating")
            }
        }

    @staticmethod
    def calculate_strict_level(
        composite_score: float,
        github_data: Dict[str, Any],
        leetcode_data: Dict[str, Any],
        skills_score: float,
        claimed_skills_count: int,
        verified_skills_count: int
    ) -> Tuple[float, str, str]:
        """
        Calculates a strict candidate level between 0.0 and 10.0 based on industry benchmarks:
        - Level 0.0 - 1.4: L0 / Trainee / Unverified
        - Level 1.5 - 2.9: L1 / Junior Software Engineer (Associate / Entry-Level)
        - Level 3.0 - 4.9: L2 / Mid-Level Software Engineer (SDE II)
        - Level 5.0 - 6.9: L3 / Senior Software Engineer (Senior SDE)
        - Level 7.0 - 8.4: L4 / Staff Software Engineer
        - Level 8.5 - 9.4: L5 / Principal Software Engineer
        - Level 9.5 - 10.0: L6+ / Distinguished / Fellow Engineer

        Includes strict anti-inflation guardrails:
        - Zero original repositories caps level at 2.5 max.
        - Unverified skills > 60% caps level at 4.0 max.
        - Reaching Level >= 6.0 requires genuine original repos + verified medium/hard problem solving.
        """
        # Base raw level on 0.0 - 10.0 scale
        raw_level = composite_score / 10.0

        original_repos_count = len(github_data.get("original_repos", []))
        total_stars = github_data.get("total_stars", 0)
        recent_active = len(github_data.get("recent_active_repos", []))

        lc_solved = leetcode_data.get("total_solved", 0)
        lc_medium = leetcode_data.get("medium_solved", 0)
        lc_hard = leetcode_data.get("hard_solved", 0)
        contest_rating = leetcode_data.get("contest_rating") or 0.0

        # === STRICT COMPANY GUARDRAILS ===
        reasons = []

        # Guardrail 1: Zero original code proof
        if original_repos_count == 0 and lc_solved < 50:
            if raw_level > 1.5:
                raw_level = 1.0
                reasons.append("Capped: Zero original GitHub repositories and under 50 LeetCode problems solved.")

        # Guardrail 2: Fork collector penalty (only forks, no authored original repos)
        elif original_repos_count == 0 and len(github_data.get("forked_repos", [])) > 0:
            if raw_level > 2.0:
                raw_level = 2.0
                reasons.append("Capped at L1: Repositories are cloned/forked without verified authored original code.")

        # Guardrail 3: Poor skill corroboration (claiming many skills but proving few)
        if claimed_skills_count >= 5 and skills_score < 30.0:
            if raw_level > 3.5:
                raw_level = 3.5
                reasons.append("Capped at L2 (Low): Under 30% of claimed technical skills corroborated by public code.")

        # Guardrail 4: Prerequisites for Senior (Level >= 5.0)
        # Senior developers in top companies must have demonstrable architecture proof
        if raw_level >= 5.0:
            has_senior_code = (original_repos_count >= 3 and recent_active >= 1)
            has_senior_dsa = (lc_medium + lc_hard >= 40 or contest_rating >= 1600 or lc_solved >= 150)

            if not has_senior_code and not has_senior_dsa:
                raw_level = 4.8
                reasons.append("Senior cap: Requires at least 3 original maintained repos or 40+ Medium/Hard DSA solutions.")

        # Guardrail 5: Prerequisites for Staff (Level >= 7.0)
        # Staff engineers require public recognition (stars/impact) and deep verification
        if raw_level >= 7.0:
            has_staff_code = (original_repos_count >= 5 and total_stars >= 5 and recent_active >= 2)
            has_staff_dsa = (lc_medium + lc_hard >= 120 or contest_rating >= 1800 or lc_solved >= 300)

            if not (has_staff_code and has_staff_dsa) and not (total_stars >= 50):
                raw_level = 6.8
                reasons.append("Staff cap: Requires community validation (stars), active maintenance, and high DSA rigor.")

        # Guardrail 6: Principal / Distinguished (Level >= 8.5)
        if raw_level >= 8.5:
            if total_stars < 20 and lc_solved < 500 and contest_rating < 2000:
                raw_level = 8.2
                reasons.append("Principal cap: Requires exceptional open-source impact (20+ stars) or Guardian/top-tier DSA proof.")

        final_level = round(max(0.0, min(10.0, raw_level)), 1)

        # Company designation mapping
        if final_level >= 9.5:
            designation = "L6+ - Distinguished / Fellow Engineer"
            desc = "Exceptional industry-grade architectural footprint, viral open-source repositories, and elite algorithmic mastery."
        elif final_level >= 8.5:
            designation = "L5 - Principal Software Engineer"
            desc = "Deep distributed systems proof, recognized open-source architectures, and advanced problem-solving competence."
        elif final_level >= 7.0:
            designation = "L4 - Staff Software Engineer"
            desc = "High-impact codebase ownership, community validation, broad technical breadth, and verified senior DSA competence."
        elif final_level >= 5.0:
            designation = "L3 - Senior Software Engineer"
            desc = "Proven original repositories, strong commit recency, solid medium/hard algorithmic problem solving, and high skill corroboration."
        elif final_level >= 3.0:
            designation = "L2 - Mid-Level Software Engineer"
            desc = "Consistent multi-repo original contributions, solid functional problem solving, and verifiable working knowledge of core stack."
        elif final_level >= 1.5:
            designation = "L1 - Junior Software Engineer"
            desc = "Basic code syntax and foundational repository footprint. Trivial or academic codebases with limited public corroboration."
        else:
            designation = "L0 - Trainee / Unverified"
            desc = "Insufficient public code proof or unverified accounts. Skills lack public repository corroboration."

        if reasons:
            explanation = f"{desc} [{' | '.join(reasons)}]"
        else:
            explanation = desc

        return final_level, designation, explanation
