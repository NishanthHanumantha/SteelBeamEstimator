"""Drawing interpretation audit types — Phase QA.3."""

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

PHASE = "Phase QA.3"
INTERPRETATION_VERSION = "1.0.0"
DRAWING_INTERPRETATION_OUTPUT_REL = OUTPUT_DIR_REL / "drawing_interpretation"
UNKNOWN_THRESHOLD_PCT = 5.0

ENGINEERING_CONCEPT_TYPES = (
    "TOP_MAIN",
    "TOP_EXTRA",
    "BOTTOM_MAIN",
    "BOTTOM_EXTRA",
    "SIDE_BAR",
    "STIRRUP",
    "SPACER_BAR",
    "SFR",
    "CURTAILMENT",
    "SUPPORT_ZONE",
    "MIDDLE_ZONE",
    "END_ZONE",
    "LAP_ZONE",
    "DEVELOPMENT_LENGTH_NOTE",
    "HOOK_NOTE",
    "SHAPE_NOTE",
    "SPACING_ZONE",
    "MULTIPLE_STIRRUP_REGION",
    "ANNOTATION",
    "UNKNOWN",
)


class InterpretationClassification(str, Enum):
    DRAWING_AND_ESTIMATOR_AND_PIPELINE = "DRAWING_AND_ESTIMATOR_AND_PIPELINE"
    DRAWING_AND_ESTIMATOR_ONLY = "DRAWING_AND_ESTIMATOR_ONLY"
    DRAWING_AND_PIPELINE_ONLY = "DRAWING_AND_PIPELINE_ONLY"
    ESTIMATOR_ONLY = "ESTIMATOR_ONLY"
    PIPELINE_ONLY = "PIPELINE_ONLY"
    DRAWING_ONLY = "DRAWING_ONLY"
    UNKNOWN = "UNKNOWN"


class InterpretationRootCause(str, Enum):
    PARSER_INTERPRETATION = "Parser Interpretation"
    DRAWING_AMBIGUITY = "Drawing Ambiguity"
    ENGINEERING_INTERPRETATION = "Engineering Interpretation"
    ESTIMATOR_ENGINEERING_DECISION = "Estimator Engineering Decision"
    IDENTITY = "Identity"
    BAR_GROUP = "Bar Group"
    BEAM_SCHEDULE = "Beam Schedule"
    ENGINEERING_REPORT = "Engineering Report"
    EXCEL_EXPORT = "Excel Export"
    GROUND_TRUTH_DIFFERENCE = "Ground Truth Difference"
    UNKNOWN = "Unknown"


class LengthInterpretation(str, Enum):
    CLEAR_SPAN = "Clear Span"
    EFFECTIVE_SPAN = "Effective Span"
    OVERALL_BEAM = "Overall Beam"
    SUPPORT_CENTRE_DISTANCE = "Support Centre Distance"
    DIMENSION_CHAIN = "Dimension Chain"
    MANUAL_ESTIMATOR_LENGTH = "Manual Estimator Length"
    UNKNOWN = "Unknown"


VALID_CLASSIFICATIONS: FrozenSet[str] = frozenset(item.value for item in InterpretationClassification)
VALID_ROOT_CAUSES: FrozenSet[str] = frozenset(item.value for item in InterpretationRootCause)


@dataclass
class EngineeringConcept:
    beam_mark: str
    concept_type: str
    role: str
    diameter_mm: Optional[float] = None
    quantity: Optional[float] = None
    spacing_mm: Optional[float] = None
    zone: Optional[str] = None
    raw_callouts: List[str] = field(default_factory=list)
    description: Optional[str] = None
    source_layer: str = "unknown"

    def concept_key(self) -> str:
        diameter = f"{self.diameter_mm:.0f}" if self.diameter_mm is not None else ""
        spacing = f"@{self.spacing_mm:.0f}" if self.spacing_mm is not None else ""
        zone = self.zone or ""
        return f"{self.beam_mark}|{self.role}|{diameter}|{spacing}|{zone}|{self.description or ''}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "beam_mark": self.beam_mark,
            "concept_type": self.concept_type,
            "role": self.role,
            "diameter_mm": self.diameter_mm,
            "quantity": self.quantity,
            "spacing_mm": self.spacing_mm,
            "zone": self.zone,
            "raw_callouts": self.raw_callouts,
            "description": self.description,
            "source_layer": self.source_layer,
            "concept_key": self.concept_key(),
        }


@dataclass
class BeamInterpretation:
    beam_mark: str
    raw_annotations: List[str] = field(default_factory=list)
    support_notes: List[str] = field(default_factory=list)
    development_notes: List[str] = field(default_factory=list)
    hook_notes: List[str] = field(default_factory=list)
    shape_notes: List[str] = field(default_factory=list)
    zone_notes: List[str] = field(default_factory=list)
    concepts: List[EngineeringConcept] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "beam_mark": self.beam_mark,
            "raw_annotations": self.raw_annotations,
            "support_notes": self.support_notes,
            "development_notes": self.development_notes,
            "hook_notes": self.hook_notes,
            "shape_notes": self.shape_notes,
            "zone_notes": self.zone_notes,
            "concepts": [item.to_dict() for item in self.concepts],
            "concept_count": len(self.concepts),
        }


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_i = root / Path("data/output/phase_i")
    phase_g = root / Path("data/output/phase_g")
    phase_f = root / Path("data/output/phase_f")
    return {
        "estimator_workbook": resolve_estimator_workbook(root),
        "generated_workbook": root / GENERATED_WORKBOOK_REL,
        "output_dir": root / DRAWING_INTERPRETATION_OUTPUT_REL,
        "reinforcement_text": phase_g / "g_2_reinforcement_drawing/reinforcement_text.json",
        "engineering_properties": phase_g / "g_5_3_1_property_parser/engineering_properties.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "bar_identity": phase_i / "i_8_bar_identity/bar_identity_results.json",
        "bar_group": phase_i / "i_9_bar_group/bar_group_results.json",
        "beam_schedule": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
        "engineering_report": phase_i / "i_16_engineering_report/engineering_reports.json",
        "beam_summary": phase_i / "i_12_beam_summary/beam_summary_results.json",
        "calculation_context": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "clear_spans": phase_f / "f_4_engineering_length/clear_spans.json",
        "beam_dimensions": phase_f / "f_1_framing_geometry/beam_dimensions.json",
        "framing_beams": root / Path("data/output/phase_a/framing_beams.json"),
    }
