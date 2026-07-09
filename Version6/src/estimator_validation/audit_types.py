"""Estimator validation audit types — Phase QA.1."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import FrozenSet

PHASE = "Phase QA.1"
AUDIT_VERSION = "1.0.0"
FLOAT_TOLERANCE = 0.001

GENERATED_WORKBOOK_REL = Path("data/output/phase_i/i_17_excel_export/Beam_Reinforcement_Schedule.xlsx")
ESTIMATOR_DIR_REL = Path("data/Estimator_Validated_Output")
OUTPUT_DIR_REL = Path("data/output/estimator_validation")

ENGINEERING_FIELDS = (
    "clear_span_m",
    "width_m",
    "depth_m",
    "diameter_mm",
    "spacing_m",
    "bar_count",
    "development_length_m",
    "cut_length_m",
    "total_length_m",
    "steel_weight_kg",
)

SUMMARY_METADATA_LABELS = frozenset({
    "total bars",
    "total cut length (mm)",
    "total steel weight (kg)",
    "validation status",
    "generation timestamp",
    "model version",
})


class RootCause(str, Enum):
    EXCEL_MAPPING = "EXCEL_MAPPING"
    DISPLAY_ORDER = "DISPLAY_ORDER"
    ROW_INSERTION = "ROW_INSERTION"
    TEMPLATE_LAYOUT = "TEMPLATE_LAYOUT"
    ENGINEERING_REPORT = "ENGINEERING_REPORT"
    BEAM_SCHEDULE = "BEAM_SCHEDULE"
    MATERIAL = "MATERIAL"
    QUANTITY = "QUANTITY"
    STEEL_WEIGHT = "STEEL_WEIGHT"
    BBS = "BBS"
    ENGINEERING_CALCULATION = "ENGINEERING_CALCULATION"
    PARSER = "PARSER"
    DRAWING_DATA = "DRAWING_DATA"
    GROUND_TRUTH_DIFFERENCE = "GROUND_TRUTH_DIFFERENCE"
    UNKNOWN = "UNKNOWN"


VALID_ROOT_CAUSES: FrozenSet[str] = frozenset(item.value for item in RootCause)


class DiscrepancySeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


def resolve_estimator_workbook(project_root: Path) -> Path:
    directory = project_root / ESTIMATOR_DIR_REL
    matches = sorted(directory.glob("*.xlsx"))
    if not matches:
        raise FileNotFoundError(f"No estimator workbook found in {directory}")
    preferred = [item for item in matches if "EstimatorValidated" in item.name]
    return preferred[0] if preferred else matches[0]


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    return {
        "generated_workbook": root / GENERATED_WORKBOOK_REL,
        "estimator_workbook": resolve_estimator_workbook(root),
        "output_dir": root / OUTPUT_DIR_REL,
        "phase_i_root": root / Path("data/output/phase_i"),
    }
