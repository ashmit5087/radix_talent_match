import json
import sys
from pathlib import Path

from extract import extract_resume
from schema import ResumeExtract

OUTPUT_DIR = Path("output")
SIMPLE_DIR = OUTPUT_DIR / "simple"  # same details, skills as plain names only
SUPPORTED = {".pdf", ".docx"}


def save_simple(extract: ResumeExtract, out_name: str) -> Path:
    """Same details as the full file, but each skill is just its name
    (no category code, evidence or confidence)."""
    SIMPLE_DIR.mkdir(parents=True, exist_ok=True)
    simple = {
        "source_file": extract.source_file,
        "skills": [s.skill_name for s in extract.skills],
        "education": extract.education,
        "projects": extract.projects,
        "experience": extract.experience,
        "certifications": extract.certifications,
    }
    path = SIMPLE_DIR / out_name
    path.write_text(json.dumps(simple, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def save(file_path: Path) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_name = f"{file_path.stem}_{file_path.suffix.lstrip('.').lower()}.json"
    out_path = OUTPUT_DIR / out_name

    # Remove the old results first, so a failed run can't leave a stale file
    # behind that check_output.py would still count as OK
    out_path.unlink(missing_ok=True)
    (SIMPLE_DIR / out_name).unlink(missing_ok=True)

    extract = extract_resume(str(file_path))

    out_path.write_text(extract.model_dump_json(indent=2), encoding="utf-8")
    simple_path = save_simple(extract, out_name)
    print(f"OK    {file_path.name} -> {out_path} + {simple_path}  ({len(extract.skills)} skills)")
    return out_path


def main(target: str):
    path = Path(target)

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(f for f in path.iterdir() if f.suffix.lower() in SUPPORTED)
    else:
        print(f"Not found: {target}")
        sys.exit(1)

    if not files:
        print("No PDF or DOCX files found.")
        sys.exit(1)

    failed = 0
    for f in files:
        try:
            save(f)
        except Exception as e:
            # One bad resume should not stop the rest
            failed += 1
            print(f"FAIL  {f.name}: {e}")

    print(f"\nDone: {len(files) - failed} saved, {failed} failed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_resume.py <resume file or folder>")
        sys.exit(1)
    main(sys.argv[1])
