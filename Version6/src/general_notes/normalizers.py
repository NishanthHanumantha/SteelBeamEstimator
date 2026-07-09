"""Normalize engineering values extracted from General Notes drawings."""

import re
from typing import Any, Optional

_STEEL_RE = re.compile(r"Fe\s*(\d{3})\s*D?", re.IGNORECASE)
_STEEL_D_RE = re.compile(r"Fe\s*(\d{3})\s*D\b", re.IGNORECASE)
_FY_RE = re.compile(r"FY[-\s]*(\d{3})", re.IGNORECASE)
_CONCRETE_RE = re.compile(r"\bM\s*(\d{2,3})\b", re.IGNORECASE)
_MM_RE = re.compile(r"([\d.]+)\s*mm", re.IGNORECASE)
_NUMBER_RE = re.compile(r"^[\d.]+$")
_DIAMETER_RE = re.compile(r"^(\d{1,2})$")


def normalize_steel_grade(text: str) -> Optional[dict[str, str]]:
    """Map FY-500 / Fe550D style labels to {grade: Fe500} or {grade: Fe550D}."""
    cleaned = text.strip().replace(" ", "")
    fy = _FY_RE.search(cleaned)
    if fy:
        return {"grade": f"Fe{fy.group(1)}"}
    d_match = _STEEL_D_RE.search(cleaned)
    if d_match:
        return {"grade": f"Fe{d_match.group(1)}D"}
    steel = _STEEL_RE.search(cleaned)
    if steel:
        has_d = cleaned.upper().endswith("D") and cleaned.upper().startswith("FE")
        suffix = "D" if has_d else ""
        return {"grade": f"Fe{steel.group(1)}{suffix}"}
    return None


def _valid_concrete_grade_num(value: int) -> bool:
    return 15 <= value <= 60


def normalize_concrete_grade(text: str) -> Optional[dict[str, str]]:
    match = _CONCRETE_RE.search(text.upper())
    if not match:
        return None
    num = int(match.group(1))
    if not _valid_concrete_grade_num(num):
        return None
    return {"grade": f"M{num}"}


def normalize_mm(text: str) -> Optional[dict[str, Any]]:
    match = _MM_RE.search(text)
    if match:
        return {"value_mm": float(match.group(1)), "unit": "mm"}
    if _NUMBER_RE.match(text.strip()):
        return {"value_mm": float(text.strip()), "unit": "mm"}
    return None


def normalize_diameter_mm(text: str) -> Optional[int]:
    stripped = text.strip().replace("mm", "").strip()
    if _DIAMETER_RE.match(stripped):
        value = int(stripped)
        if 6 <= value <= 40:
            return value
    return None


def normalize_db_multiplier(text: str) -> Optional[dict[str, Any]]:
    match = re.search(r"(\d+)\s*x\s*db", text.strip(), re.IGNORECASE)
    if match:
        return {"multiplier": int(match.group(1)), "reference": "bar_diameter"}
    return None


def normalize_angle_degrees(text: str) -> Optional[dict[str, Any]]:
    match = re.search(r"(\d+)\s*(?:%%D|°|deg)", text, re.IGNORECASE)
    if match:
        return {"angle_deg": int(match.group(1)), "unit": "degrees"}
    if _NUMBER_RE.match(text.strip()) and int(text.strip()) in (90, 135, 180, 190):
        return {"angle_deg": int(text.strip()), "unit": "degrees"}
    return None


def extract_all_steel_grades(text_blob: str) -> list[dict[str, str]]:
    grades: list[dict[str, str]] = []
    seen: set[str] = set()
    slash = re.search(r"Fe(\d{3})\s*/\s*(\d{3})D", text_blob, re.IGNORECASE)
    if slash:
        for g in (f"Fe{slash.group(1)}", f"Fe{slash.group(2)}D"):
            if g not in seen:
                seen.add(g)
                grades.append({"grade": g})
    for match in _STEEL_D_RE.finditer(text_blob):
        grade = f"Fe{match.group(1)}D"
        if grade not in seen:
            seen.add(grade)
            grades.append({"grade": grade})
    for match in _STEEL_RE.finditer(text_blob):
        raw = match.group(0)
        suffix = "D" if raw.upper().strip().endswith("D") else ""
        grade = f"Fe{match.group(1)}{suffix}"
        if grade not in seen:
            seen.add(grade)
            grades.append({"grade": grade})
    for match in _FY_RE.finditer(text_blob):
        grade = f"Fe{match.group(1)}"
        if grade not in seen:
            seen.add(grade)
            grades.append({"grade": grade})
    return grades


def extract_all_concrete_grades(text_blob: str) -> list[dict[str, str]]:
    grades: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in _CONCRETE_RE.finditer(text_blob.upper()):
        num = int(match.group(1))
        if not _valid_concrete_grade_num(num):
            continue
        grade = f"M{num}"
        if grade not in seen:
            seen.add(grade)
            grades.append({"grade": grade})
    return grades
