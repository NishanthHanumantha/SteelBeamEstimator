"""
role_normalizer.py — Normalize role from R.2.1B semantic object to R.2.1C role.
MODEL_VERSION: 7.12.0

Role is preserved from R.2.1B — it is based on observable annotation evidence:
  - S.F.R. text → SIDE_FACE
  - @spacing     → STIRRUP
  - Large dia + high qty → MAIN_BAR
  - Small dia / lesser qty → EXTRA_BAR / SPACER_BAR

Role is NOT inferred from intent. It remains the closest engineering classification
we can assert from the annotation alone, without geometry.
"""
from __future__ import annotations

from typing import Any, Dict

from .fact_models import (
    ROLE_MAIN_BAR,
    ROLE_EXTRA_BAR,
    ROLE_STIRRUP,
    ROLE_SPACER_BAR,
    ROLE_SIDE_FACE,
    ROLE_UNKNOWN,
)

# Map R.2.1B engineering_role → R.2.1C role
_ESO_ROLE_MAP: Dict[str, str] = {
    "MAIN_BAR":              ROLE_MAIN_BAR,
    "EXTRA_BAR":             ROLE_EXTRA_BAR,
    "STIRRUP":               ROLE_STIRRUP,
    "SPACER_BAR":            ROLE_SPACER_BAR,
    "SIDE_FACE":             ROLE_SIDE_FACE,
    "SIDE_FACE_REINFORCEMENT": ROLE_SIDE_FACE,
    "UNKNOWN":               ROLE_UNKNOWN,
    # Legacy R.1 role names (may appear in original_r1_role)
    "TOP_MAIN":              ROLE_MAIN_BAR,
    "BOTTOM_MAIN":           ROLE_MAIN_BAR,
    "TOP_EXTRA":             ROLE_EXTRA_BAR,
    "BOTTOM_EXTRA":          ROLE_EXTRA_BAR,
    "LAP":                   ROLE_UNKNOWN,
    "DEVELOPMENT":           ROLE_UNKNOWN,
    "BENT_UP":               ROLE_MAIN_BAR,
    "ANCHORAGE":             ROLE_UNKNOWN,
}


class RoleNormalizer:
    """
    Normalize the engineering role from a R.2.1B semantic object.

    Returns (role: str, notes: list[str]).
    """

    def normalize(self, eso: Dict[str, Any]) -> tuple:
        notes = []
        eso_role = eso.get("engineering_role", "UNKNOWN") or "UNKNOWN"
        role = _ESO_ROLE_MAP.get(eso_role, ROLE_UNKNOWN)
        notes.append(f"Role normalized from ESO.engineering_role={eso_role!r} -> {role}")
        return role, notes
