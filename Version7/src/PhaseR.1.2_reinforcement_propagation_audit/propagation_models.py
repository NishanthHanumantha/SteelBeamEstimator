"""Propagation audit data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


ROOT_CAUSE_CATEGORIES = [
    "NO_REINFORCEMENT",
    "EMPTY_GROUP",
    "ROLE_NOT_SUPPORTED",
    "SPAN_NOT_AVAILABLE",
    "GEOMETRY_NOT_AVAILABLE",
    "CUT_LENGTH_FAILED",
    "BAR_CREATION_FAILED",
    "ADAPTER_FILTERED",
    "L2_FILTERED",
    "STEEL_SKIPPED",
    "BBS_SKIPPED",
    "EXCEL_SKIPPED",
    "FULLY_PROPAGATED",
    "UNKNOWN",
]

STAGE_ORDER = [
    "VROOT",
    "R1",
    "ADAPTER",
    "L2",
    "SI0",
    "SI1",
    "STEEL",
    "BBS",
    "EXCEL",
]

L2_BAR_KEYS = [
    "top_main_bars", "bottom_main_bars", "top_extra_bars", "bottom_extra_bars",
    "side_face_reinforcement", "stirrups", "spacer_bars", "chair_bars",
    "supplementary_bars", "development_length_regions", "continuity_regions",
]

R1_ROLE_KEYS = [
    "TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA",
    "STIRRUP", "SPACER_BAR", "SIDE_FACE_REINFORCEMENT",
    "DEVELOPMENT", "LAP", "UNKNOWN",
]

BENCHMARK_BEAMS = {"B1", "B2", "B8", "B9", "B10"}


@dataclass
class BeamPropagationRecord:
    beam_id: str
    in_registry: bool = False
    geometry: Dict[str, Any] = field(default_factory=dict)
    r1_group_count: int = 0
    r1_total_quantity: int = 0
    r1_roles: Dict[str, int] = field(default_factory=dict)
    adapter_bar_count: int = 0
    l2_bar_count: int = 0
    l2_roles: Dict[str, int] = field(default_factory=dict)
    steel_bar_count: int = 0
    steel_weight_kg: float = 0.0
    bbs_row_count: int = 0
    bbs_engineering_rows: int = 0
    excel_has_steel: bool = False
    first_failure_stage: str = ""
    root_cause: str = ""
    responsible_module: str = ""
    responsible_function: str = ""
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "in_registry": self.in_registry,
            "geometry": self.geometry,
            "r1": {
                "group_count": self.r1_group_count,
                "total_quantity": self.r1_total_quantity,
                "roles": self.r1_roles,
            },
            "adapter": {"bar_count": self.adapter_bar_count},
            "l2": {
                "bar_count": self.l2_bar_count,
                "roles": self.l2_roles,
            },
            "steel": {
                "bar_count": self.steel_bar_count,
                "weight_kg": round(self.steel_weight_kg, 3),
            },
            "bbs": {
                "row_count": self.bbs_row_count,
                "engineering_rows": self.bbs_engineering_rows,
            },
            "excel": {"has_steel": self.excel_has_steel},
            "first_failure_stage": self.first_failure_stage,
            "root_cause": self.root_cause,
            "responsible_module": self.responsible_module,
            "responsible_function": self.responsible_function,
            "evidence": self.evidence,
        }


@dataclass
class ValidationResult:
    rule_id: str
    description: str
    passed: bool
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "passed": self.passed,
            "status": "PASS" if self.passed else "FAIL",
            "evidence": self.evidence,
        }
