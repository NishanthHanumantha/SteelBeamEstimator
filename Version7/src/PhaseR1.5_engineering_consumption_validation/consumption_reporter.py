"""Consumption validation reporter."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List


class ConsumptionReporter:

    MODEL_VERSION = "7.8.1"

    def build_markdown(
        self,
        stats: Dict[str, Any],
        validation: Any,
        qty_validation: Dict[str, Any],
        losses: Dict[str, Any],
        excel_trace: Dict[str, Any],
        root_causes: Dict[str, int],
    ) -> str:
        ref = excel_trace.get("reference_comparison", {})
        lines = [
            "# Phase R.1.5 — Engineering Consumption Validation Report",
            "",
            f"**MODEL_VERSION:** {self.MODEL_VERSION}",
            f"**Status:** {'PASS' if validation.all_passed else 'FAIL'}",
            f"**Consumption Score:** {stats.get('consumption_pct', 0)}%",
            f"**Engineering Accuracy:** {validation.engineering_accuracy_score}",
            "",
            "## Engineering Bar Trace Statistics",
            "",
            f"1. EngineeringBarModels: **{stats.get('engineering_bars_loaded', 0)}**",
            f"2. Reach Steel Weight: **{stats.get('reach_steel', 0)}**",
            f"3. Reach BBS: **{stats.get('reach_bbs', 0)}**",
            f"4. Reach Diameter Summary: **{stats.get('reach_diameter_summary', 0)}**",
            f"5. Reach Beam Totals: **{stats.get('reach_beam_total', 0)}**",
            f"6. Reach Project Totals: **{stats.get('reach_project_total', 0)}**",
            f"7. Reach Excel: **{stats.get('reach_excel', 0)}**",
            "",
            "## Skipped Bars",
            "",
            f"- Lost before steel: {losses.get('lost_before_steel', 0)}",
            f"- Lost before BBS: {losses.get('lost_before_bbs', 0)}",
            f"- Skipped (classified): {stats.get('skipped_bars', 0)}",
            "",
            "## Under-Consumed Roles",
            "",
        ]
        for role in stats.get("under_consumed_roles", []):
            rc = stats.get("role_consumption", {}).get(role, {})
            lines.append(
                f"- {role}: expected qty {rc.get('expected', 0)}, "
                f"consumed {rc.get('consumed', 0)}"
            )

        lines.extend(["", "## Reference Workbook Comparison", ""])
        if ref:
            lines.append(
                f"- Project total delta: {ref.get('project_total_delta_kg', 'N/A')} kg"
            )
            lines.append(
                f"- Diameter mismatches: {ref.get('diameter_mismatch_count', 0)}"
            )
            lines.append(f"- Beam mismatches: {ref.get('beam_mismatch_count', 0)}")
            for dm in ref.get("diameter_mismatches", [])[:10]:
                lines.append(
                    f"  - Y{dm['diameter_mm']}: bars delta {dm['bar_delta']}, "
                    f"weight delta {dm['weight_delta_kg']} kg"
                )
        else:
            lines.append("- No reference workbook detected for this drawing set")

        lines.extend(["", "## Root Cause Summary", ""])
        for cause, count in sorted(root_causes.items(), key=lambda x: -x[1]):
            if cause:
                lines.append(f"- {cause}: {count}")

        lines.extend(["", "## Validation Rules", ""])
        for rule_id, rule in sorted(validation.rules.items()):
            lines.append(f"- **{rule_id}**: {rule['status']} — {rule['detail']}")

        lines.extend([
            "",
            "## Remaining Engineering Gaps",
            "",
            "Quantity differences vs reference estimator workbook are documented "
            "in root_cause_report.json. This phase does NOT modify engineering logic.",
            "",
        ])
        return "\n".join(lines)

    def build_summary(
        self, stats: Dict[str, Any], validation: Any
    ) -> Dict[str, Any]:
        return {
            "phase": "R.1.5",
            "model_version": self.MODEL_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "PASS" if validation.all_passed else "FAIL",
            "validation_score": (
                f"{sum(1 for r in validation.rules.values() if r['passed'])}"
                f"/{len(validation.rules)}"
            ),
            "statistics": stats,
            "read_only": True,
        }
