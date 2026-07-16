"""Data models for engineering consumption traceability."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class EngineeringBarTrace:
    trace_id: str
    beam_id: str
    bar_role: str
    diameter_mm: float
    quantity: int
    spacing_mm: Optional[float]
    development_length_mm: Optional[int]
    cover_mm: Optional[int]
    hook_rule: Optional[int]
    lap_rule_mm: Optional[int]
    source_phase: str
    bar_label: str
    engineering_metadata: Dict[str, Any] = field(default_factory=dict)
    steel_role: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SteelConsumptionTrace:
    trace_id: str
    consumed: bool
    weight_kg: Optional[float] = None
    unit_weight_kg: Optional[float] = None
    cut_length_mm: Optional[float] = None
    formula_used: str = ""
    skip_reason: str = ""
    steel_bar_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BBSConsumptionTrace:
    trace_id: str
    consumed: bool
    row_index: Optional[int] = None
    description: str = ""
    diameter_mm: Optional[float] = None
    quantity: Optional[int] = None
    cut_length_m: Optional[float] = None
    weight_kg: Optional[float] = None
    skip_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsumptionMatrixRow:
    trace_id: str
    beam_id: str
    bar_role: str
    diameter_mm: float
    quantity: int
    steel: str
    bbs: str
    diameter_summary: str
    beam_total: str
    project_total: str
    excel: str
    root_cause: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsumptionValidationResult:
    model_version: str = "7.8.1"
    rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    all_passed: bool = False
    consumption_score: float = 0.0
    engineering_accuracy_score: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
