"""
Phase V.A.1 — End-to-End Validation
validation_models.py — Core dataclasses for validation results.
MODEL_VERSION: 6.5.3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

MODEL_VERSION = "6.5.3"


@dataclass
class StageResult:
    """Result of running one pipeline stage."""
    stage_name: str
    script_path: str
    success: bool
    exit_code: int
    elapsed_seconds: float
    stdout_lines: int
    stderr: str
    error_message: str = ""
    output_files: List[str] = field(default_factory=list)


@dataclass
class WorkbookValidation:
    """Result of validating the generated Excel workbook."""
    workbook_path: str
    exists: bool
    readable: bool
    corrupted: bool
    size_bytes: int
    sheet_names: List[str]
    total_sheets: int
    total_rows: int
    total_columns: int
    has_data: bool
    validation_passed: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class WorksheetValidation:
    """Per-worksheet validation result."""
    sheet_name: str
    exists: bool
    row_count: int
    col_count: int
    has_headers: bool
    header_row: List[Any]
    has_data_rows: bool
    first_data_row: Optional[List[Any]]
    validation_passed: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class CellComparison:
    """Individual cell comparison result."""
    row: int
    col: int
    generated_value: Any
    reference_value: Any
    match: bool
    diff_pct: Optional[float] = None


@dataclass
class WorksheetComparison:
    """Comparison of one worksheet between generated and reference."""
    sheet_name: str
    gen_rows: int
    ref_rows: int
    gen_cols: int
    ref_cols: int
    row_count_match: bool
    col_count_match: bool
    header_match: bool
    data_rows_compared: int
    matching_cells: int
    mismatching_cells: int
    match_rate_pct: float
    key_differences: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkbookComparison:
    """Full workbook comparison: generated vs reference."""
    generated_path: str
    reference_path: str
    generated_sheets: List[str]
    reference_sheets: List[str]
    sheet_count_match: bool
    sheet_names_match: bool
    common_sheets: List[str]
    missing_in_generated: List[str]
    extra_in_generated: List[str]
    worksheet_comparisons: List[WorksheetComparison]
    overall_match_rate_pct: float
    totals_match: bool
    steel_weight_comparison: Dict[str, Any] = field(default_factory=dict)
    quantity_comparison: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationSummary:
    """Top-level summary of the V.A.1 validation run."""
    model_version: str
    benchmark_id: str
    drawing_name: str
    timestamp: str

    # Pipeline execution
    stages_executed: int
    stages_passed: int
    stages_failed: int
    total_pipeline_seconds: float

    # Workbook
    workbook_generated: bool
    workbook_valid: bool
    workbook_path: str

    # Worksheets
    expected_worksheets: int
    validated_worksheets: int
    worksheet_pass_rate_pct: float

    # Comparison
    comparison_completed: bool
    overall_match_rate_pct: float
    totals_match: bool

    # Rules
    rule_results: Dict[str, bool]
    validation_passed: bool

    # Engineering differences
    engineering_differences: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    ready_for_benchmark_set_2: bool = False
