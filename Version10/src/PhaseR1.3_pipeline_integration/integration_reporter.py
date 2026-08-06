"""Integration reporter for Phase R.1.3."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict


class IntegrationReporter:

    MODEL_VERSION = "7.7.0"

    def build_summary(
        self,
        validation: Dict[str, Any],
        statistics: Dict[str, Any],
        comparison: Dict[str, Any],
        source_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "phase": "R.1.3",
            "title": "Generalized Reinforcement Pipeline Integration",
            "model_version": self.MODEL_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "PASS" if validation.get("all_passed") else "FAIL",
            "validation_score": validation.get("score"),
            "source": source_report,
            "statistics": statistics,
            "comparison": comparison,
            "architecture": {
                "pipeline": [
                    "DXF",
                    "V.ROOT.1",
                    "R.1 Discovery",
                    "R.1.1 Adapter",
                    "EngineeringBarModel",
                    "L.2 Engineering Processing",
                    "Steel Weight",
                    "BBS",
                    "Excel",
                ],
                "reinforcement_source": "EngineeringBarModel (R.1.3)",
                "reference_classification_removed": True,
            },
        }

    def build_engineering_validation_md(
        self,
        validation: Dict[str, Any],
        statistics: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> str:
        lines = [
            "# Phase R.1.3 — Engineering Validation Report",
            "",
            f"**MODEL_VERSION:** {self.MODEL_VERSION}",
            f"**Status:** {'PASS' if validation.get('all_passed') else 'FAIL'}",
            f"**Validation Score:** {validation.get('score')}",
            "",
            "## Validation Rules",
            "",
        ]
        for rule_id, rule in validation.get("rules", {}).items():
            status = "PASS" if rule["passed"] else "FAIL"
            desc = PipelineValidatorRules.get(rule_id, rule_id)
            lines.append(f"- **{rule_id}** ({desc}): {status} — {rule['detail']}")

        lines.extend([
            "",
            "## Propagation Statistics",
            "",
            f"- Engineering bars created: {statistics.get('engineering_bars_created', 0)}",
            f"- Propagation: {statistics.get('propagation_pct', 0)}%",
            f"- Propagation loss: {statistics.get('propagation_loss', 0)}",
            "",
            "## Before vs After",
            "",
        ])
        before = comparison.get("before", {})
        after = comparison.get("after", {})
        for key in [
            "beams_reaching_steel", "beams_reaching_bbs",
            "beams_reaching_excel", "total_steel_kg", "bbs_rows",
        ]:
            lines.append(
                f"- {key}: {before.get(key, 'N/A')} -> {after.get(key, 'N/A')}"
            )

        lines.extend([
            "",
            "## Remaining Limitations",
            "",
            "- B34, B35, B43 have no R.1 reinforcement (empty beams)",
            "- L.2 legacy path retained for backward compatibility only",
            "",
        ])
        return "\n".join(lines)


# Avoid circular import — inline rule descriptions
PipelineValidatorRules = {
    "RULE_1": "All R.1 beams converted",
    "RULE_2": "EngineeringBarModel created",
    "RULE_3": "No benchmark beam filtering",
    "RULE_4": "No REFERENCE_CLASSIFICATION dependency",
    "RULE_5": "Steel Weight consumes EngineeringBarModel",
    "RULE_6": "BBS consumes EngineeringBarModel",
    "RULE_7": "Excel consumes EngineeringBarModel",
    "RULE_8": "No engineering equations changed",
    "RULE_9": "Backward compatibility preserved",
    "RULE_10": "62 beams propagate to production",
}
