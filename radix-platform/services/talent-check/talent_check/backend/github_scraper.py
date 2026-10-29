import os
import requests
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone

GITHUB_API_URL = "https://api.github.com"


class GitHubScraper:
    """
    Queries public GitHub profiles and audits repositories:
    - Filters original authored repositories from forked/cloned code
    - Analyzes language frequency, commit recency, stars, and contribution activity
    - Cross-references claimed technical skills and projects against public code proof
    """

    def __init__(self, token: str = None):
        self.token = token or os.getenv("GITHUB_TOKEN")

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def audit_user(self, username: str, claimed_skills: List[str] = None, claimed_projects: List[Any] = None) -> Dict[str, Any]:
        """
        Deep code audit for a candidate GitHub handle.
        """
        claimed_skills = claimed_skills or []
        claimed_projects = claimed_projects or []

        result = {
            "username": username,
            "exists": False,
            "total_repos": 0,
            "original_repos": [],
            "forked_repos": [],
            "total_stars": 0,
            "recent_active_repos": [],
            "languages": {},
            "verified_skills": [],
            "verified_projects": [],
            "proof": {"skills": {}, "projects": {}},
            "score": 0.0,
            "error": None
        }

        if not username:
            result["error"] = "No GitHub username provided"
            return result

        try:
            # 1. Fetch repositories
            repos = self._get_repositories(username)
            if repos is None:
                result["error"] = f"User '{username}' not found on GitHub"
                return result

            result["exists"] = True
            result["total_repos"] = len(repos)

            # 2. Anti-Fork Codebase Segregation
            now = datetime.now(timezone.utc)
            original_repos = []
            forked_repos = []
            total_stars = 0
            recent_active = []

            for repo in repos:
                name = repo.get("name", "")
                is_fork = repo.get("fork", False)
                stars = repo.get("stargazers_count", 0)
                pushed_at_str = repo.get("pushed_at")

                if is_fork:
                    forked_repos.append(name)
                else:
                    original_repos.append(name)
                    total_stars += stars
                    if pushed_at_str:
                        try:
                            pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                            if (now - pushed_at).days <= 365:
                                recent_active.append(name)
                        except Exception:
                            pass

            result["original_repos"] = original_repos
            result["forked_repos"] = forked_repos
            result["total_stars"] = total_stars
            result["recent_active_repos"] = recent_active

            # 3. Detect primary and repo languages
            languages = self._extract_languages(repos)
            result["languages"] = languages

            # 4. Verify Technical Skills against repositories
            verified_skills, skill_proof = self._verify_skills(claimed_skills, repos, languages)
            result["verified_skills"] = verified_skills
            result["proof"]["skills"] = skill_proof

            # 5. Verify Claimed Projects
            verified_projects, project_proof = self._verify_projects(claimed_projects, repos)
            result["verified_projects"] = verified_projects
            result["proof"]["projects"] = project_proof

            # 6. GitHub Authenticity & Architecture Score (0 - 100)
            # Strict corporate rubric:
            # - Original repositories: max 30 pts (requires genuine authored code, not clones)
            # - Language breadth / depth: max 25 pts
            # - Active maintenance / recency (last 365 days): max 20 pts
            # - Community validation (stars on original work): max 15 pts
            # - Repo count / velocity: max 10 pts
            repo_pts = min(30.0, len(original_repos) * 6.0)
            lang_pts = min(25.0, len(languages) * 5.0)
            recency_pts = min(20.0, len(recent_active) * 5.0)
            star_pts = min(15.0, total_stars * 3.0)
            velocity_pts = min(10.0, len(original_repos) * 2.0)

            result["score"] = round(min(100.0, repo_pts + lang_pts + recency_pts + star_pts + velocity_pts), 1)
            return result

        except Exception as e:
            result["error"] = str(e)
            return result

    def _get_repositories(self, username: str) -> List[Dict[str, Any]]:
        all_repos = []
        page = 1
        per_page = 100

        while True:
            url = f"{GITHUB_API_URL}/users/{username}/repos?per_page={per_page}&page={page}&sort=pushed"
            try:
                resp = requests.get(url, headers=self._get_headers(), timeout=12)
                if resp.status_code == 404:
                    return None
                if resp.status_code != 200:
                    break

                repos = resp.json()
                if not repos or not isinstance(repos, list):
                    break

                all_repos.extend(repos)
                if len(repos) < per_page:
                    break
                page += 1
            except Exception:
                break

        return all_repos

    def _extract_languages(self, repos: List[Dict[str, Any]]) -> Dict[str, int]:
        lang_counts = {}
        for r in repos:
            lang = r.get("language")
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        return lang_counts

    def _verify_skills(self, skills: List[str], repos: List[Dict[str, Any]], languages: Dict[str, int]) -> Tuple[List[str], Dict[str, Any]]:
        verified = []
        proof = {}

        skill_synonyms = {
            "python": ["python", "django", "flask", "fastapi", "pandas", "numpy", "pytorch", "tensorflow", "py"],
            "javascript": ["javascript", "js", "node", "nodejs", "react", "vue", "angular", "express"],
            "typescript": ["typescript", "ts", "react", "next.js", "nextjs", "angular", "node"],
            "react": ["react", "next.js", "nextjs", "jsx", "tsx", "redux"],
            "node.js": ["node", "nodejs", "express", "nest", "nestjs", "fastify"],
            "go": ["go", "golang", "gin", "fiber", "gorilla"],
            "golang": ["go", "golang", "gin", "fiber"],
            "rust": ["rust", "cargo", "actix", "tokio"],
            "c++": ["c++", "cpp", "cmake"],
            "c": ["c", "cmake", "make"],
            "c#": ["c#", "csharp", ".net", "dotnet"],
            "java": ["java", "spring", "springboot", "maven", "gradle"],
            "kotlin": ["kotlin", "android"],
            "swift": ["swift", "ios", "swiftui"],
            "sql": ["sql", "mysql", "postgresql", "postgres", "sqlite"],
            "postgresql": ["postgresql", "postgres", "psql"],
            "mysql": ["mysql"],
            "mongodb": ["mongodb", "mongo", "mongoose"],
            "redis": ["redis"],
            "docker": ["docker", "dockerfile", "container"],
            "kubernetes": ["kubernetes", "k8s", "helm"],
            "aws": ["aws", "s3", "lambda", "ec2", "dynamodb", "cloudformation", "terraform"],
            "git": ["git", "github"],
            "github": ["git", "github"],
            "html": ["html", "html5"],
            "css": ["css", "css3", "sass", "scss", "tailwind", "tailwindcss"]
        }

        # Repos texts for semantic scanning
        repo_texts = []
        for r in repos:
            repo_name = r.get("name", "").lower()
            desc = (r.get("description") or "").lower()
            topics = [t.lower() for t in r.get("topics", [])]
            repo_lang = (r.get("language") or "").lower()
            is_fork = r.get("fork", False)

            combined = f"{repo_name} {desc} {' '.join(topics)} {repo_lang}"
            repo_texts.append({"name": r.get("name"), "text": combined, "is_fork": is_fork, "lang": r.get("language")})

        detected_langs = {k.lower(): k for k in languages.keys()}

        for raw_skill in skills:
            skill = raw_skill.strip()
            skill_lower = skill.lower()
            matched = False
            matching_repos = []

            # A. Direct language match
            if skill_lower in detected_langs:
                matched = True
                real_lang = detected_langs[skill_lower]
                repos_using_lang = [r.get("name") for r in repos if (r.get("language") or "").lower() == skill_lower and not r.get("fork")]
                matching_repos.extend(repos_using_lang)
                proof[skill] = f"Authored code in {real_lang} across {languages.get(real_lang, 0)} repositories"

            # B. Check synonyms in repo metadata and topics
            syns = skill_synonyms.get(skill_lower, [skill_lower])
            for syn in syns:
                for r in repo_texts:
                    # Require word boundary to avoid substring false positives
                    if re.search(r'\b' + re.escape(syn) + r'\b', r["text"]):
                        matched = True
                        if r["name"] not in matching_repos:
                            matching_repos.append(r["name"])

            if matched:
                verified.append(skill)
                if skill not in proof:
                    orig_matching = [m for m in matching_repos if m in [r["name"] for r in repo_texts if not r["is_fork"]]]
                    if orig_matching:
                        proof[skill] = f"Found in original repositories: {', '.join(orig_matching[:3])}"
                    else:
                        proof[skill] = f"Found in candidate repositories: {', '.join(matching_repos[:3])}"

        return verified, proof

    def _verify_projects(self, projects: List[Any], repos: List[Dict[str, Any]]) -> Tuple[List[str], Dict[str, Any]]:
        verified = []
        proof = {}

        for p in projects:
            proj_name = p.get("name", "") if isinstance(p, dict) else str(p)
            if not proj_name:
                continue

            clean_name = re.sub(r'[^a-zA-Z0-9]', '', proj_name.lower())
            matched_repo = None

            for r in repos:
                repo_name = re.sub(r'[^a-zA-Z0-9]', '', r.get("name", "").lower())
                desc = (r.get("description") or "").lower()

                if clean_name in repo_name or repo_name in clean_name:
                    matched_repo = r
                    break
                elif proj_name.lower() in desc:
                    matched_repo = r
                    break

            if matched_repo:
                verified.append(proj_name)
                is_fork = matched_repo.get("fork", False)
                proof[proj_name] = {
                    "matched_repo": matched_repo.get("name"),
                    "url": matched_repo.get("html_url"),
                    "stars": matched_repo.get("stargazers_count", 0),
                    "is_original": not is_fork
                }

        return verified, proof
