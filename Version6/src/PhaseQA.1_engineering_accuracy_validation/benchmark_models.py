"""
Phase QA.1 — Engineering Accuracy Benchmark & Validation Framework
benchmark_models.py  — Core dataclasses for benchmark results and KPI records.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

MODEL_VERSION = "6.5.1"

# ── Accuracy classification thresholds ─────────────────────────────────────
CLASSIFICATION_THRESHOLDS = {
    "EXCELLENT":  98.0,
    "VERY_GOOD":  95.0,
    "GOOD":       90.0,
    "FAIR":       80.0,
    # below 80 → POOR
}

# ── Default KPI weights (must sum to 100) ──────────────────────────────────
DEFAULT_WEIGHTS = {
    "beam_detection":        10.0,
    "beam_assignment":       15.0,
    "geometry":              10.0,
    "feature_extraction":    10.0,
    "top_bottom":            15.0,
    "diameter":               5.0,
    "quantity":               5.0,
    "pattern_recognition":   10.0,
    "bbs":                   10.0,
    "steel_weight":           5.0,
    "cut_length":             5.0,
}


# ── Individual KPI record ───────────────────────────────────────────────────
@dataclass
class KPIRecord:
    kpi_name: str
    expected: Optional[float]
    detected: Optional[float]
    correct: Optional[float]
    accuracy_pct: Optional[float]       # None if not evaluable
    mae: Optional[float] = None
    rmse: Optional[float] = None
    max_error: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    weight: float = 0.0
    status: str = "OK"                  # OK | NOT_AVAILABLE | PARTIAL
    notes: str = ""


# ── Per-beam accuracy record ────────────────────────────────────────────────
@dataclass
class BeamAccuracyRecord:
    beam_id: str
    expected: bool = True
    detected: bool = False
    match: bool = False
    is_false_positive: bool = False
    notes: str = ""


# ── Geometry error record ───────────────────────────────────────────────────
@dataclass
class GeometryErrorRecord:
    beam_id: str
    field: str                       # span_mm | depth_mm | width_mm
    expected_value: float
    predicted_value: float
    absolute_error_mm: float
    within_tolerance: bool
    tolerance_mm: float = 2.0


# ── Pattern comparison record ───────────────────────────────────────────────
@dataclass
class PatternComparisonRecord:
    beam_id: str
    pattern_type: str                # span_pattern | continuity | structural_behavior
    expected: str
    predicted: str
    match: bool


# ── BBS row comparison record ───────────────────────────────────────────────
@dataclass
class BBSRowRecord:
    bbs_id: str
    beam_id: str
    diameter_match: bool
    shape_match: bool
    quantity_match: bool
    cut_length_match: bool
    row_correct: bool
    notes: str = ""


# ── Error entry for error analysis ─────────────────────────────────────────
@dataclass
class ErrorEntry:
    error_type: str
    beam_id: str
    description: str
    severity: str         # HIGH | MEDIUM | LOW
    impact_score: float   # 0-10
    kpi_affected: str
    details: Dict[str, Any] = field(default_factory=dict)


# ── Main benchmark result dataclass ────────────────────────────────────────
@dataclass
class EngineeringBenchmarkResult:
    benchmark_id: str
    drawing_name: str
    model_version: str
    validation_timestamp: str

    # KPI scores (0-100 or None if not available)
    beam_detection_accuracy: Optional[float]
    beam_assignment_accuracy: Optional[float]
    geometry_accuracy: Optional[float]
    feature_accuracy: Optional[float]
    top_bottom_accuracy: Optional[float]
    diameter_accuracy: Optional[float]
    quantity_accuracy: Optional[float]
    pattern_accuracy: Optional[float]
    cut_length_accuracy: Optional[float]
    steel_weight_accuracy: Optional[float]
    bbs_accuracy: Optional[float]
    overall_engineering_accuracy: Optional[float]

    # Weighted score
    weighted_score: float
    classification: str              # EXCELLENT | VERY_GOOD | GOOD | FAIR | POOR

    # Pass / fail
    pass_fail: str                   # PASS | FAIL | PARTIAL

    # Detailed KPI records
    kpi_records: List[KPIRecord] = field(default_factory=list)

    # Beam-level details
    beam_accuracy_records: List[BeamAccuracyRecord] = field(default_factory=list)
    geometry_error_records: List[GeometryErrorRecord] = field(default_factory=list)
    pattern_comparison_records: List[PatternComparisonRecord] = field(default_factory=list)
    bbs_row_records: List[BBSRowRecord] = field(default_factory=list)

    # Error analysis
    error_summary: List[ErrorEntry] = field(default_factory=list)

    # Validation rules
    rule_results: Dict[str, bool] = field(default_factory=dict)
    validation_passed: bool = False

    # Confusion matrices (keyed by category)
    confusion_matrices: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    benchmark_file: str = ""
    notes: str = ""


def classify_score(score: float) -> str:
    """Return EXCELLENT / VERY_GOOD / GOOD / FAIR / POOR."""
    if score >= CLASSIFICATION_THRESHOLDS["EXCELLENT"]:
        return "EXCELLENT"
    if score >= CLASSIFICATION_THRESHOLDS["VERY_GOOD"]:
        return "VERY_GOOD"
    if score >= CLASSIFICATION_THRESHOLDS["GOOD"]:
        return "GOOD"
    if score >= CLASSIFICATION_THRESHOLDS["FAIR"]:
        return "FAIR"
    return "POOR"


def safe_pct(correct: float, total: float, default: Optional[float] = None) -> Optional[float]:
    """Return percentage or default when total is zero."""
    if total == 0:
        return default
    return round(correct / total * 100.0, 4)
