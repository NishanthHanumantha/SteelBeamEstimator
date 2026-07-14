"""
Phase V.A.2 -- benchmark2_models.py
Dataclasses for all Benchmark Set 2 artefacts.
MODEL_VERSION: 7.0.0
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---- Input Manifest ---------------------------------------------------------

@dataclass
class BenchmarkFile:
    filename: str
    relative_path: str
    file_type: str          # FRAMING_DXF | REINFORCEMENT_DXF | GENERAL_NOTES_DXF | ESTIMATOR_EXCEL | OTHER
    size_bytes: int
    copied_to: str


@dataclass
class Benchmark2Manifest:
    benchmark_id: str
    timestamp: str
    source_folder: str
    destination_folder: str
    model_version: str
    files: List[BenchmarkFile] = field(default_factory=list)
    total_files: int = 0
    dxf_count: int = 0
    has_estimator_excel: bool = False
    drawing_name: str = ""
    validation_passed: bool = False
    issues: List[str] = field(default_factory=list)


# ---- Pipeline ---------------------------------------------------------------

@dataclass
class PipelineStageResult:
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
class PipelineRunResult:
    stages: List[PipelineStageResult] = field(default_factory=list)
    total_elapsed_seconds: float = 0.0
    stages_executed: int = 0
    stages_passed: int = 0
    stages_failed: int = 0
    success_rate_pct: float = 0.0
    pipeline_passed: bool = False


# ---- Workbook Validation ----------------------------------------------------

@dataclass
class WorksheetValidation:
    sheet_name: str
    row_count: int
    col_count: int
    has_headers: bool
    has_data_rows: bool
    validation_passed: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class WorkbookValidation:
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
    worksheet_validations: List[WorksheetValidation] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


# ---- Engineering KPIs -------------------------------------------------------

@dataclass
class EngineeringKPIs:
    total_beams: int
    total_engineering_rows: int
    total_bbs_rows: int
    total_steel_kg: float
    stirrup_coverage_beams: int
    bbs_completeness_pct: float
    diameter_totals_kg: Dict[str, float] = field(default_factory=dict)
    data_source: str = "Production_Output"


# ---- Workbook Comparison ----------------------------------------------------

@dataclass
class WorksheetComparison:
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


@dataclass
class WorkbookComparison:
    generated_path: str
    reference_path: str
    reference_exists: bool
    generated_sheets: List[str]
    reference_sheets: List[str]
    common_sheets: List[str]
    overall_match_rate_pct: float
    worksheet_comparisons: List[WorksheetComparison] = field(default_factory=list)
    comparison_completed: bool = False
    note: str = ""


# ---- Set 1 vs Set 2 Comparison ----------------------------------------------

@dataclass
class BenchmarkMetricComparison:
    metric_name: str
    set1_value: Any
    set2_value: Any
    delta: Any
    status: str          # SAME | BETTER | WORSE | N/A


@dataclass
class BenchmarkSetComparison:
    set1_id: str
    set2_id: str
    metric_comparisons: List[BenchmarkMetricComparison] = field(default_factory=list)
    stable_behaviours: List[str] = field(default_factory=list)
    new_failure_modes: List[str] = field(default_factory=list)
    drawing_specific_issues: List[str] = field(default_factory=list)
    common_issues: List[str] = field(default_factory=list)
    generalization_score: str = "POOR"


# ---- Full Result ------------------------------------------------------------

@dataclass
class FullBenchmark2Result:
    model_version: str
    benchmark_id: str
    timestamp: str
    manifest: Optional[Benchmark2Manifest] = None
    pipeline: Optional[PipelineRunResult] = None
    workbook_validation: Optional[WorkbookValidation] = None
    engineering_kpis: Optional[EngineeringKPIs] = None
    workbook_comparison: Optional[WorkbookComparison] = None
    set_comparison: Optional[BenchmarkSetComparison] = None
    validation_errors: List[str] = field(default_factory=list)
    rules_passed: Dict[str, bool] = field(default_factory=dict)
    overall_passed: bool = False
    generalization_assessment: Optional[Dict[str, Any]] = None
    recurring_issues: List[str] = field(default_factory=list)
    drawing_specific_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
