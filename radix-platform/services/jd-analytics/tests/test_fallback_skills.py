from app.services.llm_fallback import extract_jd_fallback


def test_fallback_extracts_analytics_requirements():
    result = extract_jd_fallback(
        """
        What we're looking for: strong SQL and schema design, data visualization
        with Power BI, quantitative reasoning, statistics, A/B testing, and
        communication with stakeholders.
        """,
        "analyst.docx",
    )

    names = {skill.skill_name for skill in result.skills}
    assert {
        "SQL",
        "Schema Design",
        "Data Visualization",
        "Quantitative Reasoning",
        "Statistics",
        "A/B testing",
        "Communication",
        "Stakeholder Management",
    } <= names


def test_fallback_extracts_engineering_requirements():
    result = extract_jd_fallback(
        """
        Build distributed systems with programming, object-oriented design,
        operating systems, networking, system design, cloud infrastructure,
        software engineering, and Agile practices.
        """,
        "engineer.docx",
    )

    names = {skill.skill_name for skill in result.skills}
    assert {
        "Programming",
        "Object-Oriented Design",
        "Operating Systems",
        "Networking",
        "System Design",
        "Distributed Systems",
        "Cloud Infrastructure",
        "Software Engineering",
        "Agile",
    } <= names


def test_fallback_reads_company_and_role_from_document_heading():
    result = extract_jd_fallback(
        "Microsoft Corporation — Data Analyst\nRole Overview\nBuild dashboards.",
        "microsoft.docx",
    )
    assert result.company == "Microsoft Corporation"
    assert result.role == "Data Analyst"
