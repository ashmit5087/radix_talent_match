# Web-Level Skill Scraper & Candidate Level Evaluator

A standalone, pure command-line Python tool that audits developer technical skills against public **GitHub** and **LeetCode** footprints. It calculates a strict corporate engineering level between **0.0 and 10.0**.

Zero frontend dependencies. Easily portable into other backend services, recruiting workflows, and assessment pipelines.

---

## 1. Features

- **GitHub Scraper (`github_scraper.py`)**:
  - **Anti-Fork Auditing**: Segregates original authored repositories from cloned/forked code.
  - Inspects language distribution, authored commits, commit recency (past 365 days), and repository stars.
  - Cross-references technical skills and claimed projects against public code proof.
- **LeetCode Scraper (`leetcode_scraper.py`)**:
  - Queries official LeetCode GraphQL API endpoint (`https://leetcode.com/graphql`).
  - Extracts total solved problems with Easy / Medium / Hard difficulty counts.
  - Queries global ranking, contest ratings, contest percentiles, and programming languages used.
- **Skill Matcher & Corporate Leveling (`skill_matcher.py`)**:
  - Classifies skills into **Verified**, **Unverified Claims**, and **Bonus Discovered**.
  - Applies strict company leveling guardrails: returns a standardized level between **0.0 and 10.0**.
- **CLI Runner (`cli.py`)**:
  - Supports file-based audits (single candidate or batch array).
  - Supports CLI flag overrides and interactive terminal mode.
  - Exports structured results to JSON.

---

## 2. Strict Company Leveling Rubric (0.0 – 10.0)

| Level Scale | Company Designation | Requirements & Signal |
| :--- | :--- | :--- |
| **0.0 – 1.4** | **L0 - Trainee / Unverified** | No verifiable public repositories or under 50 LeetCode problems solved. Technical claims lack public corroboration. |
| **1.5 – 2.9** | **L1 - Junior Software Engineer** | Basic code syntax familiarity. Trivial/academic codebases or primarily Easy LeetCode solutions. Low corroboration ratio (<35%). |
| **3.0 – 4.9** | **L2 - Mid-Level Software Engineer (SDE II)** | Multi-repo original contributions, active commits over the past year, solid Medium problem solving competence, and >50% verified skills. |
| **5.0 – 6.9** | **L3 - Senior Software Engineer (Senior SDE)** | Demonstrable architectural breadth. At least 3 original maintained repositories, 40+ Medium/Hard LeetCode solutions (or contest rating >1600), >60% skill corroboration. |
| **7.0 – 8.4** | **L4 - Staff Software Engineer** | High-impact codebases with community validation (stars), broad language breadth, 120+ Medium/Hard problems (or contest rating >1800), active recency. |
| **8.5 – 9.4** | **L5 - Principal Software Engineer** | Deep distributed systems footprint, recognized open-source architectures (20+ stars), top-tier algorithmic problem solving competence. |
| **9.5 – 10.0** | **L6+ - Distinguished / Fellow Engineer** | Exceptional industry-grade open-source repositories with broad adoption and elite algorithmic mastery (Guardian / top 1-2%). |

### Strict Anti-Inflation Guardrails
- **Fork Collector Cap**: Candidates with 0 original repos (only forked templates) are capped at **2.0 max**.
- **Resume Fluff Cap**: Candidates claiming 5+ skills with under 30% corroboration are capped at **3.5 max**.
- **Senior Gate**: Reaching Level >= 5.0 strictly requires proven original repos + verified Medium/Hard algorithmic solutions.

---

## 3. Installation

```bash
cd web-level-scrapping
pip install -r requirements.txt
```

*(Optional)* To increase GitHub API rate limits from 60 requests/hour to 5,000 requests/hour:
```bash
cp .env.example .env
# Add your GitHub Personal Access Token to .env:
# GITHUB_TOKEN=ghp_your_token_here
```

---

## 4. CLI Usage

### A. Audit from a Parsed Resumes JSON File
```bash
# Run batch audit on sample file
python cli.py --input sample_parsed_resumes.json

# Export structured results to an output JSON file
python cli.py --input sample_parsed_resumes.json --output audit_results.json
```

### B. Override / Specify Usernames Manually
```bash
python cli.py --input single_candidate.json --github torvalds --leetcode neetcode
```

### C. Interactive Terminal Mode
```bash
python cli.py
# Prompts for file path or manual candidate details directly in terminal
```

---

## 5. Input JSON Format

The tool accepts either a single candidate JSON object or a list of candidate objects:

```json
[
  {
    "name": "Alex Chen",
    "email": "alex.chen@example.com",
    "github_username": "alexchen-dev",
    "leetcode_username": "alexchen_code",
    "technical_skills": [
      "TypeScript", "Go", "Python", "React", "Docker", "PostgreSQL", "Redis"
    ],
    "projects": [
      {
        "name": "CloudMesh",
        "description": "High-throughput traffic controller in Go and Docker"
      }
    ]
  }
]
```

---

## 6. How to Integrate into Another Project (Python API)

You can import the scrapers directly into any other Python application or backend service:

```python
from github_scraper import GitHubScraper
from leetcode_scraper import LeetCodeScraper
from skill_matcher import SkillMatcher

# 1. Initialize scrapers
gh_scraper = GitHubScraper(token="your_optional_github_token")
lc_scraper = LeetCodeScraper()

# 2. Extract candidate data from your parsed resume
claimed_skills = ["Python", "Go", "Docker", "PostgreSQL", "React"]
claimed_projects = [{"name": "CloudMesh"}]

# 3. Scrape footprints
github_data = gh_scraper.audit_user("alexchen-dev", claimed_skills, claimed_projects)
leetcode_data = lc_scraper.audit_user("alexchen_code", claimed_skills)

# 4. Evaluate candidate level (0.0 - 10.0)
result = SkillMatcher.evaluate_candidate(
    claimed_skills=claimed_skills,
    claimed_projects=claimed_projects,
    github_data=github_data,
    leetcode_data=leetcode_data
)

print(f"Candidate Level: {result['candidate_level']} / 10.0")
print(f"Designation:     {result['level_designation']}")
print(f"Verified Skills: {result['skills_breakdown']['verified_skills']}")
print(f"Unverified:      {result['skills_breakdown']['unverified_skills']}")
```
