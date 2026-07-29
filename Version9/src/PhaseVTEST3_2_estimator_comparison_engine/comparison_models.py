"""
comparison_models.py — Data models for V.TEST.3.2 / V.TEST.3.2.1
MODEL_VERSION: 8.1.3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DIAMETER_MM = [8, 10, 12, 16, 20, 25, 32]

ROLE_PATTERNS = {
    "Top Bars":            [r"^top bars$", r"^top bar$"],
    "Top Bars Extra":      [r"top bars?\s*-?\s*extra"],
    "Bottom Bars":         [r"^bottom bars?\s*$"],
    "Bottom Bars Extra":   [r"bottom bars?\s*-?\s*extra"],
    "Stirrups":            [r"stirrup", r"stirupp"],
    "Hooks":               [r"hook", r"c\s*-\s*hook"],
    "Spacer Bars":         [r"spacer"],
    "Side Face Reinforcement": [r"\bsfr\b", r"side face"],
}

ROOT_CAUSE_CATEGORIES = [
    "CATEGORY A — Drawing interpretation",
    "CATEGORY B — Reinforcement discovery",
    "CATEGORY C — Engineering semantics",
    "CATEGORY D — Geometry",
    "CATEGORY E — Engineering intent",
    "CATEGORY F — Steel calculation",
    "CATEGORY G — Workbook generation",
    "CATEGORY H — Unknown",
]

@dataclass
class WorkbookRef:
    path: str
    filename: str
    sheet_names: List[str]
    size_bytes: int


@dataclass
class ProjectSummary:
    label: str
    concrete_m3: float
    shuttering_m2: float
    diameter_kg: Dict[int, float]
    total_steel_kg: float
    source_row: int
    total_steel_mt: float = 0.0
    total_steel_source: str = "kg_column"
    diameter_mt: Dict[int, float] = field(default_factory=dict)
    parser_warnings: List[str] = field(default_factory=list)


@dataclass
class RoleLine:
    role: str
    description: str
    diameter_mm: Optional[float]
    spacing_m: Optional[float]
    bar_count: Optional[float]
    cut_length_m: Optional[float]
    total_length_m: Optional[float]
    steel_kg: float
    diameter_kg: Dict[int, float]


@dataclass
class BeamBlock:
    beam_id: str
    start_row: int
    end_row: int
    concrete_m3: float
    shuttering_m2: float
    lines: List[RoleLine] = field(default_factory=list)
    diameter_kg: Dict[int, float] = field(default_factory=dict)
    total_steel_kg: float = 0.0


@dataclass
class ModelBeam:
    beam_id: str
    span_m: float
    total_bars: int
    steel_kg: float
    diameter_kg: Dict[int, float]
    roles: List[RoleLine] = field(default_factory=list)


@dataclass
class ComparisonResult:
    model_version: str
    phase_id: str
    timestamp: str
    model_workbook: WorkbookRef
    estimator_workbook: WorkbookRef
    estimator_summary: Optional[ProjectSummary] = None
    model_summary: Optional[ProjectSummary] = None
    summary_comparison: Dict[str, Any] = field(default_factory=dict)
    diameter_comparison: List[Dict[str, Any]] = field(default_factory=list)
    role_comparison: List[Dict[str, Any]] = field(default_factory=list)
    beam_comparisons: List[Dict[str, Any]] = field(default_factory=list)
    beam_coverage: Dict[str, Any] = field(default_factory=dict)
    engineering_differences: List[Dict[str, Any]] = field(default_factory=list)
    root_causes: Dict[str, Any] = field(default_factory=dict)
    accuracy_metrics: Dict[str, Any] = field(default_factory=dict)
    top_20_differences: List[Dict[str, Any]] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=dict)
    recommended_investigation_order: List[str] = field(default_factory=list)
