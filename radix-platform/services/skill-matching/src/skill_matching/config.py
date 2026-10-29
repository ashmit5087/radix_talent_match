"""Configuration defaults. No secrets live here."""

import os

ALGORITHM_VERSION = "1.0.0"
SERVICE_NAME = "radix-role5-skill-matching"

# Score contribution per match status (spec section 4.3).
STATUS_SCORE = {
    "matched": 1.0,
    "partial": 0.5,
    "review_required": 0.0,
    "missing": 0.0,
}

# Output length limit for preserved upstream evidence strings.
MAX_EVIDENCE_CHARS = 300

# Default API port (spec section 6).
DEFAULT_HOST = os.environ.get("SKILL_MATCH_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("SKILL_MATCH_PORT", "8005"))

# Role 4 Talent Check integration. gap = required_level - candidate_level.
# gap <= 0            : no gap, full credit
# 0 < gap <= 3        : scored gap, credit scaled by candidate_level / required_level
# gap > 3 (critical)  : taken straight from Role 4 as missing; skill matching is skipped
# Fallback only: when Role 4 sends summary.critical_categories, that list is used instead (one definition).
CRITICAL_GAP_MIN = 4

# Optional LLM layer (any OpenAI-compatible endpoint: OpenAI, xAI Grok, OpenRouter, Ollama...).
# Read from the environment only; never hard-code keys.
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_TIMEOUT_S = float(os.environ.get("LLM_TIMEOUT_S", "20"))
