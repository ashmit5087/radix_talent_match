import os
import sys
import json
import argparse
from typing import List, Dict, Any

# Ensure local imports work regardless of execution directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Optional dotenv loading
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from github_scraper import GitHubScraper
from leetcode_scraper import LeetCodeScraper
from skill_matcher import SkillMatcher


def render_level_bar(level: float, max_level: float = 10.0, bar_len: int = 20) -> str:
    """Renders a visual terminal level bar."""
    filled_len = int(round(bar_len * (level / max_level)))
    filled_len = max(0, min(bar_len, filled_len))
    bar = "=" * filled_len + "-" * (bar_len - filled_len)
    return f"[{bar}] {level:.1f} / {max_level:.1f}"


def format_candidate_report(result: Dict[str, Any], candidate_name: str = "Candidate") -> str:
    """Formats the audit evaluation into a clean, professional terminal report."""
    lvl = result["candidate_level"]
    designation = result["level_designation"]
    reality = result["composite_reality_score"]
    sub = result["sub_scores"]
    skills = result["skills_breakdown"]
    gh = result["github_summary"]
    lc = result["leetcode_summary"]

    lines = []
    lines.append("=" * 72)
    lines.append(f" CANDIDATE AUDIT REPORT: {candidate_name.upper()}")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"  COMPANY LEVEL:       {render_level_bar(lvl)}")
    lines.append(f"  DESIGNATION:         {designation}")
    lines.append(f"  REALITY SCORE:       {reality:.1f} / 100")
    lines.append("")
    lines.append(f"  Level Assessment:    {result['level_explanation']}")
    lines.append("")
    lines.append("-" * 72)
    lines.append(" COMPONENT SUB-SCORES (0 - 100)")
    lines.append("-" * 72)
    lines.append(f"  • GitHub Code Authenticity:     {sub['github_authenticity']:5.1f} / 100  ({gh['original_repos']} original repos, {gh['stars']} stars)")
    lines.append(f"  • LeetCode Problem Solving:     {sub['leetcode_problem_solving']:5.1f} / 100  ({lc['total_solved']} solved: {lc['medium']} Med, {lc['hard']} Hard)")
    lines.append(f"  • Skill Corroboration Ratio:    {sub['skills_corroboration']:5.1f} / 100  ({skills['total_verified']}/{skills['total_claimed']} skills verified)")
    lines.append(f"  • Project Codebase Match:       {sub['project_authenticity']:5.1f} / 100")
    lines.append("")
    lines.append("-" * 72)
    lines.append(" TECHNICAL SKILL BREAKDOWN")
    lines.append("-" * 72)

    if skills["verified_skills"]:
        lines.append(f"  [+] VERIFIED SKILLS ({len(skills['verified_skills'])}):")
        lines.append(f"      {', '.join(skills['verified_skills'])}")
    else:
        lines.append("  [!] VERIFIED SKILLS: None backed by public repository or LeetCode proof")

    if skills["unverified_skills"]:
        lines.append(f"  [-] UNVERIFIED CLAIMS ({len(skills['unverified_skills'])}):")
        lines.append(f"      {', '.join(skills['unverified_skills'])}")

    if skills["bonus_discovered_skills"]:
        lines.append(f"  [*] BONUS DISCOVERED ({len(skills['bonus_discovered_skills'])}):")
        lines.append(f"      {', '.join(skills['bonus_discovered_skills'][:10])}")

    lines.append("")
    lines.append("=" * 72)
    return "\n".join(lines)


def process_candidate(
    candidate: Dict[str, Any],
    gh_scraper: GitHubScraper,
    lc_scraper: LeetCodeScraper,
    cli_github: str = None,
    cli_leetcode: str = None
) -> Dict[str, Any]:
    """Evaluates a single parsed candidate dictionary."""
    name = candidate.get("name") or candidate.get("candidate_name")
    if not name:
        src = candidate.get("source_file", "")
        if src:
            name = os.path.splitext(os.path.basename(src))[0]
        else:
            name = "Candidate"

    raw_skills = candidate.get("technical_skills") or candidate.get("skills") or []
    skills = []
    for s in raw_skills:
        if isinstance(s, str) and s.strip():
            skills.append(s.strip())
        elif isinstance(s, dict):
            sname = s.get("skill_name") or s.get("name") or s.get("skill") or ""
            if isinstance(sname, str) and sname.strip():
                skills.append(sname.strip())

    projects = candidate.get("projects") or []

    # Username resolution priority: CLI argument > JSON field
    github_user = cli_github or candidate.get("github_username") or candidate.get("github")
    leetcode_user = cli_leetcode or candidate.get("leetcode_username") or candidate.get("leetcode")

    print(f"\n>> Auditing {name}...")
    if github_user:
        print(f"   GitHub handle:   @{github_user}")
    if leetcode_user:
        print(f"   LeetCode handle: @{leetcode_user}")
    print(f"   Skills to check: {len(skills)} claimed skills")

    # 1. Scrape GitHub
    gh_data = gh_scraper.audit_user(github_user, claimed_skills=skills, claimed_projects=projects)

    # 2. Scrape LeetCode
    lc_data = lc_scraper.audit_user(leetcode_user, claimed_skills=skills)

    # 3. Match skills and compute candidate level (0 - 10)
    evaluation = SkillMatcher.evaluate_candidate(
        claimed_skills=skills,
        claimed_projects=projects,
        github_data=gh_data,
        leetcode_data=lc_data
    )

    evaluation["candidate_name"] = name
    evaluation["email"] = candidate.get("email")
    evaluation["github_username"] = github_user
    evaluation["leetcode_username"] = leetcode_user
    return evaluation


def interactive_mode(gh_scraper: GitHubScraper, lc_scraper: LeetCodeScraper):
    """Fallback interactive prompt if no CLI flags are supplied."""
    print("\n" + "=" * 60)
    print(" ProfileAuditor: Web-Level Skill Scraper & Level Evaluator")
    print("=" * 60)

    choice = input("\nDo you want to load from a JSON file? (y/n) [default: y]: ").strip().lower()
    if choice != 'n':
        filepath = input("Enter path to parsed resumes JSON file: ").strip()
        if not os.path.exists(filepath):
            print(f"Error: File not found: {filepath}")
            return
        run_file_audit(filepath, gh_scraper, lc_scraper)
    else:
        name = input("Candidate Name: ").strip() or "Candidate"
        skills_raw = input("Enter claimed technical skills (comma-separated): ").strip()
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
        github = input("GitHub Username (press Enter to skip): ").strip() or None
        leetcode = input("LeetCode Username (press Enter to skip): ").strip() or None

        candidate = {
            "name": name,
            "technical_skills": skills,
            "github_username": github,
            "leetcode_username": leetcode,
            "projects": []
        }
        res = process_candidate(candidate, gh_scraper, lc_scraper)
        print("\n" + format_candidate_report(res, name))


def run_file_audit(
    filepath: str,
    gh_scraper: GitHubScraper,
    lc_scraper: LeetCodeScraper,
    cli_github: str = None,
    cli_leetcode: str = None,
    output_path: str = None
):
    """Loads JSON file, audits all candidates, and prints/saves results."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON file '{filepath}': {e}")
        return

    # Normalize to list
    candidates = data if isinstance(data, list) else [data]
    print(f"Loaded {len(candidates)} candidate(s) from {filepath}")

    all_results = []
    for c in candidates:
        res = process_candidate(c, gh_scraper, lc_scraper, cli_github, cli_leetcode)
        all_results.append(res)
        print("\n" + format_candidate_report(res, res.get("candidate_name", "Candidate")))

    # Optional JSON export
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_results if len(all_results) > 1 else all_results[0], f, indent=2)
            print(f"\n[OK] Successfully saved audit evaluation results to: {output_path}")
        except Exception as e:
            print(f"Error saving output to '{output_path}': {e}")


def main():
    parser = argparse.ArgumentParser(
        description="ProfileAuditor Web-Level Scraper: Audit GitHub & LeetCode and evaluate candidate engineering levels (0.0 - 10.0)."
    )
    parser.add_argument(
        "-i", "--input",
        dest="input_file",
        help="Path to JSON file containing parsed resume(s)"
    )
    parser.add_argument(
        "-g", "--github",
        dest="github_username",
        help="Optional GitHub username override"
    )
    parser.add_argument(
        "-l", "--leetcode",
        dest="leetcode_username",
        help="Optional LeetCode username override"
    )
    parser.add_argument(
        "-t", "--token",
        dest="github_token",
        help="Optional GitHub personal access token (or set GITHUB_TOKEN in env)"
    )
    parser.add_argument(
        "-o", "--output",
        dest="output_file",
        help="Optional path to export audit results as JSON"
    )

    args = parser.parse_args()

    # Initialize scrapers
    gh_scraper = GitHubScraper(token=args.github_token)
    lc_scraper = LeetCodeScraper()

    if args.input_file:
        if not os.path.exists(args.input_file):
            print(f"Error: Input file '{args.input_file}' does not exist.")
            sys.exit(1)
        run_file_audit(
            filepath=args.input_file,
            gh_scraper=gh_scraper,
            lc_scraper=lc_scraper,
            cli_github=args.github_username,
            cli_leetcode=args.leetcode_username,
            output_path=args.output_file
        )
    else:
        interactive_mode(gh_scraper, lc_scraper)


if __name__ == "__main__":
    main()
