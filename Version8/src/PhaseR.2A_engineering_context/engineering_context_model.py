"""
Immutable Engineering Context model.

After construction the context is frozen; no consumer may mutate it.
All access is via accessor methods on EngineeringContextLoader.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DevelopmentLengthEntry:
    """Ld in mm for a single (steel_grade, diameter_mm, concrete_grade) triplet."""
    steel_grade: str        # e.g. "Fe415"
    diameter_mm: int        # e.g. 12
    concrete_grade: str     # e.g. "M25"
    length_mm: int          # e.g. 485
    source: str = "GN_DXF_TABLE_1"


@dataclass(frozen=True)
class CoverRule:
    """Clear cover specification for a structural element."""
    element_type: str       # e.g. "BEAM IN SUPERSTRUCTURE"
    cover_mm: int           # e.g. 30
    concrete_grade: str     # e.g. "M30"
    steel_grade: str        # e.g. "Fe550"
    source: str = "GN_DXF_TABLE_2"
    note: str = ""


@dataclass(frozen=True)
class HookBendRule:
    """Standard hook / bend specification."""
    rule_type: str          # "STANDARD_90_BEND" | "STANDARD_135_BEND" | "HOOK"
    angle_deg: int          # 90 | 135
    multiplier_xd: int      # length = N * diameter
    source: str = "GN_DXF"
    note: str = ""


@dataclass(frozen=True)
class LapRule:
    """Lap splice specification."""
    rule_type: str          # "MINIMUM_LAP" | "TABLE_REF"
    value_mm: Optional[int] = None     # e.g. 300
    table_ref: str = ""                # e.g. "TABLE-1"
    source: str = "GN_DXF"
    note: str = ""


@dataclass(frozen=True)
class SpacerRule:
    """Spacer bar / cover block specification."""
    description: str
    source: str = "GN_DXF"
    note: str = ""


@dataclass(frozen=True)
class CodeReference:
    """Indian Standard code reference found in GN DXF."""
    code: str               # e.g. "IS 456:2000"
    clause: str = ""
    context: str = ""
    source: str = "GN_DXF"


# ---------------------------------------------------------------------------
# Master immutable EngineeringContext
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EngineeringContext:
    """
    Immutable container for all engineering parameters extracted from the
    General Notes DXF.  Created once per project; never mutated.

    Access via EngineeringContextLoader methods which implement fallbacks.
    """
    # Provenance
    gn_dxf_path: str
    project_id: str
    parsed_at: str              # ISO timestamp

    # Steel grades present in the GN DXF
    steel_grades: tuple         # e.g. ("Fe415", "Fe500", "Fe550")
    primary_steel_grade: str    # dominant grade, e.g. "Fe550"

    # Concrete grades (set-level — full table per element is in cover_rules)
    concrete_grades: tuple      # e.g. ("M30",)

    # Development length lookup (TABLE 1)
    # dict key: (steel_grade, diameter_mm, concrete_grade) -> length_mm
    development_length_table: dict  # frozen via __post_init__ trick

    # Cover rules per element (TABLE 2)
    cover_rules: tuple          # tuple of CoverRule

    # Hook and bend rules
    hook_rules: tuple           # tuple of HookBendRule

    # Lap rules
    lap_rules: tuple            # tuple of LapRule

    # Spacer rules
    spacer_rules: tuple         # tuple of SpacerRule

    # IS code references
    code_references: tuple      # tuple of CodeReference

    # Parsing metadata
    warnings: tuple             # tuple of str — non-fatal parse warnings
    parse_confidence: float     # 0.0–1.0

    # Backward-compat fallbacks (filled when GN parsing succeeds)
    fallback_dev_length_factor: int     # e.g. 40 (for single-value consumers)
    fallback_cover_mm: int              # e.g. 30 (beam cover from TABLE 2)
    fallback_steel_grade: str           # e.g. "Fe550"
    fallback_concrete_grade: str        # e.g. "M30"

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict."""
        return {
            "gn_dxf_path": self.gn_dxf_path,
            "project_id": self.project_id,
            "parsed_at": self.parsed_at,
            "steel_grades": list(self.steel_grades),
            "primary_steel_grade": self.primary_steel_grade,
            "concrete_grades": list(self.concrete_grades),
            "development_length_table": {
                f"{k[0]}_dia{k[1]}__{k[2]}": v
                for k, v in self.development_length_table.items()
            },
            "cover_rules": [
                {
                    "element": r.element_type,
                    "cover_mm": r.cover_mm,
                    "concrete_grade": r.concrete_grade,
                    "steel_grade": r.steel_grade,
                    "source": r.source,
                    "note": r.note,
                }
                for r in self.cover_rules
            ],
            "hook_rules": [
                {
                    "rule_type": r.rule_type,
                    "angle_deg": r.angle_deg,
                    "multiplier_xd": r.multiplier_xd,
                    "source": r.source,
                    "note": r.note,
                }
                for r in self.hook_rules
            ],
            "lap_rules": [
                {
                    "rule_type": r.rule_type,
                    "value_mm": r.value_mm,
                    "table_ref": r.table_ref,
                    "source": r.source,
                    "note": r.note,
                }
                for r in self.lap_rules
            ],
            "spacer_rules": [
                {"description": r.description, "source": r.source}
                for r in self.spacer_rules
            ],
            "code_references": [
                {"code": r.code, "clause": r.clause, "context": r.context}
                for r in self.code_references
            ],
            "warnings": list(self.warnings),
            "parse_confidence": self.parse_confidence,
            "fallback_dev_length_factor": self.fallback_dev_length_factor,
            "fallback_cover_mm": self.fallback_cover_mm,
            "fallback_steel_grade": self.fallback_steel_grade,
            "fallback_concrete_grade": self.fallback_concrete_grade,
        }
