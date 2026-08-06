"""
coverage_reporter.py — Phase R.1.1A engineering report (markdown).
"""
from __future__ import annotations

from typing import Any, Dict


class CoverageReporter:

    def generate(self, result: Dict[str, Any]) -> str:
        val = result.get("validation", {})
        stats = result.get("coverage_statistics", {})
        set3 = result.get("benchmark_results", {}).get("Set_3", {})
        base = set3.get("baseline", {})
        imp = set3.get("improved", {})
        rec = result.get("recommendation", "B")

        lines = [
            "# Phase R.1.1A — Annotation Coverage Recovery Report",
            "",
            f"**MODEL_VERSION:** {result.get('model_version', '8.2.0')}",
            f"**Validation:** {val.get('passed', 0)}/{val.get('total', 8)} rules passed",
            "",
            "## 1. Executive Summary",
            "",
            result.get("executive_summary", ""),
            "",
            "## 2. Previous vs Improved Coverage",
            "",
            "| Metric | Baseline (Set 3) | Improved (Set 3) |",
            "|--------|------------------|------------------|",
            f"| Total beams | {base.get('total_beams', '?')} | {imp.get('total_beams', '?')} |",
            f"| Beams with reinforcement | {base.get('beams_with_reinforcement', '?')} | {imp.get('beams_with_reinforcement', '?')} |",
            f"| Total annotations | {base.get('total_annotations', '?')} | {imp.get('total_annotations', '?')} |",
            f"| Coverage % | {base.get('coverage_pct', '?')} | {imp.get('coverage_pct', '?')} |",
            "",
            "## 3. Beam Detail Reconstruction Results",
            "",
            f"- Detail clusters: **{stats.get('total_clusters', 0)}**",
            f"- Adaptive search regions: **{stats.get('search_region_count', 0)}**",
            "",
            "## 4. Annotation Recovery Statistics",
            "",
            f"- Recovered orphan annotations: **{stats.get('orphan_recovered', 0)}**",
            f"- Unrecovered orphans: **{stats.get('orphan_unrecovered', 0)}**",
            "",
            "## 5. Leader-Based Association Results",
            "",
            f"- Leader associations: **{stats.get('leader_associations', 0)}**",
            "",
            "## 6. Orphan Annotation Recovery Results",
            "",
            f"- Orphan recovery pass executed: **{result.get('orphan_recovery_executed', False)}**",
            "",
            "## 7. Coverage by Benchmark Set",
            "",
        ]

        for set_name, data in result.get("benchmark_results", {}).items():
            imp_d = data.get("improved", {})
            lines.append(
                f"- **{set_name}**: {imp_d.get('total_annotations', 0)} annotations on "
                f"{imp_d.get('beams_with_reinforcement', 0)}/{imp_d.get('total_beams', 0)} beams"
            )

        lines.extend([
            "",
            "## 8. Engineering Confidence Analysis",
            "",
            f"- Average association confidence: **{stats.get('average_confidence', 0)}**",
            f"- Cluster/hybrid associations: **{stats.get('cluster_associations', 0)}**",
            "",
            "## 9. Remaining Undiscovered Beam Details",
            "",
            f"- Beams without reinforcement (Set 3): **{imp.get('beams_without_reinforcement', '?')}**",
            "",
            "## 10. Recommendation",
            "",
        ])

        if rec == "A":
            lines.append(
                "**A — Ready for Phase R.1.1B** — Production Integration of Engineering Interpretation"
            )
        else:
            lines.append(
                "**B — Additional annotation discovery improvements required**"
            )

        return "\n".join(lines)
