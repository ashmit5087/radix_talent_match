# RADIX Candidate Assessment Platform — Role 4: Talent Check & Profile Auditor

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Proprietary-orange.svg)](#)
[![Deterministic Engine](https://img.shields.io/badge/Scoring-100%25%20Deterministic%20(No%20LLMs)-brightgreen.svg)](#)

A high-performance, deterministic candidate readiness assessment engine and web footprint verification platform built for the **RADIX Talent Match Hackathon**.

Evaluates engineering candidates against **115 target enterprise hiring benchmarks** across the **12 RADIX competency skillsets**, computing objective readiness scores (0–100), critical gap analyses, and live **GitHub & LeetCode** corporate level audits (0.0–10.0).

---

## 📑 Table of Contents
1. [System Architecture](#-system-architecture)
2. [The 12 RADIX Competency Framework](#-the-12-radix-competency-framework)
3. [Core Engines & Mathematical Models](#-core-engines--mathematical-models)
   - [Layer A: Evidence Points & Saturating Curve](#layer-a-evidence-points--saturating-exponential-curve)
   - [Layer B: Deterministic Readiness Scoring](#layer-b-deterministic-readiness-scoring)
   - [Web-Level Profile Auditor (GitHub & LeetCode)](#web-level-profile-auditor-github--leetcode)
4. [Performance & Latency Profile](#-performance--latency-profile)
5. [Repository Structure](#-repository-structure)
6. [Quick Start & CLI Commands](#-quick-start--cli-commands)
7. [REST API Endpoints](#-rest-api-endpoints)
8. [Data Contracts](#-data-contracts)

---

## 🏛 System Architecture

```
                    ┌───────────────────────────────────────────────┐
                    │          Candidate Resume / Profile           │
                    │   (Skills, Experience, Projects, Hackathons)  │
                    └───────────────────────┬───────────────────────┘
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               ▼                                                         ▼
┌───────────────────────────────┐                       ┌───────────────────────────────┐
│     TALENT CHECK (ROLE 4)     │                       │     WEB PROFILE AUDITOR       │
│   Deterministic Core Engine   │                       │   Public Footprint Scraper    │
├───────────────────────────────┤                       ├───────────────────────────────┤
│ • Layer A: Evidence Points    │                       │ • GitHub API Audit:           │
│   (Skills + Work + Projects)  │                       │   - Anti-fork segregation     │
│ • Saturating Curve (k=2.0)    │                       │   - Language breadth & stars  │
│   → Derived Levels (0–10)     │                       │   - Commit recency            │
│ • Layer B: Company Benchmark  │                       │ • LeetCode GraphQL Audit:     │
│   (115 Companies, 12 Skills)  │                       │   - Easy/Med/Hard breakdown   │
│ • Requirement-Weighted Score  │                       │   - Contest ratings           │
│ • Critical Gap Detection (≥4) │                       │ • Strict Level Rubric (0–10)  │
└──────────────┬────────────────┘                       └──────────────┬────────────────┘
               │                                                       │
               └────────────────────────────┬──────────────────────────┘
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │               Evaluation Report               │
                    │  • Readiness Score (0–100) & Verdict          │
                    │  • 12-Skillset Gaps & Prioritized Remediation │
                    │  • Verified vs Unverified Skills Audit        │
                    │  • Official RADIX JSON Contract Export        │
                    └───────────────────────────────────────────────┘
```

---

## 🎯 The 12 RADIX Competency Framework

Every candidate and company is evaluated across 12 standardized engineering competencies mapped to Bloom's taxonomy cognitive levels:

| Code | Competency Name | Primary Focus | Cognitive Tiers |
| :--- | :--- | :--- | :--- |
| **`COD`** | Coding | Syntax, Core Languages (Python, Java, C++, Go, Rust) | `CU` (Conceptual) |
| **`DSA`** | Data Structures & Algorithms | Problem Solving, Graph Theory, DP, Complexity | `AP` (Application) |
| **`OOD`** | Object-Oriented Design | Clean Architecture, SOLID, Design Patterns, UML | `AS` (Analysis) |
| **`APTI`** | Aptitude & Problem Solving | Analytical Reasoning, Logic, Quantitative Modeling | `EV` (Evaluation) |
| **`COMM`** | Communication Skills | Stakeholder Management, Mentorship, Tech Writing | `CR` (Creation) |
| **`AI`** | AI Native Engineering | ML/DL Pipelines, LLMs, RAG, PyTorch, Embeddings | — |
| **`CLOUD`** | DevOps & Cloud | AWS, Azure, GCP, Docker, Kubernetes, CI/CD, Terraform | — |
| **`SQL`** | SQL & Database Design | PostgreSQL, MySQL, Query Optimization, Warehousing | — |
| **`SWE`** | Software Engineering | Testing (QA/PyTest), Git Workflows, Agile/Scrum, SDLC | — |
| **`SYSD`** | System Design & Architecture | Scalability, High Availability, Distributed Systems | — |
| **`NETW`** | Computer Networking | TCP/IP, Sockets, HTTP/REST, WebSockets, TLS | — |
| **`OS`** | Operating Systems | Linux Internals, Concurrency, Threads, Memory Mgmt | — |

---

## 🧮 Core Engines & Mathematical Models

### Layer A: Evidence Points & Saturating Exponential Curve

To prevent "resume fluff" (a candidate listing 20 keywords automatically getting 10/10), points are aggregated from qualitative resume proof and mapped through an asymptotic saturating curve:

#### 1. Evidence Points Source Weighting
| Source in Candidate Profile | Assigned Evidence Points |
| :--- | :--- |
| **Skill (`confidence: high`)** | **+1.0 pt** |
| **Skill (`confidence: medium`)** | **+0.6 pt** |
| **Skill (`confidence: low`)** | **+0.3 pt** |
| **Internship / Real-World Work** | **+1.5 pts** *(Work counts more than a listed skill)* |
| **Hackathon Experience** | **+1.0 pt** |
| **Certification** | **+1.0 pt** |
| **Project** | **+1.0 pt** |

*Includes automatic deduplication of identical items across sections and dynamic recovery of untagged/`OTHER` skills.*

#### 2. Saturating Exponential Curve Formula
$$\text{level} = \text{round}\left(10 \times \left(1 - e^{-\frac{\text{points}}{k}}\right)\right), \quad k = 2.0$$

The curve rises quickly for initial proof and flattens out, ensuring high levels (8–10) strictly require substantial real-world projects and verified experience:

| Raw Points | Derived Level (0–10) | Representation |
| :---: | :---: | :--- |
| **0.0** | **0** | No demonstrated competency |
| **1.0** | **2** | Novice / Theoretical grasp |
| **3.0** | **5** | Working competent practitioner |
| **5.0** | **7** | Strong applied professional |
| **8.0** | **9** | Senior subject-matter specialist |
| **12.0+** | **10** | Mastery bar |

---

### Layer B: Deterministic Readiness Scoring

Company benchmarks are loaded from **115 normalized enterprise profiles** (1,380 requirement cells) parsed from [`staging_company_skill_levels_rows.sql`](file:///c:/Users/vishu/Documents/CodeBase/Radix/staging_company_skill_levels_rows.sql).

#### Weighted Readiness Formula
$$\text{Readiness Score} = \text{round}\left(100 \times \frac{\sum_{i=1}^{12} \text{ratio}_i \times \text{weight}_i}{\sum_{i=1}^{12} \text{weight}_i}\right)$$

Where:
- $\text{ratio}_i = \min\left(\frac{\text{candidate\_level}_i}{\text{required\_level}_i}, 1.0\right)$
- $\text{weight}_i = \text{required\_level}_i$ *(Higher company bars naturally carry higher weighting)*
- $\text{gap\_size}_i = \max(\text{required\_level}_i - \text{candidate\_level}_i, 0)$
- **Critical Gap:** Flagged when $\text{gap\_size}_i \ge 4$ (`CRITICAL_GAP_MIN` in `scoring.py`; also returned as `summary.critical_gap_min`). Gaps of 1-3 are scored gaps.
- **Role 5 contract:** Skill Matching reads `summary.critical_categories` from this result, so there is exactly one definition of "critical".

#### Readiness Verdicts
- **Ready** ($\text{Score} \ge 88$ & $0$ Critical Gaps): Meets or exceeds the target company's bar.
- **Close** ($\text{Score} \ge 70$ & $\le 2$ Critical Gaps): Strong competitive match with targeted gaps to bridge.
- **Needs Work** ($\text{Score} < 70$ or $> 2$ Critical Gaps): Significant remediation required.

---

### Web-Level Profile Auditor (GitHub & LeetCode)

Located in [`web-level-scrapping/`](file:///c:/Users/vishu/Documents/CodeBase/Radix/web-level-scrapping), this module audits public footprints to verify candidate claims:

- **GitHub Scraper:**
  - **Anti-Fork Auditing:** Filters out cloned/forked code from genuine authored repos.
  - Measures commit recency (past 365 days), language distribution, and stars.
  - Semantic cross-referencing of claimed skills and projects.
- **LeetCode Scraper:**
  - Direct query to LeetCode's public GraphQL endpoint.
  - Granular **Easy**, **Medium**, and **Hard** solution counts and contest ratings.
- **Strict Corporate Leveling (0.0 – 10.0):**
  - **L0 (0.0–1.4):** Trainee / Unverified (no public proof or $<50$ LeetCode).
  - **L1 (1.5–2.9):** Junior Software Engineer (academic/trivial codebases).
  - **L2 (3.0–4.9):** Mid-Level Software Engineer (active commits, solid Medium DSA).
  - **L3 (5.0–6.9):** Senior Software Engineer ($\ge 3$ original repos, 40+ Med/Hard DSA).
  - **L4 (7.0–8.4):** Staff Software Engineer (stars, community adoption, 120+ Med/Hard DSA).
  - **L5 (8.5–9.4):** Principal Software Engineer (distributed systems, 20+ stars).
  - **L6+ (9.5–10.0):** Distinguished / Fellow (viral open-source, Guardian top 1%).

---

## ⚡ Performance & Latency Profile

Benchmarked on production hardware using high-resolution performance timers (`time.perf_counter()`):

| Sub-System | Execution Latency | Throughput |
| :--- | :---: | :---: |
| **Layer B Scoring Math** | **$0.017\text{ ms}$** ($17\ \mu\text{s}$) | $\approx 58,000\text{ evals/sec}$ |
| **Layer A Level Extraction** | **$0.277\text{ ms}$** ($277\ \mu\text{s}$) | $\approx 3,600\text{ profiles/sec}$ |
| **Full Talent Check Pipeline** | **$0.294\text{ ms}$** ($294\ \mu\text{s}$) | **$> 3,400\text{ evals/sec}$** |
| **Web-Level Public Footprint Audit** | **$\approx 0.500\text{ s}$** | Network I/O bound |

---

## 📁 Repository Structure

```
.
├── companies.json                           # Clean 115-company requirements database
├── staging_company_skill_levels_rows.sql    # Raw SQL source benchmark data
├── README.md                                # Platform documentation
├── talent_check/                            # Role 4 Talent Check Core Package
│   ├── cli.py                               # Terminal CLI & contract exporter
│   ├── test_scoring.py                      # Test suite: saturating curve & sanity checks
│   ├── test_companies_json.py               # Test suite: 115-company JSON validation
│   ├── backend/
│   │   ├── levels.py                        # Layer A: Points aggregator & saturating curve
│   │   ├── scoring.py                       # Layer B: Deterministic gap & readiness engine
│   │   ├── loader.py                        # SQL to JSON parser & deduplicator
│   │   └── api.py                           # FastAPI REST service
│   └── data/
│       ├── companies.json                   # Local data store copy
│       └── mock_profiles/                   # Canonical test profiles
│           ├── ananya_rao.json              # Systems generalist (OS/NETW/SWE)
│           ├── karthik_subramaniam.json     # Data analyst (SQL/AI/APTI)
│           ├── priya_menon.json             # Support & DB analyst (Oracle FSS fit)
│           └── rohan_verma.json             # High all-rounder full-stack candidate
└── web-level-scrapping/                     # Public Footprint Auditor Package
    ├── cli.py                               # Web audit terminal runner
    ├── github_scraper.py                    # GitHub REST API & anti-fork auditor
    ├── leetcode_scraper.py                  # LeetCode GraphQL API scraper
    ├── skill_matcher.py                     # Corroborator & strict leveling rubric
    └── sample_parsed_resumes.json           # Sample candidate input file
```

---

## 🚀 Quick Start & CLI Commands

### 1. Prerequisites & Installation
```bash
# Clone the repository
git clone https://github.com/ashmit5087/candidate-assessment-platform.git
cd candidate-assessment-platform

# Install dependencies
pip install -r web-level-scrapping/requirements.txt
```

### 2. Run Test Suites
```bash
# Verify Layer A saturating curve math & Layer B benchmark scoring
python -m talent_check.test_scoring

# Verify companies.json database integrity (all 115 companies & 1,380 cells)
python -m talent_check.test_companies_json
```

### 3. Run Talent Check CLI
```bash
# Evaluate a candidate against a target company (Visual Terminal Report)
python -m talent_check.cli --candidate priya_menon --company "Oracle Financial"

# Evaluate using a custom k-factor (e.g. k=1.5 or k=2.5; default is 2.0)
python -m talent_check.cli --candidate priya_menon --company "Google" --k-factor 4.0

# Export official RADIX JSON contract
python -m talent_check.cli --candidate priya_menon --company "Google" --format contract

# Batch evaluate all mock profiles against a company
python -m talent_check.cli --candidate all --company "Microsoft"

# List available companies or candidate profiles
python -m talent_check.cli --list-companies
python -m talent_check.cli --list-candidates
```

### 4. Run Web-Level Profile Auditor
```bash
# Run audit on a parsed resume file
python web-level-scrapping/cli.py --input web-level-scrapping/sample_parsed_resumes.json

# Audit a candidate with live GitHub and LeetCode handles
python web-level-scrapping/cli.py -g torvalds -l neetcode
```

---

## 🌐 REST API Endpoints

Start the FastAPI service:
```bash
python -m uvicorn talent_check.backend.api:app --reload --port 8000
```
Interactive Swagger API documentation: `http://localhost:8000/docs`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health status and category count |
| `GET` | `/api/categories` | Metadata for all 12 RADIX categories & tier definitions |
| `GET` | `/api/companies` | List & filter hiring company benchmark profiles |
| `GET` | `/api/companies/{id}` | Detailed hiring benchmarks for a specific company |
| `GET` | `/api/candidates` | List built-in mock candidate profiles |
| `POST` | `/api/talent-check` | Full Talent Check: runs Layer A & Layer B evaluation |
| `POST` | `/api/talent-check/direct` | Direct simulation: evaluates raw `{CODE: level}` dict |

---

## 📋 Data Contracts

### 1. Candidate Input Contract (Role 3 $\rightarrow$ Role 4)
```json
{
  "name": "Priya Menon",
  "skills": [
    { "skill_name": "SQL", "category_code": "SQL", "confidence": "high" },
    { "skill_name": "Java", "category_code": "COD", "confidence": "medium" },
    { "skill_name": "Linux", "category_code": "OS", "confidence": "medium" }
  ],
  "experience": [
    "IT Support desk at local business — handled first-level troubleshooting"
  ],
  "projects": [
    "Built attendance tracker using Java and MySQL backend"
  ]
}
```

### 2. Talent Check Output Contract (Role 4 Shared Schema)
```json
{
  "company": "Oracle Financial Services Software Limited",
  "company_id": 24,
  "readiness_score": 59,
  "verdict": "Needs Work",
  "verdict_badge": "danger",
  "skillset_gap": [
    {
      "category_code": "SQL",
      "category_name": "SQL & Design",
      "required_level": 6,
      "required_tier": "AP",
      "tier_name": "Application",
      "candidate_level": 5,
      "gap": true,
      "gap_size": 1,
      "ratio": 0.833,
      "evidence_points": 2.6
    }
  ],
  "summary": {
    "total_categories": 12,
    "met_count": 5,
    "gap_count": 7,
    "critical_gap_count": 3,
    "critical_categories": ["SWE", "DSA", "OOD"]
  },
  "focus_areas": [
    {
      "code": "SWE",
      "name": "Software Engineering",
      "required": 7,
      "current": 0,
      "gap": 7,
      "target_tier": "AS (Analysis & Assessment)"
    }
  ]
}
```
