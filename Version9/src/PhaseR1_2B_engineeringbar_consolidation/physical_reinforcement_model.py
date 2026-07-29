"""Physical Reinforcement Member — one structural component, one model."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PhysicalReinforcementMember:
    """Exactly one physical reinforcement component on a beam."""

    member_id: str
    beam_id: str
    bar_role: str
    diameter_mm: float
    quantity: int
    zone: str
    spacing_mm: Optional[float] = None
    development_length_mm: Optional[int] = None
    cover_mm: Optional[int] = None
    steel_grade: str = "Y"
    concrete_grade: str = "M30"
    hook_rule: Optional[int] = None
    lap_rule_mm: Optional[int] = None
    bar_label: str = ""
    source_phase: str = "R.1.2B"
    evidence_bar_indices: List[int] = field(default_factory=list)
    evidence_labels: List[str] = field(default_factory=list)
    annotation_ids: List[str] = field(default_factory=list)
    merged_evidence_ids: List[str] = field(default_factory=list)
    consolidation_reason: str = ""
    similarity_score: float = 1.0
    confidence: float = 1.0
    engineering_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_engineering_bar_dict(self) -> Dict[str, Any]:
        """Emit a production EngineeringBarModel-compatible dict."""
        meta = dict(self.engineering_metadata or {})
        meta.update({
            "physical_member_id": self.member_id,
            "consolidation_reason": self.consolidation_reason,
            "similarity_score": self.similarity_score,
            "confidence": self.confidence,
            "evidence_labels": list(self.evidence_labels),
            "merged_evidence_ids": list(self.merged_evidence_ids),
            "annotation_ids": list(self.annotation_ids),
            "source_phase_consolidation": "R.1.2B",
        })
        return {
            "beam_id": self.beam_id,
            "bar_role": self.bar_role,
            "diameter_mm": self.diameter_mm,
            "quantity": self.quantity,
            "zone": self.zone,
            "spacing_mm": self.spacing_mm,
            "development_length_mm": self.development_length_mm,
            "cover_mm": self.cover_mm,
            "steel_grade": self.steel_grade,
            "concrete_grade": self.concrete_grade,
            "hook_rule": self.hook_rule,
            "lap_rule_mm": self.lap_rule_mm,
            "source_phase": "R.1.2B",
            "bar_label": self.bar_label,
            "engineering_metadata": meta,
        }
