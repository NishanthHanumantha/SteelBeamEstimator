"""
Production Output Models — Phase V.B.1
Data classes for steel weight, BBS rows, and production output.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class BarSteelWeight:
    bar_id: str
    beam_id: str
    role: str
    bar_label: str
    diameter_mm: float
    quantity: int
    steel_grade: str
    cut_length_mm: float
    cut_length_source: str
    area_mm2: float
    weight_per_bar_kg: float
    total_weight_kg: float
    formula_used: str


@dataclass
class BeamSteelWeight:
    beam_id: str
    beam_name: str
    span_mm: float
    depth_mm: Optional[float]
    width_mm: Optional[float]
    bar_weights: List[BarSteelWeight] = field(default_factory=list)
    total_weight_kg: float = 0.0
    weight_by_diameter: Dict[int, float] = field(default_factory=dict)


@dataclass
class DiameterSummary:
    diameter_mm: int
    total_bars: int
    total_length_mm: float
    total_weight_kg: float
    weight_fraction: float = 0.0


@dataclass
class ProjectSteelSummary:
    total_weight_kg: float
    beam_weights: List[BeamSteelWeight]
    diameter_summary: List[DiameterSummary]
    total_bars: int
    total_beams: int
    calculation_method: str = "IS_456_DETERMINISTIC"
    density_kg_m3: float = 7850.0


@dataclass
class BBSRow:
    """Single row in the Bar Bending Schedule."""
    si_no: Optional[int]
    frame_type: str
    description: str
    diameter_mm: Optional[float]
    spacing_m: Optional[float]
    quantity: Optional[int]
    dvlp_length_m: Optional[float]
    cut_length_m: Optional[float]
    total_length_m: Optional[float]
    weight_d8: Optional[float] = None
    weight_d10: Optional[float] = None
    weight_d12: Optional[float] = None
    weight_d16: Optional[float] = None
    weight_d20: Optional[float] = None
    weight_d25: Optional[float] = None
    weight_d32: Optional[float] = None
    total_weight_kg: Optional[float] = None
    is_beam_header: bool = False
    beam_id: str = ""


@dataclass
class WorkbookValidationResult:
    is_readable: bool
    is_complete: bool
    worksheet_count: int
    worksheet_names: List[str]
    expected_worksheets: List[str]
    missing_worksheets: List[str]
    row_counts: Dict[str, int]
    header_checks: Dict[str, bool]
    steel_total_check: bool
    steel_total_found: float
    no_corrupted_cells: bool
    validation_passed: bool
    validation_errors: List[str]


@dataclass
class ProductionStatistics:
    execution_time_sec: float
    total_beams: int
    total_bbs_rows: int
    total_engineering_rows: int
    total_rows_generated: int
    total_columns: int
    steel_total_kg: float
    workbook_files_generated: int
    worksheet_statistics: Dict[str, Dict[str, Any]]
    diameter_summary: Dict[int, float]


@dataclass
class ProductionOutputResult:
    phase_id: str = "VB.1"
    model_version: str = "6.6.0"
    pipeline_exit_code: int = 0
    steel_weight_kg: float = 0.0
    workbook_path: str = ""
    engineering_review_path: str = ""
    archive_path: str = ""
    workbook_validated: bool = False
    validation_result: Optional[WorkbookValidationResult] = None
    statistics: Optional[ProductionStatistics] = None
    beam_count: int = 0
    bbs_row_count: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
