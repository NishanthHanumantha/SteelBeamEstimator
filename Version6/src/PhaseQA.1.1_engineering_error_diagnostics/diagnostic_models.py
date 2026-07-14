"""
Phase QA.1.1 — Engineering Error Diagnostics & Root Cause Analysis Engine
diagnostic_models.py — Core dataclasses for diagnostics.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

MODEL_VERSION = "6.5.2"

# ── Pipeline stages ─────────────────────────────────────────────────────────
class PipelineStage:
    DRAWING_PARSER              = "DRAWING_PARSER"
    GEOMETRY_ENGINE             = "GEOMETRY_ENGINE"
    REINFORCEMENT_INTERPRETATION = "REINFORCEMENT_INTERPRETATION"
    GEOMETRY_RECOVERY           = "GEOMETRY_RECOVERY"
    FEATURE_EXTRACTION          = "FEATURE_EXTRACTION"
    PATTERN_RECOGNITION         = "PATTERN_RECOGNITION"
    BBS_GENERATION              = "BBS_GENERATION"
    STEEL_CALCULATION           = "STEEL_CALCULATION"
    UNKNOWN                     = "UNKNOWN"

    ORDER = [
        DRAWING_PARSER,
        GEOMETRY_ENGINE,
        REINFORCEMENT_INTERPRETATION,
        GEOMETRY_RECOVERY,
        FEATURE_EXTRACTION,
        PATTERN_RECOGNITION,
        BBS_GENERATION,
        STEEL_CALCULATION,
    ]

    @classmethod
    def index(cls, stage: str) -> int:
        try:
            return cls.ORDER.index(stage)
        except ValueError:
            return len(cls.ORDER)


# ── Root cause categories ────────────────────────────────────────────────────
class RootCause:
    DRAWING_ERROR       = "DRAWING_ERROR"
    PARSER_ERROR        = "PARSER_ERROR"
    GEOMETRY_ERROR      = "GEOMETRY_ERROR"
    ASSOCIATION_ERROR   = "ASSOCIATION_ERROR"
    FEATURE_ERROR       = "FEATURE_ERROR"
    PATTERN_ERROR       = "PATTERN_ERROR"
    BBS_ERROR           = "BBS_ERROR"
    CALCULATION_ERROR   = "CALCULATION_ERROR"
    REFERENCE_DATA_ERROR = "REFERENCE_DATA_ERROR"
    UNKNOWN             = "UNKNOWN"


# ── Impact levels ────────────────────────────────────────────────────────────
class ImpactLevel:
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"

    LEVEL_SCORE = {CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1}

    @classmethod
    def from_score(cls, score: float) -> str:
        if score >= 8.0:   return cls.CRITICAL
        if score >= 6.0:   return cls.HIGH
        if score >= 3.0:   return cls.MEDIUM
        return cls.LOW


# ── Engineering diagnostic per error ─────────────────────────────────────────
@dataclass
class EngineeringDiagnostic:
    diagnostic_id: str
    drawing_name: str
    beam_id: str
    bar_id: str                         # empty string if beam-level

    error_type: str
    expected_value: Optional[str]
    predicted_value: Optional[str]
    difference: Optional[str]

    pipeline_stage: str                 # PipelineStage constant
    root_cause: str                     # RootCause constant
    severity: str                       # LOW / MEDIUM / HIGH / CRITICAL
    impact_score: float                 # 0–10
    impact_level: str                   # ImpactLevel constant
    confidence: float                   # 0–1

    downstream_modules: List[str] = field(default_factory=list)
    recommended_fix: str = ""
    priority_score: float = 0.0
    priority_rank: int = 0

    engineering_notes: List[str] = field(default_factory=list)
    traceability: Dict[str, Any] = field(default_factory=dict)


# ── Priority fix entry ───────────────────────────────────────────────────────
@dataclass
class PriorityFix:
    rank: int
    fix_title: str
    error_type: str
    root_cause: str
    pipeline_stage: str
    frequency: int
    severity: str
    priority_score: float
    expected_improvement_pct: float
    kpi_affected: str
    recommendation: str
    affected_beams: List[str] = field(default_factory=list)


# ── Diagnostics summary ──────────────────────────────────────────────────────
@dataclass
class DiagnosticsSummary:
    benchmark_id: str
    drawing_name: str
    model_version: str
    timestamp: str

    total_diagnostics: int
    total_qa1_errors_diagnosed: int
    total_kpi_gap_diagnostics: int

    root_cause_distribution: Dict[str, int]
    pipeline_stage_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
    impact_distribution: Dict[str, int]

    priority_fixes: List[PriorityFix]
    validation_passed: bool
    rule_results: Dict[str, bool]

    overall_diagnostic_confidence: float
    recommendations_count: int
    notes: str = ""
