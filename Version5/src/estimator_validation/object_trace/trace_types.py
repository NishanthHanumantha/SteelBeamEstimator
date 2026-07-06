"""Engineering object trace types — Phase QA.2."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional

from src.estimator_validation.audit_types import (
    ESTIMATOR_DIR_REL,
    FLOAT_TOLERANCE,
    GENERATED_WORKBOOK_REL,
    OUTPUT_DIR_REL,
    resolve_estimator_workbook,
)

PHASE = "Phase QA.2"
TRACE_VERSION = "1.0.0"
ENGINEERING_TRACE_NAMESPACE = "ENGINEERING_TRACE"
ENGINEERING_TRACE_REGISTRY = "ENGINEERING_TRACE_REGISTRY"

OBJECT_TRACE_OUTPUT_REL = OUTPUT_DIR_REL / "object_trace"

CONFIDENCE_EXACT = 100
CONFIDENCE_NO_FAB_MARK = 95
CONFIDENCE_NO_SHAPE = 90
CONFIDENCE_ROLE_DIAMETER = 80
CONFIDENCE_UNMATCHED = 0

MIN_MATCH_CONFIDENCE = CONFIDENCE_ROLE_DIAMETER
UNKNOWN_THRESHOLD_PCT = 5.0

TRACE_LAYERS: tuple[str, ...] = (
    "drawing",
    "identity",
    "bar_group",
    "bbs",
    "steel_weight",
    "beam_summary",
    "quantity",
    "material",
    "beam_schedule",
    "engineering_report",
    "excel",
)


class TraceRootCause(str, Enum):
    DRAWING_PARSER = "Drawing Parser"
    GEOMETRY = "Geometry"
    IDENTITY = "Identity"
    BAR_GROUP = "BarGroup"
    BBS = "BBS"
    STEEL_WEIGHT = "SteelWeight"
    BEAM_SUMMARY = "BeamSummary"
    QUANTITY = "Quantity"
    MATERIAL = "Material"
    BEAM_SCHEDULE = "BeamSchedule"
    ENGINEERING_REPORT = "EngineeringReport"
    EXCEL_EXPORT = "Excel Export"
    GROUND_TRUTH_DIFFERENCE = "Ground Truth Difference"
    UNKNOWN = "Unknown"


LAYER_TO_ROOT_CAUSE: Dict[str, TraceRootCause] = {
    "drawing": TraceRootCause.DRAWING_PARSER,
    "identity": TraceRootCause.IDENTITY,
    "bar_group": TraceRootCause.BAR_GROUP,
    "bbs": TraceRootCause.BBS,
    "steel_weight": TraceRootCause.STEEL_WEIGHT,
    "beam_summary": TraceRootCause.BEAM_SUMMARY,
    "quantity": TraceRootCause.QUANTITY,
    "material": TraceRootCause.MATERIAL,
    "beam_schedule": TraceRootCause.BEAM_SCHEDULE,
    "engineering_report": TraceRootCause.ENGINEERING_REPORT,
    "excel": TraceRootCause.EXCEL_EXPORT,
}

VALID_ROOT_CAUSES: FrozenSet[str] = frozenset(item.value for item in TraceRootCause)


@dataclass(frozen=True)
class EngineeringIdentity:
    beam_mark: str
    role: str
    diameter_mm: Optional[float] = None
    fabrication_mark: Optional[str] = None
    shape_code: Optional[str] = None
    description: Optional[str] = None
    steel_grade: Optional[str] = None
    bar_count: Optional[float] = None
    development_length_m: Optional[float] = None

    def identity_key(self) -> str:
        parts = [
            self.beam_mark,
            self.role,
            f"{self.diameter_mm:.3f}" if self.diameter_mm is not None else "",
            (self.fabrication_mark or "").strip().upper(),
            (self.shape_code or "").strip().upper(),
            (self.description or "").strip().lower(),
        ]
        return "|".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "beam_mark": self.beam_mark,
            "role": self.role,
            "diameter_mm": self.diameter_mm,
            "fabrication_mark": self.fabrication_mark,
            "shape_code": self.shape_code,
            "description": self.description,
            "steel_grade": self.steel_grade,
            "bar_count": self.bar_count,
            "development_length_m": self.development_length_m,
            "identity_key": self.identity_key(),
        }


@dataclass
class LayerMatch:
    layer: str
    status: str  # PASS | FAIL | UNMATCHED
    confidence: int = 0
    matched_id: Optional[str] = None
    matched_record: Optional[dict[str, Any]] = None


@dataclass
class ObjectTrace:
    estimator_row_index: int
    identity: EngineeringIdentity
    layer_matches: Dict[str, LayerMatch] = field(default_factory=dict)
    first_missing_layer: Optional[str] = None
    root_cause: str = TraceRootCause.UNKNOWN.value
    trace_status: str = "FAIL"
    confidence: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimator_row_index": self.estimator_row_index,
            "identity": self.identity.to_dict(),
            "layer_matches": {
                key: {
                    "layer": value.layer,
                    "status": value.status,
                    "confidence": value.confidence,
                    "matched_id": value.matched_id,
                }
                for key, value in self.layer_matches.items()
            },
            "first_missing_layer": self.first_missing_layer,
            "root_cause": self.root_cause,
            "trace_status": self.trace_status,
            "confidence": self.confidence,
        }


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_i = root / Path("data/output/phase_i")
    return {
        "generated_workbook": root / GENERATED_WORKBOOK_REL,
        "estimator_workbook": resolve_estimator_workbook(root),
        "output_dir": root / OBJECT_TRACE_OUTPUT_REL,
        "qa1_output_dir": root / OUTPUT_DIR_REL,
        "phase_i_root": phase_i,
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "bar_identity": phase_i / "i_8_bar_identity/bar_identity_results.json",
        "bar_group": phase_i / "i_9_bar_group/bar_group_results.json",
        "bbs": phase_i / "i_10_bbs/bbs_results.json",
        "steel_weight": phase_i / "i_11_steel_weight/steel_weight_results.json",
        "beam_summary": phase_i / "i_12_beam_summary/beam_summary_results.json",
        "quantity": phase_i / "i_13_quantity/quantity_results.json",
        "material": phase_i / "i_14_material_quantification/material_results.json",
        "beam_schedule": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
        "engineering_report": phase_i / "i_16_engineering_report/engineering_reports.json",
        "calculation_context": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "framing": root / Path("data/output/phase_a/framing_beams.json"),
        "geometry_model": root / Path("data/output/phase_f/beam_geometry_model.json"),
    }
