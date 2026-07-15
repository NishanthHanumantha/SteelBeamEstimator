"""Consumption models for Phase R.2B."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParameterConsumption:
    parameter: str
    module: str
    old_source: str
    new_source: str
    consumed: bool
    fallback: bool
    evidence: str = ""


@dataclass
class DependencyNode:
    module: str
    file_path: str
    hardcoded_patterns: List[str] = field(default_factory=list)
    consumes_engineering_context: bool = False
    parameters: List[str] = field(default_factory=list)


@dataclass
class ConsumptionAuditResult:
    parameter: str
    rule_id: str
    passed: bool
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter": self.parameter,
            "rule_id": self.rule_id,
            "passed": self.passed,
            "status": "PASS" if self.passed else "FAIL",
            "evidence": self.evidence,
        }


@dataclass
class ConsumptionReport:
    model_version: str = "7.6.0"
    total_modules_audited: int = 0
    consumption_rate: str = "0%"
    parameter_matrix: List[ParameterConsumption] = field(default_factory=list)
    validation_rules: List[ConsumptionAuditResult] = field(default_factory=list)
    production_workbook_generated: bool = False
    steel_weight_kg: float = 0.0
    loader_summary: Optional[Dict[str, Any]] = None
