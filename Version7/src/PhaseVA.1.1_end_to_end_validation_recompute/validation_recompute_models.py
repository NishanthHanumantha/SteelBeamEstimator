"""
Phase V.A.1.1 — validation_recompute_models.py
Dataclasses for all artefacts produced during the recompute phase.
MODEL_VERSION: 6.6.3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Pipeline ──────────────────────────────────────────────────────────────────

@dataclass
class StageRecomputeResult:
    stage_name: str
    script_path: str
    success: bool
    exit_code: int
    elapsed_seconds: float
    stdout_lines: int
    stderr: str = ""
    error_message: str = ""
    output_files: List[str] = field(default_factory=list)


@dataclass
class PipelineRecomputeResult:
    stages: List[StageRecomputeResult] = field(default_factory=list)
    total_elapsed_seconds: float = 0.0
    stages_executed: int = 0
    stages_passed: int = 0
    stages_failed: int = 0
    success_rate_pct: float = 0.0
    pipeline_passed: bool = False


# ── Workbook Validation ───────────────────────────────────────────────────────

@dataclass
class WorksheetRecomputeValidation:
    sheet_name: str
    row_count: int
    col_count: int
    has_headers: bool
    has_data_rows: bool
    has_totals_row: bool
    has_steel_summary: bool
    validation_passed: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class WorkbookRecomputeValidation:
    workbook_path: str
    exists: bool
    readable: bool
    corrupted: bool
    size_bytes: int
    size_kb: float
    sheet_names: List[str]
    total_sheets: int
    total_rows: int
    total_columns: int
    has_data: bool
    validation_passed: bool
    worksheet_validations: List[WorksheetRecomputeValidation] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


# ── Workbook Comparison ───────────────────────────────────────────────────────

@dataclass
class WorksheetDiffResult:
    sheet_name: str
    generated_rows: int
    reference_rows: int
    generated_cols: int
    reference_cols: int
    row_count_match: bool
    col_count_match: bool
    header_match: bool
    data_rows_compared: int
    matching_cells: int
    mismatching_cells: int
    match_rate_pct: float
    key_mismatches: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkbookDiffResult:
    generated_path: str
    reference_path: str
    generated_sheets: List[str]
    reference_sheets: List[str]
    sheet_count_match: bool
    sheet_names_match: bool
    common_sheets: List[str]
    missing_in_generated: List[str]
    extra_in_generated: List[str]
    overall_match_rate_pct: float
    worksheet_diffs: List[WorksheetDiffResult] = field(default_factory=list)
    comparison_completed: bool = False


# ── Engineering Accuracy ──────────────────────────────────────────────────────

@dataclass
class EngineeringAccuracyKPIs:
    total_beams: int
    beams_with_top_bars: int
    beams_with_bottom_bars: int
    beams_with_extra_bars: int
    beams_with_stirrups: int
    beams_with_development_bars: int
    beams_with_lap_bars: int
    beams_with_spacer_bars: int
    total_engineering_rows: int
    total_bbs_rows: int
    total_steel_kg: float
    diameter_totals_kg: Dict[str, float]
    project_total_kg: float
    workbook_match_pct: float
    stirrup_coverage_beams: int
    bbs_completeness_pct: float


# ── Difference Analysis (previous vs current) ─────────────────────────────────

@dataclass
class MetricDiff:
    metric_name: str
    previous_value: Any
    current_value: Any
    change: Any
    direction: str          # "improved" | "regression" | "unchanged" | "new"
    is_major: bool = False


@dataclass
class ValidationDifferenceReport:
    previous_model_version: str
    current_model_version: str
    improved_metrics: List[MetricDiff] = field(default_factory=list)
    unchanged_metrics: List[MetricDiff] = field(default_factory=list)
    regression_metrics: List[MetricDiff] = field(default_factory=list)
    new_metrics: List[MetricDiff] = field(default_factory=list)
    major_improvements: List[str] = field(default_factory=list)


# ── Validation Statistics ─────────────────────────────────────────────────────

@dataclass
class RecomputeStatistics:
    execution_time_sec: float
    pipeline_success: bool
    workbook_success: bool
    worksheet_success: bool
    engineering_row_count: int
    total_steel_kg: float
    bbs_row_count: int
    workbook_match_pct: float
    stages_passed: int
    stages_total: int
    stirrup_beams: int
    diameter_totals_kg: Dict[str, float] = field(default_factory=dict)


# ── Full Recompute Result ─────────────────────────────────────────────────────

@dataclass
class FullRecomputeResult:
    model_version: str
    benchmark_id: str
    timestamp: str
    drawing_name: str
    pipeline: Optional[PipelineRecomputeResult] = None
    workbook_validation: Optional[WorkbookRecomputeValidation] = None
    workbook_diff: Optional[WorkbookDiffResult] = None
    engineering_accuracy: Optional[EngineeringAccuracyKPIs] = None
    difference_report: Optional[ValidationDifferenceReport] = None
    statistics: Optional[RecomputeStatistics] = None
    validation_errors: List[str] = field(default_factory=list)
    rules_passed: Dict[str, bool] = field(default_factory=dict)
    overall_passed: bool = False
    readiness_assessment: Optional[Dict[str, Any]] = None
    remaining_gaps: List[str] = field(default_factory=list)
