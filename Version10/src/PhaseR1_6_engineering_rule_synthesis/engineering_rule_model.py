"""
Immutable EngineeringRule model.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple

MODEL_VERSION = "8.8.0"

RULE_FAMILIES: Tuple[str, ...] = (
    "Beam Discovery",
    "Annotation Association",
    "Role Resolution",
    "Diameter Resolution",
    "Stirrup Interpretation",
    "Hook Interpretation",
    "Spacer Interpretation",
    "Side Face Reinforcement",
    "Development Length",
    "Cut Length",
    "Support Zone",
    "Curtailment",
    "Continuity",
    "Piece Generation",
    "Steel Aggregation",
    "Weight Calculation",
    "Workbook Mapping",
    "Future",
)

GAP_TYPES: Tuple[str, ...] = (
    "Missing Rule",
    "Incomplete Rule",
    "Incorrect Rule",
    "Weak Validation",
    "Missing Dependency",
    "Incorrect Mapping",
    "Incomplete Classification",
    "Incorrect Aggregation",
    "Unsupported Engineering Case",
    "Unsupported Estimator Convention",
)

RULE_STATUSES: Tuple[str, ...] = (
    "Missing",
    "Partial",
    "Correct",
    "Deprecated",
)


@dataclass(frozen=True)
class EngineeringRule:
    rule_id: str
    rule_name: str
    rule_family: str
    rule_category: str
    originating_issue: str
    originating_phase: str
    engineering_domain: str
    engineering_intent: str
    rule_description: str
    engineering_rationale: str
    trigger_conditions: Tuple[str, ...]
    required_inputs: Tuple[str, ...]
    decision_logic: Tuple[str, ...]
    expected_outputs: Tuple[str, ...]
    validation_criteria: Tuple[str, ...]
    priority: int
    confidence: float
    expected_accuracy_gain: float
    estimated_steel_gain_kg: float
    affected_roles: Tuple[str, ...]
    affected_diameters: Tuple[int, ...]
    affected_beams: Tuple[str, ...]
    dependencies: Tuple[str, ...]
    conflicting_rules: Tuple[str, ...]
    implementation_phase: str
    status: str
    source_phase: str
    supporting_evidence: Tuple[str, ...]
    validation_flags: Tuple[str, ...]
    originating_issues: Tuple[str, ...] = field(default_factory=tuple)
    finding_ids: Tuple[str, ...] = field(default_factory=tuple)
    gap_type: str = "Missing Rule"
    pattern_id: str = ""
    estimated_effort: str = "M"
    engineering_risk: str = "Medium"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["model_version"] = MODEL_VERSION
        return d
