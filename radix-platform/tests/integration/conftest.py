"""
RADIX Platform — Cross-service Integration Tests
================================================
Tests live endpoints. All 5 services must be running before executing.

Start services:
    cd radix-platform && .\\scripts\\dev.ps1

Run tests:
    cd radix-platform/tests/integration
    python -m pytest . -v

Environment variables (optional overrides):
    ROLE1_URL  ROLE2_URL  ROLE3_URL  ROLE4_URL  ROLE5_URL
"""

import os

ROLE1 = os.getenv("ROLE1_URL", "http://localhost:8001")
ROLE2 = os.getenv("ROLE2_URL", "http://localhost:8002")
ROLE3 = os.getenv("ROLE3_URL", "http://localhost:8003")
ROLE4 = os.getenv("ROLE4_URL", "http://localhost:8004")
ROLE5 = os.getenv("ROLE5_URL", "http://localhost:8005")

