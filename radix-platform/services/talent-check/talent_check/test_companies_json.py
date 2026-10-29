import json
import os
import sys

def validate_companies(json_path: str):
    assert os.path.exists(json_path), f"File not found: {json_path}"
    with open(json_path, "r", encoding="utf-8") as f:
        companies = json.load(f)

    assert isinstance(companies, list), "companies.json root must be a list"
    assert len(companies) == 115, f"Expected 115 clean companies, got {len(companies)}"

    EXPECTED_CATS = [
        "COD", "DSA", "OOD", "APTI", "COMM", "AI",
        "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS"
    ]
    VALID_TIERS = {"CU", "AP", "AS", "EV", "CR"}

    seen_ids = set()
    seen_names = set()

    for c in companies:
        assert "id" in c and isinstance(c["id"], int), f"Missing valid int id in {c}"
        assert "company" in c and isinstance(c["company"], str) and c["company"].strip(), f"Missing valid company name in {c}"
        assert c["company"] not in seen_names, f"Duplicate company name found: {c['company']}"
        seen_names.add(c["company"])
        seen_ids.add(c["id"])

        skills = c.get("skills", {})
        assert len(skills) == 12, f"Company {c['company']} has {len(skills)} skills, expected 12"

        for code in EXPECTED_CATS:
            assert code in skills, f"Missing category {code} in {c['company']}"
            s = skills[code]
            assert s["category_code"] == code
            assert 1 <= s["required_level"] <= 10, f"Invalid level {s['required_level']} in {c['company']} ({code})"
            assert s["tier"] in VALID_TIERS, f"Invalid tier {s['tier']} in {c['company']} ({code})"
            assert s["tier_name"], f"Missing tier_name in {c['company']} ({code})"

    # Benchmark test companies verification
    by_id = {c["id"]: c for c in companies}
    
    # Google LLC (id 4)
    g = by_id[4]
    assert "Google LLC" in g["company"]
    assert g["skills"]["COD"]["required_level"] == 8 and g["skills"]["COD"]["tier"] == "CR"
    assert g["skills"]["DSA"]["required_level"] == 9 and g["skills"]["DSA"]["tier"] == "CR"
    assert g["skills"]["SYSD"]["required_level"] == 4 and g["skills"]["SYSD"]["tier"] == "AS"
    assert g["skills"]["OS"]["required_level"] == 9 and g["skills"]["OS"]["tier"] == "CR"

    # Microsoft Corporation (id 78)
    m = by_id[78]
    assert "Microsoft" in m["company"]
    assert m["skills"]["COD"]["required_level"] == 6 and m["skills"]["COD"]["tier"] == "AS"
    assert m["skills"]["DSA"]["required_level"] == 9 and m["skills"]["DSA"]["tier"] == "EV"
    assert m["skills"]["SWE"]["required_level"] == 9 and m["skills"]["SWE"]["tier"] == "EV"

    # Oracle FSS (id 24)
    o24 = by_id[24]
    assert "Oracle Financial Services" in o24["company"]
    assert o24["skills"]["COD"]["required_level"] == 5 and o24["skills"]["COD"]["tier"] == "AP"
    assert o24["skills"]["DSA"]["required_level"] == 6 and o24["skills"]["DSA"]["tier"] == "AP"
    assert o24["skills"]["SYSD"]["required_level"] == 5 and o24["skills"]["SYSD"]["tier"] == "CR"

    # Oracle India (id 3)
    o3 = by_id[3]
    assert "Oracle India" in o3["company"]
    assert o3["skills"]["COD"]["required_level"] == 7 and o3["skills"]["COD"]["tier"] == "EV"
    assert o3["id"] != o24["id"]

    # Byju's name fix
    byjus = next((c for c in companies if "Byju" in c["company"]), None)
    assert byjus is not None and byjus["company"] == "Byju's", f"Byju's name issue: {byjus}"

    # ZS Associates deduplicated to latest ID 102
    zs = next((c for c in companies if "ZS Associates" in c["company"]), None)
    assert zs is not None and zs["id"] == 102, f"ZS Associates expected id 102, got {zs['id'] if zs else None}"

    print(f"[VERIFIED] {json_path} passed all 115 company checks and benchmark assertions successfully!")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)

    # Validate both files
    validate_companies(os.path.join(base_dir, "data", "companies.json"))
    validate_companies(os.path.join(root_dir, "companies.json"))
