"""
loader.py - SQL to JSON loader for Radix staging_company_skill_levels_rows.sql
Parses 116 companies and maps columns to 12 RADIX skill categories and proficiency tiers.
"""

import os
import re
import json

CATEGORIES = [
    {"code": "COD", "name": "Coding", "col": "coding"},
    {"code": "DSA", "name": "Data Structures & Algorithms", "col": "data_structures_and_algorithms"},
    {"code": "OOD", "name": "Object-Oriented Design", "col": "object_oriented_programming_and_design"},
    {"code": "APTI", "name": "Aptitude & Problem Solving", "col": "aptitude_and_problem_solving"},
    {"code": "COMM", "name": "Communication Skills", "col": "communication_skills"},
    {"code": "AI", "name": "AI Native Engineering", "col": "ai_native_engineering"},
    {"code": "CLOUD", "name": "DevOps & Cloud", "col": "devops_and_cloud"},
    {"code": "SQL", "name": "SQL & Design", "col": "sql_and_design"},
    {"code": "SWE", "name": "Software Engineering", "col": "software_engineering"},
    {"code": "SYSD", "name": "System Design & Architecture", "col": "system_design_and_architecture"},
    {"code": "NETW", "name": "Computer Networking", "col": "computer_networking"},
    {"code": "OS", "name": "Operating Systems", "col": "operating_system"},
]

CATEGORY_CODES = [c["code"] for c in CATEGORIES]
CATEGORY_NAMES = {c["code"]: c["name"] for c in CATEGORIES}

TIER_DESCRIPTIONS = {
    "CU": "Conceptual Understanding",
    "AP": "Application",
    "AS": "Analysis & Assessment",
    "EV": "Evaluation & Optimization",
    "CR": "Creation & Architecture",
}

NAME_FIXES = {
    "ByjuÃ¢â‚¬â„¢s": "Byju's",
    "Byjuâ€™s": "Byju's",
}

def parse_cell(cell: str) -> dict:
    cell = cell.strip()
    m = re.match(r"^(\d+)\s*-\s*([A-Z]{2})$", cell)
    if not m:
        raise ValueError(f"Invalid skill cell format: '{cell}'")
    level = int(m.group(1))
    tier = m.group(2)
    return {
        "level": level,
        "tier": tier,
        "tier_name": TIER_DESCRIPTIONS.get(tier, tier),
    }

def clean_company_name(name: str) -> str:
    cleaned = name.replace("''", "'").strip()
    return NAME_FIXES.get(cleaned, cleaned)

def load_companies_from_sql(sql_path: str) -> list[dict]:
    with open(sql_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Pattern matches (id, 'company_name', 'cell1', 'cell2', ..., 'cell12', processed, ...)
    pat = re.compile(
        r"\(\s*(\d+),\s*'((?:[^']|'')*)',\s*"
        r"((?:'[^']*',\s*){11}'[^']*')"
    )

    companies_by_id = {}
    for m in pat.finditer(text):
        cid = int(m.group(1))
        raw_name = m.group(2)
        name = clean_company_name(raw_name)
        cell_str = m.group(3)
        raw_cells = re.findall(r"'([^']*)'", cell_str)

        if len(raw_cells) != 12:
            continue

        skills = {}
        for cat_info, cell_val in zip(CATEGORIES, raw_cells):
            code = cat_info["code"]
            parsed = parse_cell(cell_val)
            skills[code] = {
                "category_code": code,
                "category_name": cat_info["name"],
                "required_level": parsed["level"],
                "tier": parsed["tier"],
                "tier_name": parsed["tier_name"],
            }

        companies_by_id[cid] = {
            "id": cid,
            "company": name,
            "skills": skills,
        }

    # Handle duplicate company (ZS Associates: id 33 vs 102; take 102 as latest)
    # Deduplicate by normalized name keeping the latest id
    deduped = {}
    for cid in sorted(companies_by_id.keys()):
        item = companies_by_id[cid]
        deduped[item["company"]] = item

    return sorted(list(deduped.values()), key=lambda x: x["company"])

def export_companies_json(sql_path: str, output_path: str):
    companies = load_companies_from_sql(sql_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)
    print(f"Successfully processed and exported {len(companies)} companies to {output_path}")
    return companies

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sql_file = os.path.join(base_dir, "data", "staging_company_skill_levels_rows.sql")
    if not os.path.exists(sql_file):
        # Fallback to root if not yet copied to data/
        sql_file = os.path.join(os.path.dirname(base_dir), "staging_company_skill_levels_rows.sql")
    out_file = os.path.join(base_dir, "data", "companies.json")
    export_companies_json(sql_file, out_file)
