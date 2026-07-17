"""Configurable production quality gate."""
from __future__ import annotations
from typing import Any, Dict, List

from .validation_models import RuleResult, ValidationResult


class IntegrityQualityGate:

    def __init__(self, gate_config: Dict[str, Any]):
        self._cfg = gate_config

    def evaluate(
        self,
        result: ValidationResult,
        coverage: Dict[str, Any],
        rules: Dict[str, RuleResult],
    ) -> Dict[str, Any]:
        min_beam_cov = float(self._cfg.get("minimum_beam_coverage", 0.0))
        min_bar_cov = float(self._cfg.get("minimum_bar_coverage", 0.0))
        max_orphans = int(self._cfg.get("maximum_orphans", 0))
        max_dups = int(self._cfg.get("maximum_duplicates", 0))
        allow_empty = bool(self._cfg.get("allow_empty_beams", True))
        strict = bool(self._cfg.get("strict_mode", False))
        warning_mode = bool(self._cfg.get("warning_mode", True))

        beam_cov_ratio = coverage.get("coverage_pct", 0) / 100.0
        bar_cov_ratio = coverage.get("bar_coverage_pct", 0) / 100.0
        orphans = len(coverage.get("orphan_engineering_beams", []))
        orphans += coverage.get("orphan_reinforcement_groups", 0)
        dups = len(coverage.get("duplicate_beams", []))
        empty_count = coverage.get("empty_beams", 0)

        failures: List[str] = []
        warnings: List[str] = []

        if beam_cov_ratio < min_beam_cov:
            failures.append(
                f"beam_coverage {beam_cov_ratio:.2%} < {min_beam_cov:.2%}"
            )
        if bar_cov_ratio < min_bar_cov:
            failures.append(
                f"bar_coverage {bar_cov_ratio:.2%} < {min_bar_cov:.2%}"
            )
        if orphans > max_orphans:
            failures.append(f"orphans {orphans} > {max_orphans}")
        if dups > max_dups:
            failures.append(f"duplicates {dups} > {max_dups}")
        if not allow_empty and empty_count > 0:
            warnings.append(f"empty_beams={empty_count}")

        for rule_id, rule in rules.items():
            if rule_id.startswith("_"):
                continue
            if rule.status == "ERROR":
                failures.append(f"{rule_id}: {rule.detail}")
            elif rule.status == "WARNING" and warning_mode:
                warnings.append(f"{rule_id}: {rule.detail}")

        status = "PASS"
        production_allowed = True

        if failures:
            if strict:
                status = "FAIL"
                production_allowed = False
            else:
                status = "WARN"
                warnings.extend(failures)
        elif warnings:
            status = "WARN"

        return {
            "status": status,
            "production_allowed": production_allowed,
            "strict_mode": strict,
            "warning_mode": warning_mode,
            "thresholds": {
                "minimum_beam_coverage": min_beam_cov,
                "minimum_bar_coverage": min_bar_cov,
                "maximum_orphans": max_orphans,
                "maximum_duplicates": max_dups,
                "allow_empty_beams": allow_empty,
            },
            "measured": {
                "beam_coverage_ratio": beam_cov_ratio,
                "bar_coverage_ratio": bar_cov_ratio,
                "orphans": orphans,
                "duplicates": dups,
                "empty_beams": empty_count,
            },
            "failures": failures,
            "warnings": warnings,
        }
