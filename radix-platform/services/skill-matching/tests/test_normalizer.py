import pytest

from skill_matching.aliases import ALIAS_GROUPS
from skill_matching.normalizer import ALIAS_INDEX, canonical, is_alias_match, normalize_text


def test_text_hygiene():
    assert normalize_text("  Python   Programming ") == "python programming"
    assert normalize_text("Data Structures & Algorithms") == "data structures and algorithms"
    assert normalize_text("scikit-learn") == "scikit learn"
    assert normalize_text("Python (3.x)") == "python"


def test_symbol_names_survive():
    assert normalize_text("C++") == "cplusplus"
    assert normalize_text("C#") == "csharp"
    assert normalize_text(".NET") == "dotnet"
    assert normalize_text("Node.js") == "nodejs"
    assert canonical("C++") != canonical("C")
    assert canonical("CI/CD") == canonical("continuous integration")


@pytest.mark.parametrize("a,b", [
    ("postgres", "PostgreSQL"),
    ("JS", "JavaScript"),
    ("scikit-learn", "scikit learn"),
    ("Data Structures & Algorithms", "data structures and algorithms"),
    ("DSA", "Data Structures and Algorithms"),
    ("Python programming", "python"),
    ("Microsoft Excel", "Excel"),
    ("k8s", "Kubernetes"),
])
def test_approved_aliases(a, b):
    assert is_alias_match(a, b)


@pytest.mark.parametrize("a,b", [
    ("Java", "JavaScript"),
    ("SQL", "PostgreSQL"),
    ("AWS", "Cloud"),
    ("AI", "Machine Learning"),
    ("Machine Learning", "Deep Learning"),
    ("C", "C++"),
    ("Python", "Pandas"),
    ("OOP", "Object Oriented Design"),
])
def test_unsafe_equivalences_rejected(a, b):
    assert not is_alias_match(a, b)


def test_alias_table_has_no_collisions():
    # _build_index raises at import time on collisions; also verify sanity here.
    assert len(ALIAS_INDEX) >= len(ALIAS_GROUPS)


def test_blank_name():
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""
