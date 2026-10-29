"""
cli.py - Command Line Interface for RADIX Talent Check (Role 4)
Runs Talent Check evaluations with rich terminal visualization or pure JSON output.

Usage:
  python -m talent_check.cli --candidate priya_menon --company "Oracle Financial"
  python -m talent_check.cli --candidate priya_menon --company "Google" --format json
  python -m talent_check.cli --candidate all --company "Google"
  python -m talent_check.cli --list-companies
  python -m talent_check.cli --list-candidates
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional

from talent_check.backend.levels import get_candidate_levels, get_candidate_levels_with_points, CATEGORIES, DEFAULT_K
from talent_check.backend.scoring import CRITICAL_GAP_MIN
from talent_check.backend.scoring import score, CATEGORIES_META, TIER_NAMES

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COMPANIES_FILE = os.path.join(DATA_DIR, "companies.json")
MOCK_DIR = os.path.join(DATA_DIR, "mock_profiles")

def load_companies() -> List[Dict[str, Any]]:
    if not os.path.exists(COMPANIES_FILE):
        print(f"Error: {COMPANIES_FILE} not found. Please run loader.py first.", file=sys.stderr)
        sys.exit(1)
    with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def find_company(companies: List[Dict[str, Any]], query: str) -> Optional[Dict[str, Any]]:
    query_str = str(query).strip().lower()
    # 1. Try matching by exact ID
    for c in companies:
        if str(c["id"]) == query_str:
            return c
    # 2. Try exact or substring name match
    for c in companies:
        if query_str in c["company"].lower():
            return c
    return None

def load_candidate_profile(candidate_arg: str) -> Dict[str, Any]:
    profile = None
    root_dir = os.path.dirname(BASE_DIR)
    parse_dir = os.path.join(root_dir, "parse-resumes")

    # 1. Direct path or path relative to root
    if os.path.exists(candidate_arg):
        with open(candidate_arg, "r", encoding="utf-8") as f:
            profile = json.load(f)
    elif os.path.exists(os.path.join(root_dir, candidate_arg)):
        with open(os.path.join(root_dir, candidate_arg), "r", encoding="utf-8") as f:
            profile = json.load(f)
    elif os.path.exists(parse_dir):
        # 2. Check parse-resumes folder
        for fn in os.listdir(parse_dir):
            if fn.endswith(".json") and candidate_arg.lower() in fn.lower():
                with open(os.path.join(parse_dir, fn), "r", encoding="utf-8") as f:
                    profile = json.load(f)
                    break

    if not profile:
        # 3. Check mock directory
        clean_name = candidate_arg.replace(".json", "")
        mock_path = os.path.join(MOCK_DIR, f"{clean_name}.json")
        if os.path.exists(mock_path):
            with open(mock_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
        else:
            for fn in os.listdir(MOCK_DIR):
                if fn.endswith(".json") and clean_name.lower() in fn.lower():
                    with open(os.path.join(MOCK_DIR, fn), "r", encoding="utf-8") as f:
                        profile = json.load(f)
                        break

    if not profile:
        print(f"Error: Candidate '{candidate_arg}' not found.", file=sys.stderr)
        sys.exit(1)

    # Standardize candidate name from parsed resume format if missing
    if "name" not in profile:
        src = profile.get("source_file", "")
        if src:
            profile["name"] = os.path.splitext(os.path.basename(src))[0]
        else:
            profile["name"] = "Candidate"

    return profile

def render_bar(level: int, max_level: int = 10, fill_char: str = "■", empty_char: str = "·") -> str:
    level = max(0, min(max_level, level))
    return fill_char * level + empty_char * (max_level - level)

def print_terminal_view(result: Dict[str, Any], candidate_profile: Dict[str, Any]):
    cand_name = candidate_profile.get("name", "Candidate")
    cand_headline = candidate_profile.get("headline", "")
    company_name = result["company"]
    score_val = result["readiness_score"]
    verdict = result["verdict"]

    border = "=" * 80
    sub_border = "-" * 80

    print(f"\n{border}")
    print(f"  RADIX TALENT CHECK · ROLE 4 EVALUATION REPORT")
    print(border)
    print(f"  Candidate: {cand_name}")
    if cand_headline:
        print(f"  Focus:     {cand_headline}")
    print(f"  Target:    {company_name} (ID: {result.get('company_id')})")
    print(sub_border)
    
    # Verdict summary box
    verdict_badge = f"[{verdict.upper()}]"
    print(f"  READINESS SCORE:   {score_val}/100   {verdict_badge}")
    print(f"  ASSESSMENT:        {result['verdict_message']}")
    print(f"  METRICS:           {result['summary']['met_count']}/12 Met | "
          f"{result['summary']['gap_count']}/12 Gaps | "
          f"{result['summary']['critical_gap_count']} Critical (gap >= {CRITICAL_GAP_MIN})")
    print(sub_border)

    # 12-Skillset Matrix Table
    print(f"  {'CODE':<6} {'SKILLSET NAME':<28} {'REQ':<5} {'CAND':<5} {'PTS':<6} {'TIER':<16} {'STATUS':<12}")
    print(f"  {'-'*4:<6} {'-'*26:<28} {'-'*4:<5} {'-'*4:<5} {'-'*4:<6} {'-'*14:<16} {'-'*10:<12}")

    for s in result["skillset_gap"]:
        code = s["category_code"]
        name = s["category_name"]
        req = s["required_level"]
        cand = s["candidate_level"]
        pts_val = s.get("evidence_points")
        pts_str = f"{pts_val:.1f}" if pts_val is not None else "-"
        tier = f"{s['required_tier']} ({s['tier_name'][:10]})"
        
        if not s["gap"]:
            status = "[MET]"
        elif s["gap_size"] >= CRITICAL_GAP_MIN:
            status = f"[CRIT -{s['gap_size']}]"
        else:
            status = f"[GAP -{s['gap_size']}]"

        print(f"  {code:<6} {name:<28} {req:<5} {cand:<5} {pts_str:<6} {tier:<16} {status:<12}")

    # Top priority gap areas
    focus = result.get("focus_areas", [])
    if focus:
        print(sub_border)
        print("  PRIORITY ACTION ITEMS TO MEET THE BAR:")
        for idx, f in enumerate(focus, 1):
            print(f"   {idx}. {f['name']} ({f['code']}): At level {f['current']}, company requires {f['required']} [{f['target_tier']}]. Gap: +{f['gap']}.")

    print(f"{border}\n")

def get_contract_json(result: Dict[str, Any]) -> Dict[str, Any]:
    """Returns exact minimal contract format required by the brief."""
    return {
        "company": result["company"],
        "skillset_gap": [
            {
                "category_code": s["category_code"],
                "required_level": s["required_level"],
                "candidate_level": s["candidate_level"],
                "gap": s["gap"]
            }
            for s in result["skillset_gap"]
        ],
        "readiness_score": result["readiness_score"]
    }

def main():
    parser = argparse.ArgumentParser(
        description="RADIX Talent Match - Role 4 (Talent Check) CLI Evaluator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python -m talent_check.cli --candidate priya_menon --company "Oracle Financial"
  python -m talent_check.cli --candidate priya_menon --company 4 --format json
  python -m talent_check.cli --candidate all --company "Google"
  python -m talent_check.cli --list-companies
  python -m talent_check.cli --list-candidates
        """
    )
    parser.add_argument("-c", "--candidate", help="Candidate name/id (e.g. 'priya_menon', 'all', or path to JSON)")
    parser.add_argument("-t", "--company", help="Target company name or ID (e.g. 'Google', 'Microsoft', '24')")
    parser.add_argument("-f", "--format", choices=["terminal", "json", "contract"], default="terminal",
                        help="Output format: 'terminal' (visual table), 'json' (enriched JSON), or 'contract' (minimal spec JSON)")
    parser.add_argument("-k", "--k-factor", type=float, default=DEFAULT_K,
                        help=f"Saturation curve parameter k (default: {DEFAULT_K})")
    parser.add_argument("-o", "--output", help="Optional file path to write JSON output to")
    parser.add_argument("--list-companies", action="store_true", help="List all available companies and exit")
    parser.add_argument("--list-candidates", action="store_true", help="List all built-in mock candidates and exit")

    args = parser.parse_args()

    companies = load_companies()

    # Handle --list-companies
    if args.list_companies:
        print(f"\nAvailable Companies ({len(companies)} loaded):\n")
        print(f"  {'ID':<6} {'COMPANY NAME':<60}")
        print(f"  {'-'*4:<6} {'-'*58:<60}")
        for c in companies:
            print(f"  {c['id']:<6} {c['company']:<60}")
        print()
        return

    # Handle --list-candidates
    if args.list_candidates:
        print("\nAvailable Mock Candidates:\n")
        print(f"  {'ID':<25} {'NAME':<25} {'FOCUS':<40}")
        print(f"  {'-'*23:<25} {'-'*23:<25} {'-'*38:<40}")
        for filename in sorted(os.listdir(MOCK_DIR)):
            if filename.endswith(".json"):
                cid = filename[:-5]
                with open(os.path.join(MOCK_DIR, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"  {cid:<25} {data.get('name', ''):<25} {data.get('headline', '')[:38]:<40}")
        print()
        return

    if not args.candidate:
        parser.print_help()
        print("\nError: Please specify --candidate (or run with --list-candidates).", file=sys.stderr)
        sys.exit(1)

    target_company = None
    if args.company:
        target_company = find_company(companies, args.company)
        if not target_company:
            print(f"Error: Company matching '{args.company}' not found. Use --list-companies to see valid names/IDs.", file=sys.stderr)
            sys.exit(1)
    else:
        # Default to Google LLC (id 4)
        target_company = next((c for c in companies if c["id"] == 4), companies[0])

    # Handle 'all' candidates benchmark comparison
    if args.candidate.lower() == "all":
        mock_files = sorted([f for f in os.listdir(MOCK_DIR) if f.endswith(".json")])
        results_list = []
        
        if args.format == "terminal":
            print("\n" + "=" * 90)
            print(f"  RADIX BENCHMARK SUMMARY FOR: {target_company['company']} (ID: {target_company['id']}) [k={args.k_factor}]")
            print("=" * 90)
            print(f"  {'CANDIDATE':<24} {'SCORE':<8} {'VERDICT':<14} {'MET':<8} {'GAPS':<8} {'CRITICAL':<10}")
            print(f"  {'-'*22:<24} {'-'*6:<8} {'-'*12:<14} {'-'*6:<8} {'-'*6:<8} {'-'*8:<10}")

        for mf in mock_files:
            profile = load_candidate_profile(os.path.join(MOCK_DIR, mf))
            levels, pts = get_candidate_levels_with_points(profile, k=args.k_factor)
            res = score(levels, target_company, evidence_points=pts)
            res["candidate_name"] = profile.get("name")
            
            if args.format == "terminal":
                s = res["summary"]
                print(f"  {profile.get('name', mf):<24} {res['readiness_score']:>3}%    {res['verdict']:<14} "
                      f"{s['met_count']:>2}/12   {s['gap_count']:>2}/12   {s['critical_gap_count']:>2}")
            else:
                if args.format == "contract":
                    results_list.append(get_contract_json(res))
                else:
                    results_list.append(res)

        if args.format == "terminal":
            print("=" * 90 + "\n")
        else:
            output_str = json.dumps(results_list, indent=2, ensure_ascii=False)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_str)
                print(f"Results written to {args.output}")
            else:
                print(output_str)
        return

    # Single Candidate Evaluation
    candidate_profile = load_candidate_profile(args.candidate)
    candidate_levels, evidence_points = get_candidate_levels_with_points(candidate_profile, k=args.k_factor)
    result = score(candidate_levels, target_company, evidence_points=evidence_points)

    if args.format == "contract":
        contract_data = get_contract_json(result)
        output_str = json.dumps(contract_data, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_str)
            print(f"Contract JSON saved to {args.output}")
        else:
            print(output_str)

    elif args.format == "json":
        result["candidate_name"] = candidate_profile.get("name")
        result["candidate_levels"] = candidate_levels
        result["evidence_points"] = evidence_points
        output_str = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_str)
            print(f"Enriched JSON saved to {args.output}")
        else:
            print(output_str)

    else:
        # Default terminal view
        print_terminal_view(result, candidate_profile)
        if args.output:
            contract_data = get_contract_json(result)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(contract_data, f, indent=2, ensure_ascii=False)
            print(f"Also saved contract JSON to {args.output}\n")

if __name__ == "__main__":
    main()
