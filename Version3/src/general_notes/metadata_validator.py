"""Reject false-positive project metadata values."""

from __future__ import annotations

import re
from typing import Optional

_REJECT_PROJECT_NAME_PATTERNS = (
    "GENERAL NOTES",
    "ALL LEVELS",
    "REFER",
    "NOTE",
    "DRAWING",
    "ARCHITECTURAL",
    "STRUCTURE IS DESIGNED",
    "TEMPORARY",
    "COMPLETION OF THE PROJECT",
    "QST TEAM",
    "CONCRETE SHALL",
)

_REJECT_COMPANY_PATTERNS = (
    "QST TEAM",
    "CONCRETE",
    "REINFORCEMENT",
    "CONSTRUCTION",
    "PROJECT STAKE",
)


def is_valid_project_name(value: Optional[str]) -> bool:
    if not value or not value.strip():
        return False
    upper = value.upper().strip()
    if len(upper) < 3 or len(upper) > 120:
        return False
    if any(token in upper for token in _REJECT_PROJECT_NAME_PATTERNS):
        return False
    if re.match(r"^\d+\.\d+\s", value.strip()):
        return False
    return True


def is_valid_company_name(value: Optional[str]) -> bool:
    if not value or not value.strip():
        return False
    upper = value.upper().strip()
    if len(upper) < 2 or len(upper) > 80:
        return False
    if any(token in upper for token in _REJECT_COMPANY_PATTERNS):
        return False
    return True


def normalize_project_name(raw: str, company_hint: Optional[str] = None) -> str:
    """Normalize title-block project name (e.g. GALERA CLUB HOUSE → Sobha Galera Clubhouse)."""
    cleaned = re.sub(r"\s+", " ", raw.strip())
    upper = cleaned.upper()

    if "CLUB HOUSE" in upper or "CLUBHOUSE" in upper.replace(" ", ""):
        base = "Galera Clubhouse"
    else:
        base = cleaned.title()

    company = (company_hint or "").strip()
    if company and company.upper() not in base.upper():
        return f"{company} {base}"
    return base
