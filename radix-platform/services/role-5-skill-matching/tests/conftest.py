import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent / "fixtures"


def sk(name, cat="COD", evidence="used it in a project", conf="high"):
    d = {"skill_name": name, "category_code": cat}
    if evidence is not None:
        d["evidence"] = evidence
    if conf is not None:
        d["confidence"] = conf
    return d


def jd(*skills, source="test_jd.json"):
    return {"source_file": source, "company": "Test Co", "role": "Tester", "skills": list(skills)}


def cand(*skills):
    return {"name": "Test Candidate", "skills": list(skills)}


@pytest.fixture
def data_dir():
    return DATA


@pytest.fixture
def load():
    def _load(name):
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    return _load
