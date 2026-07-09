"""Engineering accuracy dashboard types — Phase QA.ACCURACY.1."""

from __future__ import annotations

from pathlib import Path
from typing import FrozenSet, Tuple

PHASE = "Phase QA.ACCURACY.1"
COVERAGE_EXTENSION = "Phase QA.COVERAGE.2"
OFFICIAL_SUMMARY_EXTENSION = "Phase QA.COVERAGE.3"
TERMINOLOGY_REFINEMENT = "Phase QA.ACCURACY.1.1"
MODEL_VERSION = "5.21.4"
DASHBOARD_VERSION = "1.3.0"
DASHBOARD_TITLE = "Engineering Coverage Dashboard"
DIAMETER_SUMMARY_SOURCE = "OFFICIAL_WORKBOOK_SUMMARY"
SUMMARY_PARSE_WARNING = "SUMMARY_PARSE_WARNING"
SUMMARY_TOTAL_TOLERANCE_KG = 0.05

STANDARD_DIAMETERS_MM: Tuple[int, ...] = (8, 10, 12, 16, 20, 25, 32)

COVERAGE_DISTRIBUTION_BANDS = (
    ("high_coverage", "High Coverage", 90.0, None),
    ("moderate_coverage", "Moderate Coverage", 70.0, 90.0),
    ("low_coverage", "Low Coverage", 30.0, 70.0),
    ("very_low_coverage", "Very Low Coverage", None, 30.0),
)

MANAGEMENT_NOTE = (
    "This dashboard measures engineering coverage of the current prototype. "
    "Coverage indicates how much of the estimator's engineering schedule has been successfully generated. "
    "It does not evaluate the correctness of engineering calculations already produced. "
    "Engineering calculation modules remain deterministic and validated."
)
FLOAT_TOLERANCE = 0.001

GENERATED_WORKBOOK_REL = Path("data/output/phase_i/i_17_excel_export/Beam_Reinforcement_Schedule.xlsx")
ESTIMATOR_DIR_REL = Path("data/Estimator_Validated_Output")
OUTPUT_DIR_REL = Path("data/output/accuracy_dashboard")
PHASE_I_ROOT_REL = Path("data/output/phase_i")

ENGINEERING_REPORT_REL = PHASE_I_ROOT_REL / "i_16_engineering_report" / "engineering_reports.json"
BEAM_SCHEDULE_REL = PHASE_I_ROOT_REL / "i_15_beam_schedule" / "beam_schedule_results.json"

ENGINEERING_VALUE_FIELDS: Tuple[str, ...] = (
    "role_hint",
    "diameter_mm",
    "spacing_m",
    "bar_count",
    "cut_length_m",
    "total_length_m",
    "steel_weight_kg",
    "fabrication_mark",
    "shape_code",
)

ENGINEERING_FIELD_LABELS = {
    "role_hint": "Role",
    "diameter_mm": "Diameter",
    "spacing_m": "Spacing",
    "bar_count": "Bar Count",
    "cut_length_m": "Length",
    "total_length_m": "Length",
    "steel_weight_kg": "Weight",
    "fabrication_mark": "Fabrication Mark",
    "shape_code": "Shape Code",
}

FROZEN_PIPELINE_STAGES: FrozenSet[str] = frozenset(
    f"I.{stage}" for stage in range(10, 18)
)


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
        "engineering_report_json": root / ENGINEERING_REPORT_REL,
        "beam_schedule_json": root / BEAM_SCHEDULE_REL,
        "output_dir": root / OUTPUT_DIR_REL,
        "phase_i_root": root / PHASE_I_ROOT_REL,
    }
