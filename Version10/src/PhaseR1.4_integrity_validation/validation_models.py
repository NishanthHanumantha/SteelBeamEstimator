"""Shared validation models for Phase R.1.4."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class RuleResult:
    rule_id: str
    status: str  # PASS, WARNING, ERROR
    detail: str
    passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    model_version: str = "7.8.0"
    phase: str = "R.1.4"
    rules: Dict[str, RuleResult] = field(default_factory=dict)
    coverage: Dict[str, Any] = field(default_factory=dict)
    quality_gate: Dict[str, Any] = field(default_factory=dict)
    pipeline_health_score: float = 0.0
    integrity_score: float = 0.0
    beam_status_matrix: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    quality_gate_status: str = "PASS"
    all_rules_passed: bool = False
    production_allowed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "phase": self.phase,
            "rules": {k: v.to_dict() for k, v in self.rules.items()},
            "coverage": self.coverage,
            "quality_gate": self.quality_gate,
            "pipeline_health_score": self.pipeline_health_score,
            "integrity_score": self.integrity_score,
            "beam_status_matrix_count": len(self.beam_status_matrix),
            "warnings": self.warnings,
            "errors": self.errors,
            "quality_gate_status": self.quality_gate_status,
            "all_rules_passed": self.all_rules_passed,
            "production_allowed": self.production_allowed,
        }
