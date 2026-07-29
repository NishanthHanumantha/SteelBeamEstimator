"""
Beam stirrup coverage models for RULE-012.
MODEL_VERSION: 8.8.2
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "8.8.2"
RULE_ID = "RULE-012"

PIPELINE_STAGES: Tuple[str, ...] = (
    "Annotation Discovery",
    "Intent Resolution",
    "Reinforcement Detail",
    "Piece Generation",
    "EngineeringBars",
)

VALIDATION_STATUSES: Tuple[str, ...] = ("PASS", "FAIL", "UNKNOWN")


@dataclass(frozen=True)
class StagePresence:
    annotation: bool
    intent: bool
    detail: bool
    piece: bool
    engineering_bar: bool

    def to_dict(self) -> Dict[str, bool]:
        return {
            "Annotation Discovery": self.annotation,
            "Intent Resolution": self.intent,
            "Reinforcement Detail": self.detail,
            "Piece Generation": self.piece,
            "EngineeringBars": self.engineering_bar,
        }

    def first_missing_stage(self) -> Optional[str]:
        ordered = (
            ("Annotation Discovery", self.annotation),
            ("Intent Resolution", self.intent),
            ("Reinforcement Detail", self.detail),
            ("Piece Generation", self.piece),
            ("EngineeringBars", self.engineering_bar),
        )
        for name, present in ordered:
            if not present:
                return name
        return None


@dataclass(frozen=True)
class ObjectLevelCoverage:
    intent: bool
    detail: bool
    piece: bool
    engineering_bar: bool

    def to_dict(self) -> Dict[str, str]:
        return {
            "Intent": "YES" if self.intent else "NO",
            "Detail": "YES" if self.detail else "NO",
            "Piece": "YES" if self.piece else "NO",
            "EngineeringBar": "YES" if self.engineering_bar else "NO",
        }


@dataclass
class BeamCoverageRecord:
    beam_id: str
    beam_exists: bool
    top_exists: bool
    bottom_exists: bool
    stirrup_exists: bool
    status: str
    stage_presence: StagePresence
    object_level: ObjectLevelCoverage
    likely_missing_phase: Optional[str] = None
    missing_object: Optional[str] = None
    evidence: Tuple[str, ...] = field(default_factory=tuple)
    engineering_severity: str = "NONE"
    engineering_impact: str = ""
    expected_stirrup: str = "YES"
    detected_stirrup: str = "NO"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["stage_presence"] = self.stage_presence.to_dict()
        d["object_level"] = self.object_level.to_dict()
        d["evidence"] = list(self.evidence)
        d["model_version"] = MODEL_VERSION
        d["rule_id"] = RULE_ID
        return d


@dataclass(frozen=True)
class ProjectCoverageMetrics:
    beam_count: int
    detected_stirrup_families: int
    coverage_pct: float
    pass_count: int
    fail_count: int
    unknown_count: int
    pass_pct: float
    fail_pct: float
    missing_pct: float
    phase_distribution: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": MODEL_VERSION,
            "beam_count": self.beam_count,
            "detected_stirrup_families": self.detected_stirrup_families,
            "coverage_pct": self.coverage_pct,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "unknown_count": self.unknown_count,
            "pass_pct": self.pass_pct,
            "fail_pct": self.fail_pct,
            "missing_pct": self.missing_pct,
            "phase_distribution": dict(self.phase_distribution),
        }
