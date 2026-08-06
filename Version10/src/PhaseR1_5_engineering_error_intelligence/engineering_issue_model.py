"""
Immutable EngineeringIssue model for Phase R.1.5.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple

MODEL_VERSION = "8.7.0"

ENGINEERING_CATEGORIES: Tuple[str, ...] = (
    "Beam Discovery",
    "Annotation Association",
    "Role Classification",
    "Diameter Interpretation",
    "Quantity Interpretation",
    "Development Length",
    "Cut Length",
    "Support Zone Interpretation",
    "Curtailment",
    "Continuity",
    "Stirrup Interpretation",
    "Hook Interpretation",
    "Spacer Interpretation",
    "Side Face Reinforcement",
    "Piece Generation",
    "Steel Aggregation",
    "Weight Calculation",
    "Workbook Export",
    "Unknown",
)

ALLOWED_PHASES: Tuple[str, ...] = (
    "Annotation",
    "Fact",
    "Intent",
    "Detail",
    "Piece",
    "EngineeringBar",
    "Steel",
    "Workbook",
)

SEVERITIES: Tuple[str, ...] = (
    "Critical",
    "Major",
    "Moderate",
    "Minor",
    "Informational",
)


@dataclass(frozen=True)
class EngineeringIssue:
    issue_id: str
    category: str
    subcategory: str
    originating_phase: str
    affected_entities: Tuple[str, ...]
    affected_beams: Tuple[str, ...]
    affected_roles: Tuple[str, ...]
    affected_diameters: Tuple[int, ...]
    frequency: int
    severity: str
    engineering_impact: float
    steel_impact_kg: float
    weight_percentage: float
    production_accuracy_loss: float
    root_cause: str
    confidence: float
    recommended_fix: str
    recommended_phase: str
    supporting_evidence: Tuple[str, ...]
    validation_flags: Tuple[str, ...]
    source_phase: str = "R.1.4"
    finding_ids: Tuple[str, ...] = field(default_factory=tuple)
    expected_accuracy_gain: float = 0.0
    priority: str = "Medium"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["model_version"] = MODEL_VERSION
        return d


@dataclass
class RawFinding:
    finding_id: str
    error_type: str
    entity: str
    field: str
    message: str
    originating_phase: str = ""
    confidence: float = 0.5
    suggested_fix: str = ""
    role: str = ""
    diameter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
