"""Forensic audit reporter."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List


class AnnotationReporter:

    MODEL_VERSION = "7.8.2"

    def build_markdown(
        self, stats: Dict, validation: Dict, losses: Dict, y10_dxf: List
    ) -> str:
        y10 = stats.get("y10", {})
        lines = [
            "# Phase R.1.5.1 — Annotation Trace Forensic Report",
            "",
            f"**MODEL_VERSION:** {self.MODEL_VERSION}",
            f"**Status:** {'PASS' if validation.get('all_passed') else 'FAIL'}",
            "",
            "## Annotation Inventory",
            "",
            f"- Total annotations: {stats.get('total_annotations', 0)}",
            f"- R.1 discovered: {stats.get('discovered_annotations', 0)}",
            f"- DXF forensic only: {stats.get('dxf_forensic_only', 0)}",
            "",
            "## Pipeline Reach",
            "",
            f"1. Groups: {stats.get('grouped', 0)}",
            f"2. Engineering bars: {stats.get('engineering_bars', 0)}",
            f"3. Steel: {stats.get('steel', 0)}",
            f"4. BBS: {stats.get('bbs', 0)}",
            f"5. Diameter: {stats.get('diameter', 0)}",
            f"6. Excel: {stats.get('excel', 0)}",
            "",
            "## Y10 Forensic Audit",
            "",
            f"- Y10 entities in DXF: {y10.get('dxf_entities', 0)}",
            f"- Y10 in pipeline: {y10.get('pipeline_annotations', 0)}",
            f"- Y10 consumed: {y10.get('consumed', 0)}",
            f"- Y10 lost: {y10.get('lost', 0)}",
            f"- Y10 in Diameter Summary: {y10.get('steel_in_diameter_summary')}",
            "",
            "### Why zero Y10 steel?",
            "",
        ]
        if y10_dxf:
            for item in y10_dxf:
                lines.append(
                    f"- DXF raw: `{item.get('raw_text', '')[:80]}`"
                )
                lines.append(
                    f"  - R.1 clean text: `{item.get('r1_clean_text', '')}`"
                )
                lines.append(
                    f"  - First loss: `{item.get('first_loss_module')}`"
                )
                lines.append(
                    f"  - Root cause: **{item.get('root_cause')}**"
                )
                lines.append(
                    f"  - Nearest beam: {item.get('nearest_beam_id')}"
                )
        else:
            lines.append("- No Y10 entities found in DXF forensic scan")

        lines.extend([
            "",
            "## Stirrup Audit",
            f"- Total: {stats.get('stirrup', {}).get('total', 0)}",
            f"- Consumed: {stats.get('stirrup', {}).get('consumed', 0)}",
            "",
            "## Spacer Audit",
            f"- Total: {stats.get('spacer', {}).get('total', 0)}",
            f"- Consumed: {stats.get('spacer', {}).get('consumed', 0)}",
            "",
            "## Root Causes",
            "",
        ])
        for cause, count in losses.get("root_cause_counts", {}).items():
            if cause:
                lines.append(f"- {cause}: {count}")

        lines.extend(["", "## Validation Rules", ""])
        for rid, rule in sorted(validation.get("rules", {}).items()):
            lines.append(f"- **{rid}**: {rule['status']} — {rule['detail']}")

        lines.extend([
            "",
            "## Recommended Engineering Fix",
            "",
            "Y10 annotation `{\\LS.F.R.- 2-Y10(O.E.F)}` is stripped to empty text by "
            "`annotation_discovery._strip_mtext` because the MTEXT formatting block "
            "`{...}` is removed entirely. Fix in Phase R.2: preserve inner text "
            "before brace stripping, or apply stirrup regex to raw text prior to "
            "format-code removal. No fix applied in this read-only audit.",
            "",
        ])
        return "\n".join(lines)
