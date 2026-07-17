"""
Stirrup Role Validator — Phase SI.0 MODULE 4

Examines each L.2 STIRRUP object and decides whether it is genuinely a
stirrup annotation or a misclassified longitudinal bar.

INVALID patterns:
  bar_label = "2Y16", "2Y20", "4Y16", etc.  (no '@')
  spacing_mm is None
  callout has no '@' sign

VALID:
  bar_label contains '@' and a spacing value
"""
import re
from typing import Optional, Tuple
from si0_stirrup_recovery_models import InvalidReason

_AT_REQUIRED = re.compile(r"@\d+", re.IGNORECASE)

# Known longitudinal bar patterns that are never stirrups
_LONGITUDINAL_RE = re.compile(
    r"^(\d+)Y(\d+)$",   # e.g. "2Y16", "4Y20"
    re.IGNORECASE,
)


def is_valid_stirrup(bar: dict) -> Tuple[bool, Optional[InvalidReason]]:
    """
    Returns (True, None) if bar is a genuine stirrup.
    Returns (False, reason) if it is invalid.
    """
    label = str(bar.get("bar_label") or "")
    spacing = bar.get("spacing_mm")

    # No bar label at all → invalid
    if not label:
        return False, InvalidReason.EMPTY

    # Matches longitudinal bar pattern "2Y16", "2Y20"
    if _LONGITUDINAL_RE.fullmatch(label.replace(" ", "")):
        return False, InvalidReason.LONGITUDINAL

    # Missing '@' symbol
    if "@" not in label:
        return False, InvalidReason.NO_AT_SIGN

    # spacing_mm should have been populated for valid stirrups
    if spacing is None:
        return False, InvalidReason.NO_SPACING

    return True, None


def is_invalid_label(label: str) -> bool:
    label_clean = (label or "").strip().replace(" ", "")
    if _LONGITUDINAL_RE.fullmatch(label_clean):
        return True
    if "@" not in label_clean:
        return True
    return False
