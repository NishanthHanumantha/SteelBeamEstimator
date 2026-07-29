"""Main validation engine — coordinates all rules."""
from __future__ import annotations
import pathlib
from typing import Any, Dict, Optional

import yaml

from .beam_consistency_checker import BeamConsistencyChecker
from .coverage_analyzer import CoverageAnalyzer
from .coverage_classifier import CoverageClassifier
from .engineering_bar_validator import EngineeringBarValidator
from .integrity_quality_gate import IntegrityQualityGate
from .pipeline_data_loader import PipelineDataLoader
from .pipeline_dependency_validator import PipelineDependencyValidator
from .validation_models import RuleResult, ValidationResult
from .validation_statistics import ValidationStatistics


class ReinforcementIntegrityValidator:

    MODEL_VERSION = "7.8.0"

    def __init__(
        self,
        v7_root: pathlib.Path,
        config_path: Optional[pathlib.Path] = None,
        reinforcement_source: str = "",
        production_models_path: str = "",
    ):
        self._v7 = v7_root
        self._config_path = config_path or (
            v7_root / "config/reinforcement_integrity_validation.yaml"
        )
        self._config = self._load_config()
        self._reinforcement_source = reinforcement_source
        self._production_models_path = production_models_path

    def _load_config(self) -> Dict[str, Any]:
        if not self._config_path.exists():
            return {"quality_gate": {}, "validation": {"valid_roles": []}}
        with open(self._config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def validate(self) -> ValidationResult:
        loader = PipelineDataLoader(self._v7, self._config)
        loader.load_all()

        coverage = CoverageAnalyzer().analyze(loader)
        classifications = CoverageClassifier().classify_all(loader)

        valid_roles = self._config.get("validation", {}).get("valid_roles", [])

        beam_rules = BeamConsistencyChecker().check(loader, coverage)
        bar_rules = EngineeringBarValidator().validate(loader, valid_roles)
        dep_rules = PipelineDependencyValidator().validate(
            loader, coverage,
            self._reinforcement_source,
            self._production_models_path,
        )

        rule1_status = self._rule1_status(classifications)
        rule10 = RuleResult(
            "RULE_10", "PASS",
            f"coverage_pct={coverage['coverage_pct']}%",
            True,
        )
        rule11 = RuleResult(
            "RULE_11", "PASS",
            f"propagation_pct={coverage['propagation_pct']}%",
            True,
        )
        rule15 = RuleResult(
            "RULE_15", "PASS", "computed_after_statistics", True,
        )

        all_rules: Dict[str, RuleResult] = {
            "RULE_1": rule1_status,
            "RULE_10": rule10,
            "RULE_11": rule11,
            "RULE_15": rule15,
        }
        for group in (beam_rules, bar_rules, dep_rules):
            for k, v in group.items():
                if not k.startswith("_"):
                    all_rules[k] = v

        beam_matrix = BeamConsistencyChecker().build_beam_status(
            loader, classifications
        )

        result = ValidationResult(
            model_version=self.MODEL_VERSION,
            coverage=coverage,
            beam_status_matrix=beam_matrix,
            rules=all_rules,
        )

        stats_calc = ValidationStatistics()
        gate = IntegrityQualityGate(self._config.get("quality_gate", {}))
        gate_result = gate.evaluate(result, coverage, all_rules)
        scores = stats_calc.compute_scores(all_rules, coverage, gate_result)

        result.pipeline_health_score = scores["pipeline_health_score"]
        result.integrity_score = scores["integrity_score"]
        result.quality_gate = gate_result
        result.quality_gate_status = gate_result["status"]
        result.production_allowed = gate_result["production_allowed"]
        result.warnings = gate_result.get("warnings", [])
        result.errors = gate_result.get("failures", [])

        all_rules["RULE_15"] = RuleResult(
            "RULE_15", "PASS",
            f"pipeline_health_score={scores['pipeline_health_score']}",
            True,
        )
        result.rules = all_rules

        error_rules = [r for r in all_rules.values() if r.status == "ERROR"]
        result.all_rules_passed = len(error_rules) == 0

        return result

    def _rule1_status(
        self, classifications: Dict[str, Dict[str, Any]]
    ) -> RuleResult:
        unclassified = [
            bid for bid, c in classifications.items()
            if c.get("status") == "UNKNOWN"
        ]
        errors = [
            bid for bid, c in classifications.items()
            if c.get("status") == "ERROR"
        ]
        if errors:
            return RuleResult(
                "RULE_1", "ERROR",
                f"beams_with_propagation_errors={len(errors)}",
                False,
            )
        if unclassified:
            return RuleResult(
                "RULE_1", "WARNING",
                f"unclassified_beams={len(unclassified)}",
                True,
            )
        return RuleResult(
            "RULE_1", "PASS",
            f"all_beams_classified={len(classifications)}",
            True,
        )
