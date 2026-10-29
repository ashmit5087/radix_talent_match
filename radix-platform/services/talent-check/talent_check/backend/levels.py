"""
levels.py - Layer A of Talent Check
Derives candidate skill levels (0-10) across the 12 RADIX categories
using an evidence-points aggregator and a saturating exponential curve.
Optimized for high-throughput evaluation, false-positive elimination, and skill recovery.
"""

import math
import re
from typing import Dict, Any, List, Tuple, Optional

CATEGORIES = [
    "COD", "DSA", "OOD", "APTI", "COMM", "AI",
    "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS"
]

# Evidence points scoring scheme
CONFIDENCE_POINTS = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.3,
}

INTERNSHIP_POINTS = 1.5
HACKATHON_POINTS = 1.0
CERTIFICATION_POINTS = 1.0
PROJECT_POINTS = 1.0

# Default saturation parameter: level = round(10 * (1 - exp(-points / k)))
DEFAULT_K = 2.0

# Free-text keyword map for assigning categories to internships, hackathons, certs, and projects
KEYWORD_MAP: Dict[str, List[str]] = {
    "COD": [
        r"\bpython\b", r"\bjava\b", r"\bc\+\+(?!\w)", r"\bgolang\b",
        r"\bgo\s+(?:lang|routines?|backend|microservices?|code|developer)\b",
        r"\brust\b", r"\bjavascript\b", r"\btypescript\b", r"\bc#(?!\w)",
        r"\bscripting\b", r"\bcoding\b", r"\bprogramming\b"
    ],
    "DSA": [
        r"\bdsa\b", r"\bdata structures?\b", r"\balgorithms?\b", r"\bleetcode\b",
        r"\bcodeforces\b", r"\bcompetitive programming\b", r"\bdynamic programming\b",
        r"\bgraphs?\b", r"\btrees?\b", r"\bsorting\b", r"\bhashing\b"
    ],
    "OOD": [
        r"\bobject[- ]oriented\b", r"\bood\b", r"\boop\b", r"\bdesign patterns?\b",
        r"\bsolid\s+(?:principles?|design|architecture|patterns?|code)\b",
        r"\bs\.o\.l\.i\.d\b", r"\bclean architecture\b", r"\buml\b",
        r"\bclass diagrams?\b"
    ],
    "APTI": [
        r"\baptitude\b", r"\bproblem[- ]solving\b", r"\banalytical\b", r"\banalytics\b",
        r"\bstatistics\b", r"\bstatistical\b", r"\bbayesian\b", r"\ba/b testing\b",
        r"\bquantitative\b", r"\blogic\b", r"\breasoning\b"
    ],
    "COMM": [
        r"\bcommunication\b", r"\bpresentation\b", r"\bpresented\b", r"\bleadership\b",
        r"\bled\s+(?:a\s+team|teams?|initiatives?|sprints?|projects?|efforts?|development|design|meetings?|discussions?)\b",
        r"\bmentored\b", r"\bworkshops?\b", r"\bdocumentation\b",
        r"\bservice desk\b", r"\bhelpdesk\b", r"\btickets?\b", r"\bescalation\b",
        r"\btroubleshoot\w*\b",
        r"\bsla\b", r"\bclient\w*\b", r"\bstakeholders?\b"
    ],
    "AI": [
        r"\bai\b", r"\ba\.i\.\b", r"\bmachine learning\b", r"\bdeep learning\b",
        r"\bllm\w*\b", r"\brag\b", r"\bnlp\b", r"\bcomputer vision\b",
        r"\blangchain\b", r"\bllamaindex\b", r"\bpytorch\b", r"\btensorflow\b",
        r"\bgenai\b", r"\bneural networks?\b", r"\btransformers?\b",
        r"\bai/ml\b", r"\bmlops\b",
        r"\bml\s+(?:models?|algorithms?|pipelines?|systems?|engineering|engineer|frameworks?|solutions?)\b"
    ],
    "CLOUD": [
        r"\bcloud\b", r"\baws\b", r"\bazure\b", r"\bgcp\b", r"\bdocker\b",
        r"\bkubernetes\b", r"\bk8s\b", r"\bterraform\b", r"\bdevops\b",
        r"\bci/cd\b", r"\bhelm\b", r"\bserverless\b"
    ],
    "SQL": [
        r"\bsql\b", r"\bpostgres\w*\b", r"\bmysql\b", r"\boracle\b",
        r"\bdatabase\w*\b", r"\brdbms\b", r"\bquery\b", r"\bqueries\b",
        r"\bbigquery\b", r"\bsnowflake\b", r"\bdatabricks\b", r"\bpl/sql\b",
        r"\betl\b", r"\bdata warehouse\b"
    ],
    "SWE": [
        r"\bsoftware engineering\b", r"\bgit\b", r"\bgithub\b", r"\btesting\b",
        r"\bqa\b", r"\bunit test\w*\b", r"\bpytest\b", r"\bjunit\b",
        r"\bjira\b", r"\bagile\b", r"\bscrum\b", r"\bfull[- ]stack\b",
        r"\bmicroservices?\b", r"\brestful\b",
        r"\brest\s+(?:apis?|endpoints?|services?|web\s+services?|architecture)\b",
        r"\bapi\w*\b", r"\bsdlc\b"
    ],
    "SYSD": [
        r"\bsystem design\b", r"\bdistributed systems?\b", r"\bscalability\b",
        r"\bcaching\b", r"\bredis\b", r"\bkafka\b", r"\bmessage queue\w*\b",
        r"\bload balanc\w*\b", r"\braft\b", r"\bhigh availability\b", r"\blow[- ]latency\b"
    ],
    "NETW": [
        r"\bnetwork\w*\b", r"\btcp\b", r"\budp\b", r"\btcp/ip\b",
        r"\bhttps?\b",
        r"\bdns\b", r"\bvpn\w*\b", r"\bebpf\b", r"\bwebsocket\w*\b",
        r"\btls\b", r"\bsockets?\b", r"\bpackets?\b", r"\brouting\b"
    ],
    "OS": [
        r"\boperating systems?\b", r"\bos\s+(?:internals|kernel|level)\b",
        r"\blinux\b", r"\bunix\b",
        r"\bkernel\b", r"\bposix\b", r"\bconcurrency\b", r"\bmultithreading\b",
        r"\bthreads?\b", r"\bprocesses\b", r"\bipc\b", r"\bmemory management\b",
        r"\bxv6\b", r"\bbash\b", r"\bshell\b"
    ]
}

COMPILED_CATEGORY_REGEX: Dict[str, re.Pattern] = {
    cat: re.compile(r"(?:" + "|".join(patterns) + r")", re.IGNORECASE)
    for cat, patterns in KEYWORD_MAP.items()
}

COMPILED_KEYWORDS = {
    cat: [re.compile(pat, re.IGNORECASE) for pat in patterns]
    for cat, patterns in KEYWORD_MAP.items()
}

URL_REGEX = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)

def extract_text(item: Any) -> str:
    """Recursively concatenates all string/text values from item and strips URLs."""
    def _collect_strings(val: Any) -> List[str]:
        if isinstance(val, str):
            return [val]
        if isinstance(val, dict):
            res = []
            for v in val.values():
                res.extend(_collect_strings(v))
            return res
        if isinstance(val, list):
            res = []
            for sub in val:
                res.extend(_collect_strings(sub))
            return res
        if isinstance(val, (int, float)):
            return [str(val)]
        return []

    raw = " ".join(_collect_strings(item))
    return URL_REGEX.sub(" ", raw)

def get_matched_categories(item: Any, text: Optional[str] = None) -> List[str]:
    """
    Returns all categories matched by an item (explicit category tags or keyword matches).
    Extracts text once if not provided.
    """
    matched = []
    if isinstance(item, dict):
        code = item.get("category_code") or item.get("category")
        if code:
            c_up = str(code).upper()
            if c_up in CATEGORIES:
                matched.append(c_up)
        cats = item.get("categories") or item.get("tags")
        if isinstance(cats, list):
            for c in cats:
                c_up = str(c).upper()
                if c_up in CATEGORIES and c_up not in matched:
                    matched.append(c_up)

    if text is None:
        text = extract_text(item)

    if text:
        for cat, pattern in COMPILED_CATEGORY_REGEX.items():
            if cat not in matched and pattern.search(text):
                matched.append(cat)

    return matched

def item_matches_category(cat: str, item: Any) -> bool:
    """
    Checks if an internship, hackathon, certification, or project matches category 'cat'.
    Supports explicit category tags or fallback keyword matching.
    """
    return cat.upper() in get_matched_categories(item)

def derive_evidence_points(profile: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculates evidence points per category across all sources in profile:
      - Skills (direct category_code from Role 1/2, or fallback keyword match for OTHER/untagged):
        high=1.0, medium=0.6, low=0.3
      - Internships matching category: +1.5
      - Hackathons matching category: +1.0
      - Certifications matching category: +1.0
      - Projects matching category: +1.0
    Deduplicates identical entries across experience and sections to prevent overcounting.
    """
    points = {cat: 0.0 for cat in CATEGORIES}

    # 1. Skills
    for s in profile.get("skills", []):
        if isinstance(s, str):
            s = {"skill_name": s, "confidence": "medium"}
        elif not isinstance(s, dict):
            continue
        cat = str(s.get("category_code") or s.get("category") or "").upper()
        conf = str(s.get("confidence", "medium")).lower()
        pts = CONFIDENCE_POINTS.get(conf, 0.6)

        if cat in points:
            points[cat] += pts
        else:
            matched_cats = get_matched_categories(s)
            for m_cat in matched_cats:
                points[m_cat] += pts

    # Helper to deduplicate list of items by normalized text content
    def _dedup_items(raw_list: List[Any]) -> List[Any]:
        seen = set()
        unique = []
        for it in raw_list:
            sig = " ".join(extract_text(it).lower().split())
            if sig and sig not in seen:
                seen.add(sig)
                unique.append(it)
        return unique

    # 2. Internships & Experience
    all_experience = _dedup_items(profile.get("internships", []) + profile.get("experience", []))
    for exp_item in all_experience:
        text = extract_text(exp_item)
        pts_to_add = HACKATHON_POINTS if "hackathon" in text.lower() else INTERNSHIP_POINTS
        matched_cats = get_matched_categories(exp_item, text=text)
        for cat in matched_cats:
            points[cat] += pts_to_add

    # 3. Dedicated Hackathons list (+1.0)
    for hack in _dedup_items(profile.get("hackathons", [])):
        text = extract_text(hack)
        matched_cats = get_matched_categories(hack, text=text)
        for cat in matched_cats:
            points[cat] += HACKATHON_POINTS

    # 4. Certifications (+1.0)
    for cert in _dedup_items(profile.get("certifications", [])):
        text = extract_text(cert)
        matched_cats = get_matched_categories(cert, text=text)
        for cat in matched_cats:
            points[cat] += CERTIFICATION_POINTS

    # 5. Projects (+1.0)
    for proj in _dedup_items(profile.get("projects", [])):
        text = extract_text(proj)
        matched_cats = get_matched_categories(proj, text=text)
        for cat in matched_cats:
            points[cat] += PROJECT_POINTS

    return {cat: round(val, 2) for cat, val in points.items()}

def points_to_level(points: float, k: float = DEFAULT_K) -> int:
    """
    Converts evidence points to a 0-10 level using a saturating exponential curve:
      level = round(10 * (1 - exp(-points / k)))
    Clamped to range [0, 10].
    """
    if points <= 0.0:
        return 0
    calc = 10.0 * (1.0 - math.exp(-points / float(k)))
    level = int(round(calc))
    return max(0, min(10, level))

def get_candidate_levels_with_points(
    profile: Dict[str, Any],
    k: float = DEFAULT_K
) -> Tuple[Dict[str, int], Dict[str, float]]:
    """
    Returns both derived levels (0-10) and the raw evidence points per category.
    """
    points = derive_evidence_points(profile)
    levels = {cat: points_to_level(points[cat], k) for cat in CATEGORIES}
    return levels, points

def get_candidate_levels(profile: Dict[str, Any], k: float = DEFAULT_K) -> Dict[str, int]:
    """
    Layer A extraction:
    Derives candidate levels (0-10) using evidence points and the saturating curve.
    """
    levels, _ = get_candidate_levels_with_points(profile, k)
    return levels


def augment_evidence_with_web_audit(
    evidence_points: Dict[str, float],
    audit_data: Dict[str, Any]
) -> Dict[str, float]:
    """
    Beta Feature: Augments evidence points across the 12 categories
    using verified code proof from GitHub and problem solving from LeetCode.
    Safely handles None values from unrated or empty profiles.
    """
    pts = dict(evidence_points)
    if not audit_data:
        return pts

    gh = audit_data.get("github") or {}
    lc = audit_data.get("leetcode") or {}
    audit = audit_data.get("audit") or {}

    # 1. Verified Skills on GitHub/LeetCode (extra +1.0 per verified skill)
    skills_breakdown = audit.get("skills_breakdown") or {}
    verified = skills_breakdown.get("verified_skills") or []
    for skill_name in verified:
        matched_cats = get_matched_categories({"skill_name": skill_name}, text=str(skill_name))
        for cat in matched_cats:
            pts[cat] = round(pts.get(cat, 0.0) + 1.0, 2)

    # 2. GitHub original repos and stars (+0.5 to +2.0 to COD, SWE)
    orig_repos_raw = gh.get("original_repos")
    orig_repos = len(orig_repos_raw) if isinstance(orig_repos_raw, list) else 0
    stars = int(gh.get("total_stars") or 0)
    if orig_repos >= 5 or stars >= 10:
        pts["COD"] = round(pts.get("COD", 0.0) + 1.5, 2)
        pts["SWE"] = round(pts.get("SWE", 0.0) + 1.5, 2)
    elif orig_repos >= 2:
        pts["COD"] = round(pts.get("COD", 0.0) + 0.8, 2)
        pts["SWE"] = round(pts.get("SWE", 0.0) + 0.8, 2)

    # 3. LeetCode problem solving (+1.0 to +3.0 to DSA, APTI)
    total_solved = int(lc.get("total_solved") or 0)
    hard_solved = int(lc.get("hard_solved") or 0)
    med_solved = int(lc.get("medium_solved") or 0)
    raw_contest = lc.get("contest_rating")
    contest_rating = float(raw_contest) if raw_contest is not None else 0.0

    if total_solved >= 100 or hard_solved >= 10 or contest_rating >= 1800:
        pts["DSA"] = round(pts.get("DSA", 0.0) + 3.0, 2)
        pts["APTI"] = round(pts.get("APTI", 0.0) + 2.5, 2)
    elif total_solved >= 30 or med_solved >= 15 or contest_rating >= 1500:
        pts["DSA"] = round(pts.get("DSA", 0.0) + 2.0, 2)
        pts["APTI"] = round(pts.get("APTI", 0.0) + 1.5, 2)
    elif total_solved > 0:
        pts["DSA"] = round(pts.get("DSA", 0.0) + 1.0, 2)
        pts["APTI"] = round(pts.get("APTI", 0.0) + 0.8, 2)

    return pts
