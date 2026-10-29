"""Explicit, documented alias / relation tables for skill matching.

Everything the matcher treats as "the same skill" or "related skill" lives
in this one file so a reviewer can challenge it. Keys and values are in
*normalized* form (see normalizer.py): lowercase, punctuation collapsed to
single spaces, with c++ -> "cplusplus", c# -> "csharp", .net -> "dotnet".

Rules of thumb for editing this file:
  * ALIAS_GROUPS: only truly equivalent names. When in doubt, leave it out.
  * PARTIAL_RELATIONS: related, but one does NOT prove the other.
  * REVIEW_RELATIONS: too generic/ambiguous to count; flagged for a human.
  * Never add: java<->javascript, ai<->machine learning, sql<->postgresql,
    aws<->cloud (as full matches).
"""

from __future__ import annotations

# canonical normalized name -> equivalent normalized names (the canonical
# name itself is implied and need not be repeated).
ALIAS_GROUPS: dict[str, list[str]] = {
    # --- languages -------------------------------------------------------
    "python": ["python programming", "python3", "python 3", "py"],
    "javascript": ["js", "java script", "ecmascript", "es6", "javascript programming"],
    "typescript": ["ts", "typescript programming"],
    "java": ["java programming", "core java", "java se"],
    "cplusplus": ["cpp", "c plus plus"],
    "csharp": ["c sharp", "csharp programming"],
    "golang": ["go lang", "go programming"],
    "c": ["c programming", "c language"],
    "r": ["r programming", "r language"],
    "kotlin": [],
    "rust": [],
    "scala": [],
    "bash": ["shell scripting", "shell script", "bash scripting", "shell"],
    # --- web / frameworks ------------------------------------------------
    "nodejs": ["node js", "node", "node js runtime"],
    "reactjs": ["react", "react js"],
    "angular": ["angularjs", "angular js"],
    "vuejs": ["vue", "vue js"],
    "expressjs": ["express", "express js"],
    "fastapi": ["fast api"],
    "django": [],
    "flask": [],
    "spring boot": ["springboot"],
    "html": ["html5"],
    "css": ["css3"],
    "rest apis": ["rest api", "restful apis", "restful api", "rest", "restful services"],
    # --- data / SQL ------------------------------------------------------
    "postgresql": ["postgres", "postgre sql", "psql"],
    "mysql": ["my sql"],
    "mongodb": ["mongo", "mongo db"],
    "sql": ["structured query language", "sql queries", "sql programming"],
    "nosql": ["no sql", "nosql databases"],
    "pandas": [],
    "numpy": ["num py"],
    "scikit learn": ["sklearn", "scikitlearn"],
    "tensorflow": ["tensor flow"],
    "pytorch": ["py torch", "torch"],
    "machine learning": ["ml"],
    "deep learning": ["dl"],
    "natural language processing": ["nlp"],
    "large language models": ["llm", "llms", "large language model"],
    "data analysis": ["data analytics", "analyzing data", "analysing data"],
    "data visualization": ["data visualisation", "dataviz"],
    "power bi": ["powerbi", "microsoft power bi"],
    "tableau": [],
    "excel": ["microsoft excel", "ms excel"],
    "statistics": ["statistical analysis", "statistical methods"],
    "etl": ["extract transform load", "etl pipelines"],
    # --- CS fundamentals -------------------------------------------------
    "data structures and algorithms": ["dsa", "data structures algorithms", "algorithms and data structures"],
    "data structures": ["data structure"],
    "algorithms": ["algorithm", "algorithmic problem solving"],
    "object oriented programming": ["oop", "oops", "object oriented", "object oriented concepts"],
    "object oriented design": ["ood", "object oriented design principles"],
    "design patterns": ["software design patterns"],
    "system design": ["systems design", "distributed system design", "software architecture design"],
    "operating systems": ["operating system", "os", "os concepts", "os fundamentals"],
    "computer networks": ["networking", "computer networking", "networks", "network fundamentals"],
    "database management systems": ["dbms", "database management", "database systems"],
    "software engineering": ["swe practices", "software engineering practices", "software development lifecycle"],
    "sdlc": ["software development life cycle"],
    "agile": ["agile methodology", "agile methodologies"],
    "version control": ["source control", "git version control"],
    "git": [],
    "unit testing": ["unit tests", "automated testing", "test automation"],
    "ci cd": ["cicd", "continuous integration", "continuous delivery", "continuous integration and continuous delivery"],
    "debugging": ["troubleshooting", "debugging and troubleshooting"],
    "linux": ["unix", "linux unix", "linux administration"],
    # --- cloud / devops --------------------------------------------------
    "aws": ["amazon web services"],
    "azure": ["microsoft azure"],
    "gcp": ["google cloud", "google cloud platform"],
    "cloud computing": ["cloud platforms", "cloud services", "cloud"],
    "docker": ["docker containers"],
    "kubernetes": ["k8s"],
    "microservices": ["microservice architecture", "microservices architecture"],
    "tcp ip": ["tcp ip protocols", "tcpip"],
    # --- soft / aptitude -------------------------------------------------
    "communication": ["communication skills", "verbal communication", "written communication"],
    "problem solving": ["problem solving skills", "analytical thinking", "analytical skills"],
    "logical reasoning": ["quantitative aptitude", "aptitude", "logical and quantitative reasoning"],
    "teamwork": ["collaboration", "team collaboration", "team player"],
    "customer support": ["technical support"],
    # --- AI --------------------------------------------------------------
    "artificial intelligence": ["ai"],
    "generative ai": ["genai", "gen ai", "generative artificial intelligence"],
    "prompt engineering": ["prompting"],
    "langchain": ["lang chain"],
}

# Composite rules: the JD skill is FULLY satisfied only if the candidate
# has *every* skill in at least one of the listed sets (canonical names).
COMPOSITES: dict[str, list[set[str]]] = {
    "data structures and algorithms": [{"data structures", "algorithms"}],
}

# (jd canonical, candidate canonical) -> reason. Related, NOT equivalent.
# Counts as a partial match (0.5) and is listed in partial_matches.
PARTIAL_RELATIONS: dict[tuple[str, str], str] = {
    # DSA halves
    ("data structures and algorithms", "data structures"): "covers only the data-structures half of 'data structures and algorithms'",
    ("data structures and algorithms", "algorithms"): "covers only the algorithms half of 'data structures and algorithms'",
    ("data structures", "data structures and algorithms"): "broader skill that includes data structures",
    ("algorithms", "data structures and algorithms"): "broader skill that includes algorithms",
    # SQL vs concrete databases: related, not interchangeable
    ("sql", "postgresql"): "PostgreSQL is a SQL database, but listing it does not prove general SQL ability",
    ("sql", "mysql"): "MySQL is a SQL database, but listing it does not prove general SQL ability",
    ("postgresql", "sql"): "general SQL does not prove PostgreSQL-specific experience",
    ("mysql", "sql"): "general SQL does not prove MySQL-specific experience",
    ("postgresql", "mysql"): "both are relational SQL databases, but they are different products",
    ("mysql", "postgresql"): "both are relational SQL databases, but they are different products",
    ("sql", "database management systems"): "DBMS knowledge is adjacent to, not the same as, SQL",
    ("database management systems", "sql"): "SQL is one part of database-management knowledge",
    # OOP vs OOD
    ("object oriented design", "object oriented programming"): "OOP is related to, but not the same as, object-oriented design",
    ("object oriented programming", "object oriented design"): "OO design is related to, but not the same as, OOP",
    # AI / ML family: related but explicitly NOT equivalent
    ("machine learning", "deep learning"): "deep learning is a subfield of machine learning but does not prove broader ML",
    ("machine learning", "scikit learn"): "scikit-learn is an ML library; tool use is not full ML competence",
    ("machine learning", "artificial intelligence"): "AI is broader than machine learning; not the same skill",
    ("artificial intelligence", "machine learning"): "machine learning is one part of AI; not the whole field",
    ("artificial intelligence", "deep learning"): "deep learning is one part of AI; not the whole field",
    ("artificial intelligence", "generative ai"): "generative AI is one part of AI; not the whole field",
    ("generative ai", "large language models"): "LLMs are related to, but narrower than, generative AI",
    ("large language models", "generative ai"): "generative AI is broader than LLMs",
    ("deep learning", "tensorflow"): "TensorFlow is a deep-learning framework; tool use is not full DL competence",
    ("deep learning", "pytorch"): "PyTorch is a deep-learning framework; tool use is not full DL competence",
    ("data analysis", "statistics"): "statistics supports, but is not the same as, data analysis",
    ("data analysis", "pandas"): "pandas is a data-analysis tool; tool use is not full analysis skill",
    ("schema design", "normalized schema"): "a normalized schema demonstrates schema-design work, but not every schema-design concern",
    ("data visualization", "power bi"): "Power BI is a visualization tool; its use supports, but does not prove, all visualization practice",
    ("data visualization", "excel"): "Excel can be used for visualization; the listed tool alone does not prove dashboard design",
    ("communication", "presentation"): "presenting findings demonstrates communication in that context",
    ("quantitative reasoning", "statistics"): "statistics supports quantitative reasoning, but does not prove every reasoning context",
    ("quantitative reasoning", "a b testing"): "A/B testing demonstrates quantitative reasoning in an experimentation context",
    ("logical reasoning", "statistics"): "statistics supports logical reasoning, but does not prove every reasoning context",
    ("logical reasoning", "a b testing"): "A/B testing demonstrates structured reasoning in an experimentation context",
    # Cloud: specific provider vs the general skill
    ("cloud computing", "aws"): "AWS is one cloud provider; general cloud knowledge is not proven",
    ("cloud computing", "azure"): "Azure is one cloud provider; general cloud knowledge is not proven",
    ("cloud computing", "gcp"): "GCP is one cloud provider; general cloud knowledge is not proven",
    ("aws", "azure"): "different cloud providers with overlapping concepts",
    ("azure", "aws"): "different cloud providers with overlapping concepts",
    ("aws", "gcp"): "different cloud providers with overlapping concepts",
    ("gcp", "aws"): "different cloud providers with overlapping concepts",
    ("azure", "gcp"): "different cloud providers with overlapping concepts",
    ("gcp", "azure"): "different cloud providers with overlapping concepts",
    ("kubernetes", "docker"): "container basics are related to, but not the same as, Kubernetes",
    ("docker", "kubernetes"): "Kubernetes experience implies container familiarity but is not proof of Docker use",
    ("microservices", "system design"): "system design is broader than microservices",
    ("system design", "microservices"): "microservices is one aspect of system design",
    ("system design", "design patterns"): "design patterns are related to, but not the same as, system design",
    ("programming", "python"): "Python is a programming language and demonstrates programming ability, but not every programming context",
    ("programming", "java"): "Java is a programming language and demonstrates programming ability, but not every programming context",
    ("programming", "javascript"): "JavaScript is a programming language and demonstrates programming ability, but not every programming context",
    ("coding", "python"): "Python is a programming language and demonstrates coding ability, but not every coding context",
    ("coding", "java"): "Java is a programming language and demonstrates coding ability, but not every coding context",
    ("coding", "javascript"): "JavaScript is a programming language and demonstrates coding ability, but not every coding context",
    # Web
    ("javascript", "typescript"): "TypeScript builds on JavaScript but this is not a guaranteed equivalence",
    ("typescript", "javascript"): "JavaScript experience does not prove TypeScript",
    ("rest apis", "fastapi"): "FastAPI is a framework for building REST APIs; related, not identical",
    ("rest apis", "expressjs"): "Express is a framework for building REST APIs; related, not identical",
    ("rest apis", "django"): "Django can build REST APIs; related, not identical",
    ("rest apis", "flask"): "Flask can build REST APIs; related, not identical",
    ("rest apis", "spring boot"): "Spring Boot can build REST APIs; related, not identical",
    # Engineering practice
    ("version control", "git"): "Git is a version-control tool; related, not identical to the general practice",
    ("git", "version control"): "general version-control practice does not prove Git use",
    ("software engineering", "sdlc"): "SDLC knowledge is one part of software engineering",
    ("sdlc", "agile"): "Agile is one SDLC approach",
    ("agile", "sdlc"): "SDLC knowledge is related to, but not the same as, Agile",
    ("unit testing", "debugging"): "debugging is adjacent to, not the same as, testing",
    ("ci cd", "git"): "Git is adjacent to, but not the same as, CI/CD",
    ("customer support", "communication"): "communication supports, but is not the same as, customer support",
    ("problem solving", "algorithms"): "algorithmic work is one form of problem solving",
    ("problem solving", "data structures and algorithms"): "DSA work is one form of problem solving",
    ("linux", "bash"): "shell scripting is adjacent to, not the same as, Linux experience",
    ("operating systems", "linux"): "Linux is one operating system; OS concepts are not fully proven",
    ("computer networks", "tcp ip"): "TCP/IP is one part of computer networking",
    ("networking", "tcp ip"): "TCP/IP is one part of computer networking",
}

# (jd canonical, candidate canonical) -> reason. Too generic / ambiguous to
# score: the matcher marks these review_required (0 points) so a human
# can decide. Never silently counted.
REVIEW_RELATIONS: dict[tuple[str, str], str] = {
    ("aws", "cloud computing"): "generic 'cloud' skill does not show AWS-specific experience",
    ("azure", "cloud computing"): "generic 'cloud' skill does not show Azure-specific experience",
    ("gcp", "cloud computing"): "generic 'cloud' skill does not show GCP-specific experience",
    ("machine learning", "data analysis"): "data analysis may or may not involve machine learning",
    ("deep learning", "machine learning"): "general ML does not show deep-learning experience",
    ("python", "pandas"): "pandas implies Python use but the candidate did not list Python itself",
    ("python", "scikit learn"): "scikit-learn implies Python use but the candidate did not list Python itself",
    ("javascript", "reactjs"): "React implies JavaScript use but the candidate did not list JavaScript itself",
    ("javascript", "nodejs"): "Node.js implies JavaScript use but the candidate did not list JavaScript itself",
    ("java", "spring boot"): "Spring Boot implies Java use but the candidate did not list Java itself",
}

# Normalized names too short/generic to use for phrase-containment matching.
CONTAINMENT_BLOCKLIST: frozenset[str] = frozenset(
    {"c", "r", "go", "os", "ai", "ml", "dl", "js", "ts", "it", "ui", "ux", "api", "sql", "node", "web", "data", "cloud", "design", "testing", "software"}
)
