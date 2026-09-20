"""
utils/config.py
----------------
Central configuration for the Tenant Complaint AI Agent project.

Loads environment variables from a .env file (if present) and decides
whether the system runs in DEMO_MODE (no external LLM calls, pure
rule-based / classical-ML pipeline) or LIVE_MODE (uses an OpenAI-style
LLM to enrich summaries and responses, with automatic fallback to
DEMO_MODE if the API call fails for any reason).

This module MUST NOT crash if the .env file is missing or if
python-dotenv is not installed — both are optional conveniences.
"""

import os

# --- Load .env if python-dotenv is available -------------------------------
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    # python-dotenv not installed, or no .env file — that's fine.
    pass

# --- Core settings -----------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# DEMO_MODE is automatically True when no API key is configured.
# It can also be forced on/off explicitly via the FORCE_DEMO_MODE env var.
_forced = os.getenv("FORCE_DEMO_MODE", "").strip().lower()
if _forced in ("true", "1", "yes"):
    DEMO_MODE = True
elif _forced in ("false", "0", "no"):
    DEMO_MODE = False
else:
    DEMO_MODE = len(OPENAI_API_KEY) == 0

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

DB_PATH = os.getenv("DB_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "complaints.db"
))

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ml", "model"
)

SAMPLE_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "sample_complaints.csv"
)

# SLA targets (in hours) by priority level — used for deadline estimation.
SLA_HOURS = {
    "Critical": 2,
    "High": 24,
    "Medium": 72,
    "Low": 168,  # 1 week
}

APP_TITLE = "🏢 TenantCare AI — Intelligent Complaint Management Agent"

CATEGORIES = [
    "Plumbing", "Electrical", "Internet", "Security", "Maintenance",
    "Cleaning", "Noise", "Heating/Cooling", "Appliance", "Structural", "Other",
]

PRIORITIES = ["Critical", "High", "Medium", "Low"]

STATUSES = [
    "Submitted", "AI Analyzed", "Assigned", "In Progress",
    "Waiting for Tenant", "Resolved", "Closed",
]

DEPARTMENTS = [
    "Plumbing Maintenance", "Electrical Maintenance", "IT/Network Support",
    "Security Team", "General Maintenance", "Housekeeping",
    "Resident Relations (Noise)", "HVAC Team", "Appliance Repair",
    "Structural Engineering", "Front Office",
]


def status_banner() -> str:
    """Human-readable one-liner describing the current run mode."""
    if DEMO_MODE:
        return "⚙️ Running in DEMO MODE (rule-based + classical ML, no external LLM calls required)."
    return f"🔌 Running in LIVE MODE (LLM enrichment enabled via {OPENAI_MODEL})."
