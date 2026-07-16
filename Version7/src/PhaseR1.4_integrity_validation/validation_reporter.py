"""Validation reporter — console, markdown, JSON."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict

from .validation_models import ValidationResult


class ValidationReporter:

    MODEL_VERSION = "7.8.0"

    RULE_DESCRIPTIONS = {
        "RULE_1": "Every registry beam has reinforcement status",
        "RULE_2": "Every EngineeringBarModel beam exists in registry",
        "RULE_3": "No orphan reinforcement objects",
        "RULE_4": "No duplicate beam ids",
        "RULE_5": "No duplicate engineering bar ids",
        "RULE_6": "Mandatory fields present on every bar",
        "RULE_7": "Every role is valid",
        "RULE_8": "Diameter > 0",
        "RULE_9": "Quantity > 0",
        "RULE_10": "Coverage calculated dynamically",
        "RULE_11": "Propagation calculated dynamically",
        "RULE_12": "Steel Weight beams originate from EngineeringBarModel",
        "RULE_13": "No REFERENCE_CLASSIFICATION in production path",
        "RULE_14": "No benchmark filtering",
        "RULE_15": "Pipeline health score computed",
    }

    def build_engineering_summary(self, result: ValidationResult) -> Dict[str, Any]:
        cov = result.coverage
        return {
            "model_version": self.MODEL_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "total_beams": cov.get("total_discovered_beams", 0),
            "covered_beams": cov.get("beams_with_reinforcement", 0),
            "coverage_pct": cov.get("coverage_pct", 0),
            "missing_beams": len(cov.get("missing_beams", [])),
            "empty_beams": cov.get("empty_beams", 0),
            "duplicate_beams": len(cov.get("duplicate_beams", [])),
            "orphan_groups": cov.get("orphan_reinforcement_groups", 0),
            "engineering_bars": cov.get("total_engineering_bars", 0),
            "pipeline_health_score": result.pipeline_health_score,
            "integrity_score": result.integrity_score,
            "quality_gate_status": result.quality_gate_status,
            "propagation_pct": cov.get("propagation_pct", 0),
            "production_allowed": result.production_allowed,
        }

    def build_markdown(self, result: ValidationResult) -> str:
        cov = result.coverage
        lines = [
            "# Phase R.1.4 — Reinforcement Integrity Validation Report",
            "",
            f"**MODEL_VERSION:** {self.MODEL_VERSION}",
            f"**Quality Gate:** {result.quality_gate_status}",
            f"**Integrity Score:** {result.integrity_score}",
            f"**Pipeline Health Score:** {result.pipeline_health_score}",
            "",
            "## Engineering Integrity Summary",
            "",
            f"- Total Beams: {cov.get('total_discovered_beams', 0)}",
            f"- Covered Beams: {cov.get('beams_with_reinforcement', 0)}",
            f"- Coverage %: {cov.get('coverage_pct', 0)}",
            f"- Propagation %: {cov.get('propagation_pct', 0)}",
            f"- Empty Beams: {cov.get('empty_beams', 0)}",
            f"- Engineering Bars: {cov.get('total_engineering_bars', 0)}",
            "",
            "## Validation Rules",
            "",
        ]
        for rule_id in sorted(result.rules.keys()):
            rule = result.rules[rule_id]
            desc = self.RULE_DESCRIPTIONS.get(rule_id, rule_id)
            lines.append(f"- **{rule_id}** ({desc}): {rule.status} — {rule.detail}")

        if result.warnings:
            lines.extend(["", "## Warnings", ""])
            for w in result.warnings:
                lines.append(f"- {w}")

        if result.errors:
            lines.extend(["", "## Errors", ""])
            for e in result.errors:
                lines.append(f"- {e}")

        lines.extend([
            "",
            "## Generalization",
            "",
            "All metrics computed dynamically from Beam Registry and "
            "EngineeringBarModel. No benchmark-specific constants.",
            "",
        ])
        return "\n".join(lines)

    def print_console(self, result: ValidationResult) -> None:
        cov = result.coverage
        print(f"      Total beams:        {cov.get('total_discovered_beams', 0)}")
        print(f"      Covered beams:      {cov.get('beams_with_reinforcement', 0)}")
        print(f"      Coverage:           {cov.get('coverage_pct', 0)}%")
        print(f"      Propagation:        {cov.get('propagation_pct', 0)}%")
        print(f"      Engineering bars:   {cov.get('total_engineering_bars', 0)}")
        print(f"      Integrity score:    {result.integrity_score}")
        print(f"      Pipeline health:    {result.pipeline_health_score}")
        print(f"      Quality gate:       {result.quality_gate_status}")
        print("\n      Validation Rules:")
        for rule_id in sorted(result.rules.keys()):
            rule = result.rules[rule_id]
            print(f"        {rule_id}: {rule.status} — {rule.detail}")
