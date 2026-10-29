import json
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from schema import CATEGORY_NAMES, ResumeExtract

OUTPUT_DIR = Path("output")


def main():
    files = sorted(OUTPUT_DIR.glob("*.json"))
    if not files:
        print("No JSON files in output/. Run parse_resume.py first.")
        return

    good = 0
    for f in files:
        try:
            data = ResumeExtract.model_validate(json.loads(f.read_text(encoding="utf-8")))
        except (ValidationError, json.JSONDecodeError) as e:
            print(f"BAD   {f.name}\n{e}\n")
            continue

        good += 1
        counts = Counter(s.category_code for s in data.skills)
        conf = Counter(s.confidence for s in data.skills)
        print(f"OK    {f.name}  ({len(data.skills)} skills: "
              f"{conf['high']} high, {conf['medium']} medium, {conf['low']} low)")
        print("      " + "  ".join(f"{c}:{counts[c]}" for c in CATEGORY_NAMES if counts[c]))
        if not data.education:
            print("      (no education found)")
        print()

    print(f"{good} of {len(files)} files match the shared format.")
    print("Milestone #8 needs at least 2 of the 4 sample resumes working.")


if __name__ == "__main__":
    main()
