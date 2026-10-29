"""Skill-name normalization.

`normalize_text`  : string hygiene only (case, punctuation, separators).
`canonical`       : normalize_text + explicit alias lookup from aliases.py.

No fuzzy/edit-distance matching happens here, by design: it would silently
equate unrelated technologies (java/javascript, sql/postgresql).
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from .aliases import ALIAS_GROUPS

# Symbol-bearing names must be rewritten BEFORE punctuation is stripped,
# otherwise c++ / c# / .net would all collapse into "c" / "net".
_SYMBOL_REWRITES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"c\s*\+\+"), "cplusplus"),
    (re.compile(r"c\s*#"), "csharp"),
    (re.compile(r"\.net\b"), "dotnet"),
    (re.compile(r"\bnode\.js\b"), "nodejs"),
    (re.compile(r"\bnext\.js\b"), "nextjs"),
    (re.compile(r"\bvue\.js\b"), "vuejs"),
    (re.compile(r"\breact\.js\b"), "reactjs"),
    (re.compile(r"\bexpress\.js\b"), "expressjs"),
    (re.compile(r"\bci\s*/\s*cd\b"), "ci cd"),
    (re.compile(r"\btcp\s*/\s*ip\b"), "tcp ip"),
]
_AMP = re.compile(r"\s*&\s*")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WS = re.compile(r"\s+")
# Parenthetical qualifiers like "Python (3.x)" or "SQL (e.g. joins)".
_PAREN = re.compile(r"\([^)]*\)")


def normalize_text(name: str) -> str:
    """Lowercase, fold unicode, rewrite symbols, collapse punctuation."""
    if not name:
        return ""
    text = unicodedata.normalize("NFKC", name).lower().strip()
    text = _PAREN.sub(" ", text)
    text = _AMP.sub(" and ", text)
    for pattern, repl in _SYMBOL_REWRITES:
        text = pattern.sub(repl, text)
    text = _NON_ALNUM.sub(" ", text)
    return _WS.sub(" ", text).strip()


def _build_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for canon, aliases in ALIAS_GROUPS.items():
        canon_n = normalize_text(canon) or canon
        index[canon_n] = canon_n
        for alias in aliases:
            alias_n = normalize_text(alias)
            if not alias_n:
                continue
            existing = index.get(alias_n)
            if existing is not None and existing != canon_n:
                raise ValueError(
                    f"alias {alias!r} maps to both {existing!r} and {canon_n!r}"
                )
            index[alias_n] = canon_n
    return index


ALIAS_INDEX: dict[str, str] = _build_index()


@lru_cache(maxsize=4096)
def canonical(name: str) -> str:
    """Canonical comparison key for a skill name (alias-resolved)."""
    n = normalize_text(name)
    return ALIAS_INDEX.get(n, n)


_SEG_SPLIT = re.compile(r"\s*(?:&|,|/|;|\||\band\b|\+)\s*")
_LEADING_MODIFIERS = {"advanced", "basic", "strong", "core", "applied", "practical", "intermediate", "solid"}


def atoms(name: str) -> list[str]:
    """Split a compound skill name into the individual skills it claims.

    'Full-Stack Development (TypeScript, Python, Go)' -> full stack development, typescript, python, go
    'Advanced Data Structures & Competitive Programming' -> data structures, competitive programming
    Each atom is canonicalized; leading level words (advanced, basic...) are dropped.
    """
    if not name:
        return []
    raw = unicodedata.normalize("NFKC", name).lower()
    parts = [_PAREN.sub(" ", raw)] + re.findall(r"\(([^)]*)\)", raw)
    out: list[str] = []
    for part in parts:
        for seg in _SEG_SPLIT.split(part):
            toks = normalize_text(seg).split()
            while toks and toks[0] in _LEADING_MODIFIERS:
                toks = toks[1:]
            if toks:
                out.append(canonical(" ".join(toks)))
    return [a for a in dict.fromkeys(out) if a]


def is_alias_match(a: str, b: str) -> bool:
    """True when two names resolve to the same canonical skill."""
    ca, cb = canonical(a), canonical(b)
    return bool(ca) and ca == cb
