"""
Stirrup Annotation Parser — Phase SI.0 MODULE 2

Parses stirrup callout text into structured fields.
Returns a plain dict to avoid cross-package imports.
"""
import re
from typing import Dict, Any, List

_LABEL_RE = re.compile(
    r"(?P<legs>\d+)?L?-?Y(?P<dia>\d+(?:\.\d+)?)@(?P<spacings>[\d/]+)",
    re.IGNORECASE,
)


def parse_stirrup_callout(
    callout: str,
    default_legs: int = 2,
    default_grade: str = "Y",
) -> Dict[str, Any]:
    """
    Returns a dict with keys:
      legs, diameter_mm, steel_grade, spacings_mm, stirrup_type,
      is_parseable, bar_label
    """
    callout_clean = (callout or "").strip().replace(" ", "")
    m = _LABEL_RE.search(callout_clean)
    if not m:
        return {
            "legs": default_legs,
            "diameter_mm": None,
            "steel_grade": default_grade,
            "spacings_mm": [],
            "stirrup_type": "UNKNOWN",
            "is_parseable": False,
            "bar_label": callout_clean,
        }

    legs = int(m.group("legs") or default_legs)
    dia  = float(m.group("dia"))
    raw  = m.group("spacings")
    spacings: List[int] = [int(x) for x in raw.split("/") if x.isdigit()]
    stype = "UNIFORM" if len(spacings) == 1 else "VARIABLE"

    s_str = "/".join(str(s) for s in spacings)
    label = f"{legs}L-Y{int(dia)}@{s_str}"

    return {
        "legs": legs,
        "diameter_mm": dia,
        "steel_grade": default_grade,
        "spacings_mm": spacings,
        "stirrup_type": stype,
        "is_parseable": True,
        "bar_label": label,
    }
