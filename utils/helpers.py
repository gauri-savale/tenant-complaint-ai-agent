"""
utils/helpers.py
-----------------
Small, dependency-free helper functions used across the project:
ID generation, timestamp handling, and SLA deadline math.
"""

import random
import string
import uuid
from datetime import datetime, timedelta

from utils.config import SLA_HOURS


def generate_complaint_id() -> str:
    """Generate a short, human-friendly, unique complaint ID e.g. CMP-3F9A2C."""
    suffix = uuid.uuid4().hex[:6].upper()
    return f"CMP-{suffix}"


def generate_tenant_id(name: str) -> str:
    """Generate a deterministic-looking tenant ID from a name (demo helper)."""
    base = "".join(c for c in name.upper() if c.isalpha())[:3] or "TEN"
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{base}-{suffix}"


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_hours_iso(hours: float, from_time: str = None) -> str:
    """Return an ISO timestamp `hours` in the future from `from_time` (or now)."""
    base = datetime.strptime(from_time, "%Y-%m-%d %H:%M:%S") if from_time else datetime.now()
    return (base + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")


def sla_deadline(priority: str, submitted_at: str = None) -> str:
    hours = SLA_HOURS.get(priority, SLA_HOURS["Medium"])
    return add_hours_iso(hours, submitted_at)


def hours_until(deadline_iso: str) -> float:
    """Hours remaining until an ISO deadline (negative if already breached)."""
    deadline = datetime.strptime(deadline_iso, "%Y-%m-%d %H:%M:%S")
    delta = deadline - datetime.now()
    return round(delta.total_seconds() / 3600, 1)


def is_sla_breached(deadline_iso: str, status: str) -> bool:
    if status in ("Resolved", "Closed"):
        return False
    return hours_until(deadline_iso) < 0


def safe_str(value, default="N/A") -> str:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    return str(value)
