"""
geometry_reporter.py — Generate GeometryReport.md for Phase R.3.
MODEL_VERSION: 8.0.0
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


class GeometryReporter:

    def generate_markdown(
        self,
        stats:      Dict[str, Any],
        validation: Dict[str, Any],
        phase_meta: Dict[str, Any],
    ) -> str:
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"

        lines = [
            "# Phase R.3 — Geometry Context Engine",
            f"**MODEL_VERSION:** {phase_meta.get('model_version', '8.0.0')}",
            f"**Generated:** {ts}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Beams processed | {stats.get('beam_count', 0)} |",
            f"| GeometryContexts produced | {stats.get('context_count', 0)} |",
            f"| Validation rules passed | {validation.get('summary', 'N/A')} |",
            f"| Phase intent status | UNKNOWN (geometry-only) |",
            "",
            "---",
            "",
            "## Architecture",
            "",
            "```",
            "R.2.1D Evidence & Intent Hypothesis Engine",
            "    |",
            "    v",
            "R.3 Geometry Context Engine  [this phase]",
            "    |",
            "    v",
            "R.4 Engineering Intent Resolver  [future]",
            "```",
            "",
            "> R.3 answers ONLY: **Where is this reinforcement annotation located?**",
            "> R.3 does NOT answer: What does this reinforcement mean?",
            "",
            "---",
            "",
            "## Beam Axis Statistics",
            "",
        ]

        ax_stats = stats.get("beam_axis", {})
        lines += [
            f"| Property | Value |",
            f"|----------|-------|",
            f"| Beam count | {ax_stats.get('count', 0)} |",
            f"| Min span | {ax_stats.get('min_length_mm', 0):.0f} mm |",
            f"| Max span | {ax_stats.get('max_length_mm', 0):.0f} mm |",
            f"| Mean span | {ax_stats.get('mean_length_mm', 0):.0f} mm |",
            "",
            "**Orientations:**",
            "",
        ]
        for k, v in ax_stats.get("orientations", {}).items():
            lines.append(f"- {k}: {v}")
        lines.append("")
        lines.append("**Geometry sources:**")
        lines.append("")
        for k, v in ax_stats.get("geometry_sources", {}).items():
            lines.append(f"- {k}: {v}")
        lines.append("")

        # Support stats
        sup = stats.get("support", {})
        lines += [
            "---",
            "",
            "## Support Statistics",
            "",
            f"| Property | Value |",
            f"|----------|-------|",
            f"| Total supports | {sup.get('total_supports', 0)} |",
            f"| Avg support width | {sup.get('avg_support_width_mm', 0):.0f} mm |",
            f"| Beams with supports | {sup.get('beams_with_supports', 0)} |",
            "",
        ]

        # Projection stats
        proj = stats.get("projection", {})
        lines += [
            "---",
            "",
            "## Projection Statistics",
            "",
            f"| Property | Value |",
            f"|----------|-------|",
            f"| Min projection | {proj.get('min_projection_mm', 0):.0f} mm |",
            f"| Max projection | {proj.get('max_projection_mm', 0):.0f} mm |",
            f"| Mean projection | {proj.get('mean_projection_mm', 0):.0f} mm |",
            "",
            "**Confidence distribution:**",
            "",
        ]
        for k, v in proj.get("confidence_distribution", {}).items():
            lines.append(f"- {k}: {v}")
        lines.append("")
        lines.append("**Position source distribution:**")
        lines.append("")
        for k, v in proj.get("position_source_distribution", {}).items():
            lines.append(f"- {k}: {v}")
        lines.append("")

        # Normalized position histogram
        lines += [
            "---",
            "",
            "## Normalized Position Histogram (0.0 → 1.0)",
            "",
            "| Bin | Count |",
            "|-----|-------|",
        ]
        for bin_key, cnt in stats.get("normalized_position_histogram", {}).items():
            lines.append(f"| {bin_key} | {cnt} |")
        lines.append("")

        # Zone distribution
        lines += [
            "---",
            "",
            "## Span Zone Distribution",
            "",
            "| Zone | Count |",
            "|------|-------|",
        ]
        for z, cnt in stats.get("span_zone_distribution", {}).items():
            lines.append(f"| {z} | {cnt} |")
        lines.append("")

        # Extent distribution
        lines += [
            "---",
            "",
            "## Extent Evidence Distribution",
            "",
            "| Label | Count |",
            "|-------|-------|",
        ]
        for ext, cnt in stats.get("extent_distribution", {}).items():
            lines.append(f"| {ext} | {cnt} |")
        lines.append("")

        # Validation summary
        lines += [
            "---",
            "",
            "## Validation Summary",
            "",
            f"**Result: {validation.get('summary', 'N/A')}**",
            "",
            "| Rule | Status | Detail |",
            "|------|--------|--------|",
        ]
        for rule_id, result in validation.get("rules", {}).items():
            icon   = "PASS" if result["passed"] else "FAIL"
            desc   = self.RULES_DESC.get(rule_id, "")
            detail = result.get("detail", "")
            lines.append(f"| {rule_id} — {desc} | {icon} | {detail} |")
        lines.append("")

        lines += [
            "---",
            "",
            "## Geometry Confidence Distribution",
            "",
            "| Confidence | Count |",
            "|------------|-------|",
        ]
        for lvl, cnt in stats.get("geometry_confidence_distribution", {}).items():
            lines.append(f"| {lvl} | {cnt} |")
        lines.append("")

        lines += [
            "---",
            "",
            "## Design Principles",
            "",
            "- Intent remains **UNKNOWN** — this phase provides geometry evidence only",
            "- All geometry computations are **deterministic** (no AI, no heuristics)",
            "- Beam axis derived from `geometry_registry.json` (local coordinate space)",
            "- Annotation position derived from `reinforcement_annotations.json` (DXF space)",
            "- Support zones derived from `geometry_registry.support_locations`",
            "- No engineering equations, BBS, steel calculations, or Excel modified",
            "",
            "---",
            "",
            f"*R.3 Geometry Context Engine | MODEL_VERSION: {phase_meta.get('model_version', '8.0.0')}*",
        ]

        return "\n".join(lines)

    RULES_DESC = {
        "RULE_1":  "Every EngineeringFact receives GeometryContext",
        "RULE_2":  "No missing beam IDs",
        "RULE_3":  "Projection on beam axis",
        "RULE_4":  "Normalized position in [0.0, 1.0]",
        "RULE_5":  "Every beam has BeamAxis",
        "RULE_6":  "Every beam has SupportLocation",
        "RULE_7":  "No duplicate contexts",
        "RULE_8":  "No hardcoded beam names",
        "RULE_9":  "Intent unchanged (UNKNOWN)",
        "RULE_10": "No engineering equations modified",
        "RULE_11": "Backward compatibility maintained",
        "RULE_12": "Production workbook generated",
    }
