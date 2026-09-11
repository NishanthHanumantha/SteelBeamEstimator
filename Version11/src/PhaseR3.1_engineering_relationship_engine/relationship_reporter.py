"""
relationship_reporter.py — Generate EngineeringRelationshipReport.md.
MODEL_VERSION: 8.1.0
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


class RelationshipReporter:

    def generate_markdown(
        self,
        stats:      Dict[str, Any],
        validation: Dict[str, Any],
        phase_meta: Dict[str, Any],
    ) -> str:
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"

        lines = [
            "# Phase R.3.1 — Engineering Drawing Relationship Engine",
            f"**MODEL_VERSION:** {phase_meta.get('model_version', '8.1.0')}",
            f"**Generated:** {ts}",
            "",
            "---",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Annotations processed | {stats.get('total_annotations', 0)} |",
            f"| Leaders discovered | {stats.get('total_leaders', 0)} |",
            f"| Arrows detected | {stats.get('total_arrows', 0)} |",
            f"| Physical bars found | {stats.get('total_physical_bars', 0)} |",
            f"| Support crossings | {stats.get('total_crossings', 0)} |",
            f"| Validation | {validation.get('summary', 'N/A')} |",
            f"| Intent status | UNKNOWN (geometry-only) |",
            "",
            "---",
            "",
            "## DXF Relationship Chain",
            "",
            "```",
            "MTEXT annotation (insert point)",
            "    ↕ ~63mm",
            "LEADER tail (last vertex) — shoulder",
            "    ↓ (path length computed)",
            "LEADER tip (first vertex) — arrowhead",
            "    ↓ (distance ≈ 0 to physical bar)",
            "Physical bar LINE on -STR-REINF layer",
            "    ↓ (normalized start/end vs beam axis)",
            "Support crossing analysis",
            "    ↓",
            "Extent evidence label (FULL_SPAN / LEFT_SUPPORT_ONLY / etc.)",
            "```",
            "",
            "---",
            "",
            "## Leader Discovery Statistics",
            "",
        ]

        ldr = stats.get("leader_statistics", {})
        lines += [
            f"| Property | Value |",
            f"|----------|-------|",
            f"| Total leaders | {stats.get('total_leaders', 0)} |",
            f"| Min length | {ldr.get('min_length_mm', 0):.0f} mm |",
            f"| Max length | {ldr.get('max_length_mm', 0):.0f} mm |",
            f"| Mean length | {ldr.get('mean_length_mm', 0):.0f} mm |",
            "",
            "**Direction distribution:**",
            "",
        ]
        for d, cnt in ldr.get("direction_distribution", {}).items():
            lines.append(f"- {d}: {cnt}")
        lines.append("")

        # Arrow stats
        arr = stats.get("arrow_statistics", {})
        lines += [
            "---",
            "",
            "## Arrow Detection Statistics",
            "",
            f"| Total arrows | {arr.get('total', 0)} |",
            f"|--------------|-----|",
            "",
            "**Arrow directions:**",
            "",
        ]
        for d, cnt in arr.get("direction_distribution", {}).items():
            lines.append(f"- {d}: {cnt}")
        lines.append("")

        # Physical bar stats
        bar = stats.get("physical_bar_statistics", {})
        lines += [
            "---",
            "",
            "## Physical Bar Statistics",
            "",
            f"| Property | Value |",
            f"|----------|-------|",
            f"| Total bars | {stats.get('total_physical_bars', 0)} |",
            f"| Min length | {bar.get('min_length_mm', 0):.0f} mm |",
            f"| Max length | {bar.get('max_length_mm', 0):.0f} mm |",
            f"| Mean length | {bar.get('mean_length_mm', 0):.0f} mm |",
            "",
            "**Placement distribution:**",
            "",
        ]
        for pl, cnt in bar.get("placement_distribution", {}).items():
            lines.append(f"- {pl}: {cnt}")
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

        # Support crossings
        sc = stats.get("support_crossing_summary", {})
        lines += [
            "---",
            "",
            "## Support Crossing Summary",
            "",
            f"| Property | Count |",
            f"|----------|-------|",
            f"| Left support reached | {sc.get('left_support_reached', 0)} |",
            f"| Right support reached | {sc.get('right_support_reached', 0)} |",
            f"| Both supports reached | {sc.get('both_supports_reached', 0)} |",
            "",
        ]

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
        RULE_DESC = {
            "RULE_1": "Every annotation has relationship",
            "RULE_2": "Every leader linked",
            "RULE_3": "Every arrow resolved",
            "RULE_4": "Valid beam IDs",
            "RULE_5": "Every relationship has extent",
            "RULE_6": "Support crossings valid",
            "RULE_7": "No duplicate relationships",
            "RULE_8": "No hardcoded beam names",
            "RULE_9": "Intent unchanged",
            "RULE_10": "No estimator modifications",
            "RULE_11": "Production workbook",
            "RULE_12": "Relationship graph exported",
        }
        for rid, res in validation.get("rules", {}).items():
            icon   = "PASS" if res["passed"] else "FAIL"
            desc   = RULE_DESC.get(rid, "")
            detail = res.get("detail", "")
            lines.append(f"| {rid} — {desc} | {icon} | {detail} |")
        lines.append("")

        lines += [
            "---",
            "",
            "## Design Principles",
            "",
            "- Intent remains **UNKNOWN** throughout R.3.1",
            "- Leader discovery: all LEADER entities from `-S-ARROW` layer",
            "- Physical bars: horizontal LINE/LWPOLYLINE from `-STR-REINF` layer",
            "- Leader→annotation: tail within 300mm of MTEXT insert point",
            "- Leader→bar: tip within 50mm of physical bar line (distance=0 for exact matches)",
            "- No beam-specific hardcoding; all spatial assignments are dynamic",
            "- No engineering equations, BBS, or Excel modified",
            "",
            "---",
            "",
            f"*R.3.1 Engineering Drawing Relationship Engine | MODEL_VERSION: {phase_meta.get('model_version', '8.1.0')}*",
        ]

        return "\n".join(lines)
