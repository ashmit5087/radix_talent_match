"""Bounded LLM retry utilities and deterministic job-description extraction."""

import logging
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar

from app.schemas import CategoryCode, ExtractedSkillList, Skill

logger = logging.getLogger("radix.llm_fallback")

_Result = TypeVar("_Result")


def retry_llm_call(
    operation: Callable[[], _Result],
    retryable_errors: tuple[type[Exception], ...],
    *,
    max_retries: int,
    backoff_seconds: float,
    max_delay_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
) -> _Result:
    """Run an LLM operation with bounded exponential backoff.

    An exception may provide a numeric ``retry_after`` attribute. Its value is
    preferred over the computed backoff and is still capped by ``max_delay_seconds``.
    """
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except retryable_errors as exc:
            if attempt >= max_retries:
                raise
            retry_after = getattr(exc, "retry_after", None)
            delay = backoff_seconds * (2 ** attempt)
            if isinstance(retry_after, (float, int)) and retry_after >= 0:
                delay = float(retry_after)
            delay = min(delay, max_delay_seconds)
            logger.warning(
                "Transient LLM error (%s); retry %d/%d in %.1fs",
                type(exc).__name__,
                attempt + 1,
                max_retries,
                delay,
            )
            sleep(delay)
    raise AssertionError("unreachable")  # pragma: no cover


@dataclass(frozen=True)
class SkillRule:
    """Canonical skill name, RADIX category, and text variants to recognize."""

    category_code: CategoryCode
    keywords: tuple[str, ...]


DEFAULT_SKILL_KEYWORDS: dict[str, SkillRule] = {
    "Python": SkillRule("COD", ("python",)),
    "Java": SkillRule("COD", ("java",)),
    "JavaScript": SkillRule("COD", ("javascript", "js")),
    "TypeScript": SkillRule("COD", ("typescript", "ts")),
    "C": SkillRule("COD", ("c",)),
    "C++": SkillRule("COD", ("c++",)),
    "C#": SkillRule("COD", ("c#", "c sharp")),
    "Go": SkillRule("COD", ("golang", "go")),
    "Rust": SkillRule("COD", ("rust",)),
    "Ruby": SkillRule("COD", ("ruby",)),
    "PHP": SkillRule("COD", ("php",)),
    "Kotlin": SkillRule("COD", ("kotlin",)),
    "Swift": SkillRule("COD", ("swift",)),
    "Scala": SkillRule("COD", ("scala",)),
    "Bash": SkillRule("COD", ("bash", "shell scripting")),
    "HTML": SkillRule("COD", ("html",)),
    "CSS": SkillRule("COD", ("css",)),
    "Data Structures": SkillRule("DSA", ("data structures",)),
    "Algorithms": SkillRule("DSA", ("algorithms", "algorithm design")),
    "Data Structures and Algorithms": SkillRule("DSA", ("data structures and algorithms",)),
    "Programming": SkillRule("COD", ("programming", "coding")),
    "Object-Oriented Programming": SkillRule("OOD", ("object-oriented", "object oriented", "oop")),
    "Object-Oriented Design": SkillRule("OOD", ("object-oriented design", "object oriented design")),
    "Design Patterns": SkillRule("OOD", ("design patterns",)),
    "Aptitude": SkillRule("APTI", ("aptitude", "quantitative reasoning", "numerical reasoning")),
    "Quantitative Reasoning": SkillRule("APTI", ("quantitative reasoning", "quantitative analysis")),
    "Statistics": SkillRule("APTI", ("statistics", "statistical analysis", "statistical judgment")),
    "A/B testing": SkillRule("APTI", ("a/b testing", "a/b tests", "experimentation", "experiments")),
    "Communication": SkillRule("COMM", ("communication", "communicate")),
    "Collaboration": SkillRule("COMM", ("collaboration", "collaborate", "teamwork")),
    "Stakeholder Management": SkillRule("COMM", ("stakeholder management", "stakeholders")),
    "Artificial Intelligence": SkillRule("AI", ("artificial intelligence", "ai")),
    "Machine Learning": SkillRule("AI", ("machine learning", "ml")),
    "Deep Learning": SkillRule("AI", ("deep learning",)),
    "Natural Language Processing": SkillRule("AI", ("natural language processing", "nlp")),
    "Generative AI": SkillRule("AI", ("generative ai", "large language model", "llm")),
    "TensorFlow": SkillRule("AI", ("tensorflow",)),
    "PyTorch": SkillRule("AI", ("pytorch",)),
    "AWS": SkillRule("CLOUD", ("aws", "amazon web services")),
    "Microsoft Azure": SkillRule("CLOUD", ("azure",)),
    "Google Cloud": SkillRule("CLOUD", ("google cloud", "gcp")),
    "Docker": SkillRule("CLOUD", ("docker",)),
    "Kubernetes": SkillRule("CLOUD", ("kubernetes", "k8s")),
    "Terraform": SkillRule("CLOUD", ("terraform",)),
    "SQL": SkillRule("SQL", ("sql",)),
    "Schema Design": SkillRule("SQL", ("schema design", "database schema", "telemetry schema")),
    "Data Visualization": SkillRule("OTHER", ("data visualization", "data visualisation", "dashboard", "dashboards")),
    "PostgreSQL": SkillRule("SQL", ("postgresql", "postgres")),
    "MySQL": SkillRule("SQL", ("mysql",)),
    "MongoDB": SkillRule("SQL", ("mongodb",)),
    "Git": SkillRule("SWE", ("git", "version control")),
    "CI/CD": SkillRule("SWE", ("ci/cd", "continuous integration", "continuous delivery")),
    "Agile": SkillRule("SWE", ("agile", "scrum")),
    "Software Engineering": SkillRule("SWE", ("software engineering", "software development")),
    "Software Testing": SkillRule("SWE", ("software testing", "unit testing", "test automation")),
    "React": SkillRule("SWE", ("react", "react.js", "reactjs")),
    "Angular": SkillRule("SWE", ("angular",)),
    "Vue.js": SkillRule("SWE", ("vue.js", "vuejs")),
    "Node.js": SkillRule("SWE", ("node.js", "nodejs")),
    "Django": SkillRule("SWE", ("django",)),
    "Flask": SkillRule("SWE", ("flask",)),
    "FastAPI": SkillRule("SWE", ("fastapi",)),
    "Spring Boot": SkillRule("SWE", ("spring boot",)),
    "ASP.NET": SkillRule("SWE", ("asp.net", "asp net")),
    ".NET": SkillRule("SWE", (".net", "dotnet")),
    "Express.js": SkillRule("SWE", ("express.js", "expressjs")),
    "Ruby on Rails": SkillRule("SWE", ("ruby on rails", "rails")),
    "Jenkins": SkillRule("SWE", ("jenkins",)),
    "GitHub Actions": SkillRule("SWE", ("github actions",)),
    "Jira": SkillRule("SWE", ("jira",)),
    "Postman": SkillRule("SWE", ("postman",)),
    "Redis": SkillRule("SQL", ("redis",)),
    "Apache Kafka": SkillRule("SYSD", ("apache kafka", "kafka")),
    "RabbitMQ": SkillRule("SYSD", ("rabbitmq",)),
    "Microservices": SkillRule("SYSD", ("microservices", "microservice")),
    "System Design": SkillRule("SYSD", ("system design", "distributed systems")),
    "Distributed Systems": SkillRule("SYSD", ("distributed systems", "distributed system")),
    "Cloud Infrastructure": SkillRule("CLOUD", ("cloud infrastructure", "cloud platform")),
    "REST APIs": SkillRule("SYSD", ("rest api", "rest apis", "restful api", "restful apis")),
    "Networking": SkillRule("NETW", ("networking", "tcp/ip", "dns")),
    "Linux": SkillRule("OS", ("linux",)),
    "Operating Systems": SkillRule("OS", ("operating systems", "multithreading", "concurrency")),
}

_PREFERRED_PATTERN = re.compile(
    r"\b(preferred|preferably|desirable|bonus|nice to have|a plus|ideally)\b",
    re.IGNORECASE,
)
_REQUIRED_HEADING_PATTERN = re.compile(
    r"\b(requirements?|qualifications?|responsibilities|what you need|must have)\b",
    re.IGNORECASE,
)
_PREFERRED_HEADING_PATTERN = re.compile(
    r"\b(preferred|desired|nice to have|bonus|a plus)\b",
    re.IGNORECASE,
)
_COMPANY_LABEL_PATTERN = re.compile(
    r"(?im)^\s*(?:company|employer|organization)\s*:\s*([^\n]+)"
)
_COMPANY_HIRING_PATTERN = re.compile(
    r"\b([A-Z][\w&'.-]*(?:\s+[A-Z][\w&'.-]*){0,4})"
    r"\s+(?:is hiring|is seeking|seeks|is looking for)\b"
)
_ROLE_LABEL_PATTERN = re.compile(
    r"(?im)^\s*(?:role|position|job title)\s*:\s*([^\n]+)"
)
_ROLE_PATTERN = re.compile(
    r"\b(?:hiring|seeking|looking for|position(?: of)?|role(?: of)?)"
    r"\s*[:\-]?\s+(?:(?:a|an|the)\s+)?"
    r"([A-Z][A-Za-z0-9+#./&'-]*(?:\s+[A-Z][A-Za-z0-9+#./&'-]*){0,5})"
)
_TITLE_HEADER_PATTERN = re.compile(
    r"(?im)^\s*(?P<company>[A-Z][A-Za-z0-9&'.-]*(?:\s+[A-Z][A-Za-z0-9&'.-]*){0,5})"
    r"\s*(?:—|--|-|\|)\s*(?P<role>[A-Z][A-Za-z0-9+#./&'() -]{2,80})\s*$"
)


def extract_jd_fallback(
    text: str,
    source_file: str,
    *,
    skill_keywords: Mapping[str, SkillRule] | None = None,
) -> ExtractedSkillList:
    """Extract grounded JD fields and known skills without making an LLM call.

    The existing response schema has no separate responsibility or required-skill
    fields; matching skills cite the source sentence as evidence, and preferred
    mentions use ``medium`` confidence. Missing company, role, and skills remain
    null or empty rather than being inferred.
    """
    keyword_rules = skill_keywords if skill_keywords is not None else DEFAULT_SKILL_KEYWORDS
    company = _extract_company(text)
    role = _extract_role(text)
    skills: list[Skill] = []
    seen: set[str] = set()

    for skill_name, rule in keyword_rules.items():
        match = _find_keyword(text, rule.keywords)
        if match is None:
            continue
        normalized_name = skill_name.casefold()
        if normalized_name in seen:
            continue
        seen.add(normalized_name)
        evidence = _evidence_for_match(text, match.start())
        skills.append(
            Skill(
                skill_name=skill_name,
                category_code=rule.category_code,  # Pydantic validates RADIX category membership.
                evidence=evidence,
                confidence="medium" if _is_preferred(text, match.start(), evidence) else "high",
            )
        )

    return ExtractedSkillList(
        source_type="jd",
        source_file=source_file,
        company=company,
        role=role,
        skills=skills,
    )


def _find_keyword(text: str, keywords: tuple[str, ...]) -> re.Match[str] | None:
    for keyword in keywords:
        escaped_keyword = re.escape(keyword).replace(r"\ ", r"\s+")
        pattern = re.compile(rf"(?<!\w){escaped_keyword}(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(text):
            matched_text = match.group(0)
            if keyword == "c" and (
                matched_text != "C" or text[match.end():match.end() + 1] in ("+", "#")
            ):
                continue
            if keyword == "go" and matched_text != "Go":
                continue
            return match
    return None


def _extract_company(text: str) -> str | None:
    match = _COMPANY_LABEL_PATTERN.search(text) or _COMPANY_HIRING_PATTERN.search(text)
    if match:
        return _clean_capture(match.group(1))
    header = _TITLE_HEADER_PATTERN.search(text)
    return _clean_capture(header.group("company")) if header else None


def _extract_role(text: str) -> str | None:
    match = _ROLE_LABEL_PATTERN.search(text) or _ROLE_PATTERN.search(text)
    if match:
        return _clean_capture(match.group(1))
    header = _TITLE_HEADER_PATTERN.search(text)
    return _clean_capture(header.group("role")) if header else None


def _clean_capture(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip(" \t\r\n.,;:!-")
    return cleaned or None


def _evidence_for_match(text: str, position: int) -> str:
    for sentence in re.finditer(r"[^.!?;\n]+(?:[.!?;]|$)", text):
        if sentence.start() <= position < sentence.end():
            return sentence.group(0).strip()
    line_start = text.rfind("\n", 0, position) + 1
    line_end = text.find("\n", position)
    if line_end < 0:
        line_end = len(text)
    return text[line_start:line_end].strip()


def _is_preferred(text: str, position: int, evidence: str) -> bool:
    if _PREFERRED_PATTERN.search(evidence):
        return True

    section = "required"
    for line in text[:position].splitlines():
        heading = line.strip()
        if len(heading) > 100:
            continue
        if _PREFERRED_HEADING_PATTERN.search(heading):
            section = "preferred"
        elif _REQUIRED_HEADING_PATTERN.search(heading):
            section = "required"
    return section == "preferred"
