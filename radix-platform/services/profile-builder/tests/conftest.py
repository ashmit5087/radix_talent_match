import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from app.repositories.profile_repository import get_profile_repository
from app.database import reset_supabase_client_for_testing


@pytest.fixture(autouse=True)
def clean_repository_state():
    """Ensures each test has an isolated in-memory repository state."""
    reset_supabase_client_for_testing()
    repo = get_profile_repository()
    repo.clear_all()
    yield repo
    repo.clear_all()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def sample_profile_payload():
    """Provides a realistic candidate profile creation payload."""
    return {
        "personal_info": {
            "full_name": "Karthik Subramaniam",
            "email": "karthik.sub@example.com",
            "phone": "+91 99887 76655",
            "location": "Bengaluru, India",
            "summary": "Data-leaning software engineer experienced in analytics pipelines and backend microservices.",
            "linkedin_url": "https://linkedin.com/in/karthik-sub",
            "github_url": "https://github.com/karthik-sub",
            "portfolio_url": "https://karthik.ai",
            "source": "manual",
        },
        "education": [
            {
                "institution": "PES University",
                "degree": "B.Tech Computer Science",
                "field_of_study": "Data Science",
                "start_date": "2021-08",
                "end_date": "2025-05",
                "grade": "8.7 / 10",
                "details": "Coursework in Machine Learning, Algorithms, and Distributed Computing.",
                "source": "manual",
            }
        ],
        "skills": [
            {
                "skill_name": "Python",
                "category_code": "COD",
                "evidence": "Engineered ETL data processing pipelines and FastAPI APIs",
                "confidence": 0.92,
                "source": "manual",
            },
            {
                "skill_name": "SQL & Analytical Queries",
                "category_code": "SQL",
                "evidence": "Optimized PostgreSQL indexes and wrote window aggregation queries",
                "confidence": 0.88,
                "source": "manual",
            },
            {
                "skill_name": "Algorithms & Complexity",
                "category_code": "DSA",
                "evidence": "Applied dynamic programming and graph shortest-path algorithms",
                "confidence": "high",
                "source": "manual",
            },
        ],
        "projects": [
            {
                "name": "Customer Churn Predictor",
                "description": "End-to-end ML training and serving pipeline using scikit-learn and FastAPI.",
                "technologies": ["Python", "FastAPI", "scikit-learn", "Docker"],
                "link": "https://github.com/karthik-sub/churn-prediction",
                "start_date": "2024-01",
                "end_date": "2024-03",
                "source": "manual",
            }
        ],
        "hackathons": [
            {
                "entry_type": "hackathon",
                "organization": "HackNITR",
                "title": "Track Winner - AI Analytics",
                "start_date": "2023-10",
                "end_date": "2023-10",
                "description": "Created automated financial transaction anomaly detector.",
                "source": "manual",
            }
        ],
        "internships": [
            {
                "entry_type": "internship",
                "organization": "DataForge Analytics",
                "title": "Data Engineering Intern",
                "start_date": "2024-06",
                "end_date": "2024-08",
                "description": "Built automated data ingestion pipelines processing 500k records daily.",
                "source": "manual",
            }
        ],
        "certifications": [
            {
                "name": "Databricks Certified Associate Developer for Apache Spark",
                "issuer": "Databricks",
                "issue_date": "2024-04",
                "credential_url": "https://credentials.databricks.com/mock-spark-123",
                "source": "manual",
            }
        ],
        "preferred_roles": ["Data Analyst", "Data Engineer", "Backend Engineer"],
        "cv_file": "karthik_resume.pdf",
    }
