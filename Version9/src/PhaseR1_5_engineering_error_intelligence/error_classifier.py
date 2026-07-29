"""
Map R.1.4 findings into deterministic engineering categories.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from engineering_issue_model import ENGINEERING_CATEGORIES

MODEL_VERSION = "8.7.0"

_ROLE_CATEGORY = {
    "STIRRUP": "Stirrup Interpretation",
    "STIRRUP_HOOK": "Hook Interpretation",
    "SPACER_BAR": "Spacer Interpretation",
    "SIDE_FACE_REINFORCEMENT": "Side Face Reinforcement",
    "TOP_MAIN": "Role Classification",
    "TOP_EXTRA": "Role Classification",
    "BOTTOM_MAIN": "Role Classification",
    "BOTTOM_EXTRA": "Role Classification",
}

_ERROR_TYPE_CATEGORY = {
    "Missing Beam": "Beam Discovery",
    "Extra Beam": "Annotation Association",
    "Wrong Diameter": "Diameter Interpretation",
    "Wrong Quantity": "Quantity Interpretation",
    "Wrong Cut Length": "Cut Length",
    "Wrong Steel": "Steel Aggregation",
    "Wrong Weight": "Weight Calculation",
    "Wrong Piece Type": "Piece Generation",
    "Wrong Shape": "Piece Generation",
    "Wrong Classification": "Role Classification",
    "Wrong BBS": "Steel Aggregation",
    "Wrong Workbook Output": "Workbook Export",
}


def extract_role(message: str) -> str:
    m = re.search(r"\(([^)]+)\)\s*$", message or "")
    if not m:
        return ""
    role = m.group(1).strip().upper()
    # ignore non-role parentheses (e.g. steel comparison text)
    if role in _ROLE_CATEGORY or role.endswith("_MAIN") or role.endswith("_EXTRA"):
        return role
    if role in ("STIRRUP", "STIRRUP_HOOK", "SPACER_BAR", "SIDE_FACE_REINFORCEMENT"):
        return role
    return ""


def extract_diameter(message: str, entity: str) -> int:
    text = f"{entity} {message}"
    m = re.search(r"(?:DIA[_ ]?|Diameter\s+)?(\d{1,2})\s*mm", text, re.I)
    if m:
        d = int(m.group(1))
        return d if d in (8, 10, 12, 16, 20, 25, 32) else 0
    m = re.search(r"\bDIA_(\d{1,2})\b", text, re.I)
    if m:
        d = int(m.group(1))
        return d if d in (8, 10, 12, 16, 20, 25, 32) else 0
    return 0


def classify_finding(error_type: str, message: str, role: str = "") -> Tuple[str, str]:
    """Return (category, subcategory). Always one of ENGINEERING_CATEGORIES."""
    role = role or extract_role(message)
    if error_type == "Missing Reinforcement Row":
        cat = _ROLE_CATEGORY.get(role, "Role Classification")
        sub = role or "UNKNOWN_ROLE"
        return cat, sub

    cat = _ERROR_TYPE_CATEGORY.get(error_type, "Unknown")
    if cat not in ENGINEERING_CATEGORIES:
        cat = "Unknown"
    sub = role or error_type
    return cat, sub


class ErrorClassifier:
    def classify(self, error_type: str, message: str, entity: str = "") -> dict:
        role = extract_role(message)
        dia = extract_diameter(message, entity)
        category, subcategory = classify_finding(error_type, message, role)
        return {
            "category": category,
            "subcategory": subcategory,
            "role": role,
            "diameter": dia,
        }
