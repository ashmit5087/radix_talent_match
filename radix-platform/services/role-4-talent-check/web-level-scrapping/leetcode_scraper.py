import requests
from typing import Dict, Any, List, Optional

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

LANGUAGE_ALIASES = {
    "python": ["python", "python3", "pandas"],
    "python3": ["python", "python3"],
    "c++": ["c++", "cpp"],
    "cpp": ["c++", "cpp"],
    "c": ["c"],
    "c#": ["c#", "csharp"],
    "csharp": ["c#", "csharp"],
    "java": ["java"],
    "javascript": ["javascript", "js", "typescript"],
    "js": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "ts": ["typescript", "ts"],
    "go": ["go", "golang"],
    "golang": ["go", "golang"],
    "rust": ["rust"],
    "sql": ["mysql", "postgresql", "ms sql server", "oracle", "sql"],
    "mysql": ["mysql", "sql"],
    "postgresql": ["postgresql", "sql"],
    "ruby": ["ruby"],
    "swift": ["swift"],
    "kotlin": ["kotlin"],
    "php": ["php"],
    "scala": ["scala"],
    "dart": ["dart"]
}


class LeetCodeScraper:
    """
    Queries the official LeetCode GraphQL API endpoint to fetch:
    - Total problems solved, broken down by Easy, Medium, and Hard
    - Global ranking, contest ratings, and contest top percentage
    - Solved programming languages
    - Cross-references DSA technical skills
    """

    def audit_user(self, username: str, claimed_skills: Optional[List[str]] = None) -> Dict[str, Any]:
        claimed_skills = claimed_skills or []

        result = {
            "username": username,
            "exists": False,
            "total_solved": 0,
            "easy_solved": 0,
            "medium_solved": 0,
            "hard_solved": 0,
            "global_ranking": None,
            "contest_rating": None,
            "top_percentage": None,
            "attended_contests": 0,
            "languages_solved": [],
            "verified_skills": [],
            "score": 0.0,
            "error": None
        }

        if not username:
            result["error"] = "No LeetCode username provided"
            return result

        query = """
        query getUserProfile($username: String!) {
          matchedUser(username: $username) {
            username
            profile {
              ranking
              reputation
            }
            submitStats {
              acSubmissionNum {
                difficulty
                count
              }
            }
            languageProblemCount {
              languageName
              problemsSolved
            }
          }
          userContestRanking(username: $username) {
            attendedContestsCount
            rating
            globalRanking
            totalParticipants
            topPercentage
          }
        }
        """

        headers = {
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            resp = requests.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": {"username": username}},
                headers=headers,
                timeout=12
            )

            if resp.status_code != 200:
                result["error"] = f"LeetCode returned HTTP {resp.status_code}"
                return result

            data = resp.json().get("data", {})
            matched_user = data.get("matchedUser")

            if not matched_user:
                result["error"] = f"LeetCode user '{username}' not found"
                return result

            result["exists"] = True

            # Extract submissions breakdown
            submit_stats = matched_user.get("submitStats", {}).get("acSubmissionNum", [])
            for item in submit_stats:
                diff = item.get("difficulty")
                count = item.get("count", 0)
                if diff == "All":
                    result["total_solved"] = count
                elif diff == "Easy":
                    result["easy_solved"] = count
                elif diff == "Medium":
                    result["medium_solved"] = count
                elif diff == "Hard":
                    result["hard_solved"] = count

            # Profile & Contest Stats
            profile = matched_user.get("profile", {})
            result["global_ranking"] = profile.get("ranking")

            contest = data.get("userContestRanking") or {}
            if contest:
                result["contest_rating"] = round(contest.get("rating", 0), 1) if contest.get("rating") else None
                result["top_percentage"] = contest.get("topPercentage")
                result["attended_contests"] = contest.get("attendedContestsCount", 0)

            # Languages solved on LeetCode
            lang_counts = matched_user.get("languageProblemCount", []) or []
            langs_solved = [l.get("languageName") for l in lang_counts if l.get("problemsSolved", 0) > 0]
            result["languages_solved"] = langs_solved

            # Cross-reference claimed technical skills
            verified_skills = []
            for skill in claimed_skills:
                if self._matches_leetcode_language(skill, langs_solved):
                    verified_skills.append(skill)
            result["verified_skills"] = verified_skills

            # Compute LeetCode DSA Problem Solving Score (0 - 100)
            # Strict corporate rubric:
            # - Easy problems: up to 10 pts (capped, low engineering signal)
            # - Medium problems: up to 45 pts (core industry interview benchmark)
            # - Hard problems: up to 30 pts (advanced algorithmic depth)
            # - Contest performance / rating: up to 15 pts
            easy_pts = min(10.0, result["easy_solved"] * 0.1)
            medium_pts = min(45.0, result["medium_solved"] * 0.3)
            hard_pts = min(30.0, result["hard_solved"] * 0.8)

            contest_pts = 0.0
            if result["contest_rating"]:
                if result["contest_rating"] >= 2100:  # Top ~1-2% Guardian
                    contest_pts = 15.0
                elif result["contest_rating"] >= 1850:  # Top ~5-8% Knight
                    contest_pts = 12.0
                elif result["contest_rating"] >= 1650:  # Above average
                    contest_pts = 8.0
                else:
                    contest_pts = 4.0
            elif result["total_solved"] >= 200:
                contest_pts = 5.0

            result["score"] = round(min(100.0, easy_pts + medium_pts + hard_pts + contest_pts), 1)
            return result

        except Exception as e:
            result["error"] = str(e)
            return result

    def _matches_leetcode_language(self, skill: str, solved_langs: List[str]) -> bool:
        s_clean = skill.strip().lower()
        solved_clean = [l.strip().lower() for l in solved_langs]

        if s_clean in solved_clean:
            return True

        aliases = LANGUAGE_ALIASES.get(s_clean, [s_clean])
        for a in aliases:
            for sl in solved_clean:
                if a == sl or a in sl or sl in a:
                    return True
        return False
