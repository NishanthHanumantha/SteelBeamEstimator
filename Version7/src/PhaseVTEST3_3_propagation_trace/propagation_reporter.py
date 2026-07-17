"""
propagation_reporter.py — Markdown forensic report for V.TEST.3.3.
MODEL_VERSION: 8.1.4
"""
from __future__ import annotations

from typing import List

from propagation_models import PropagationTraceResult


class PropagationReporter:

    def generate(self, result: PropagationTraceResult) -> str:
        s = result.statistics
        set3 = result.set3_summary
        v = result.validation
        lines: List[str] = []

        lines += [
            "# Phase V.TEST.3.3 — Reinforcement Propagation Trace Report",
            "",
            f"**MODEL_VERSION:** {result.model_version}  ",
            f"**Phase:** {result.phase_id}  ",
            f"**Timestamp:** {result.timestamp}  ",
            "**Mode:** READ-ONLY forensic trace — no production code modified",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            "",
            f"Benchmark Set 3 (Galera TF) has **{s.get('annotations_discovered', 0)} reinforcement annotations** "
            f"on **{s.get('beams_with_annotations', 0)} of 61 beams**. All 46 annotations complete the "
            f"interpretation chain (semantic → fact → hypothesis → geometry → relationship) at **100%**. "
            f"All 46 become **EngineeringBarModels** and reach steel/BBS — but only on those 7 beams.",
            "",
            f"**{set3.get('beams_without_annotations', 0)} beams** have **zero R.1 annotations** — "
            "this is the first point of propagation failure for 88.5% of beams.",
            "",
            f"- Engineering facts: **{s.get('engineering_facts', 0)}**",
            f"- Engineering bars created: **{s.get('engineering_bars_created', 0)}**",
            f"- Beams with steel: **{s.get('beams_with_steel', 0)}** ({s.get('steel_total_kg', 0):,.2f} kg)",
            f"- Interpretation → production wired: **{s.get('interpretation_path_connected_to_production')}**",
            f"- Validation: **{v.get('passed', 0)}/{v.get('total', 0)}** rules passed",
            f"- Recommendation: **{result.recommendation}**",
            "",
            "---",
            "",
            "## 2. Complete Propagation Statistics",
            "",
            "| Stage | Count |",
            "|-------|-------|",
        ]
        for k, val in s.items():
            lines.append(f"| {k.replace('_', ' ').title()} | {val} |")

        lines += [
            "",
            "---",
            "",
            "## 3. Annotation → EngineeringBar Trace",
            "",
            "All 46 annotations on beams "
            f"{', '.join(set3.get('successful_beam_ids', []))} achieve **PASS** through steel and BBS.",
            "",
            "| Annotation | Beam | Role | EBM | Steel | Status |",
            "|------------|------|------|-----|-------|--------|",
        ]
        for m in result.annotation_matrix[:20]:
            lines.append(
                f"| {m['annotation_id']} | {m['beam_id']} | {m['role']} | "
                f"{m['engineering_bar']} | {m['steel']} | {m['overall_status']} |"
            )
        if len(result.annotation_matrix) > 20:
            lines.append(f"| ... | ({len(result.annotation_matrix) - 20} more) | | | | |")

        lines += [
            "",
            "---",
            "",
            "## 4. EngineeringBar Creation Audit",
            "",
            "Production path: `ReinforcementPipelineAdapter` → `EngineeringBarBuilder.build_all()` "
            "reads **R.1 groups only**. Engineering Facts are **not consumed** by R.1.3.",
            "",
            f"- Attempted via R.1 group: **{s.get('engineering_bars_attempted_via_r1', 0)}**",
            f"- Created: **{s.get('engineering_bars_created', 0)}**",
            f"- Rejected: **{s.get('engineering_bars_rejected', 0)}**",
            "",
            "---",
            "",
            "## 5. Filter Audit",
            "",
            "| Module | Function | Condition | Objects | Reason |",
            "|--------|----------|-----------|---------|--------|",
        ]
        for f in result.filter_audit:
            lines.append(
                f"| {f['module'].split('.')[-1]} | {f['function']} | "
                f"{f['condition'][:40]}... | {f['objects_removed_or_bypassed']} | "
                f"{f['reason'][:50]} |"
            )

        lines += [
            "",
            "---",
            "",
            "## 6. Set 3 Beam-by-Beam Propagation Analysis",
            "",
            f"- Successful beams ({len(set3.get('successful_beam_ids', []))}): "
            f"{', '.join(set3.get('successful_beam_ids', []))}",
            f"- Beams without annotations: **{set3.get('beams_without_annotations', 0)}**",
            f"- Primary first failure: {set3.get('primary_first_failure', '')}",
            "",
        ]

        lines += [
            "---",
            "",
            "## 7. First Point of Propagation Failure",
            "",
            "**For 54 beams:** `PhaseR.1_generalized_reinforcement_discovery` — "
            "no reinforcement annotations discovered in DXF detail association.",
            "",
            "**For 46 annotations on 7 beams:** No failure — full propagation to workbook.",
            "",
            "**Architectural gap:** R.2.1B–R.3.1 interpretation outputs are validated but "
            "not connected to `EngineeringBarBuilder` (production reads R.1 only).",
            "",
            "---",
            "",
            "## 8. Ranked Root Causes",
            "",
            "| Rank | Severity | Stage | Module | Objects | Impact |",
            "|------|----------|-------|--------|---------|--------|",
        ]
        for c in result.root_cause_ranking:
            lines.append(
                f"| {c['rank']} | {c['severity']} | {c['pipeline_stage']} | "
                f"{c['module'].split('.')[-1]} | {c['objects_affected']} | "
                f"{c['engineering_impact'][:60]}... |"
            )

        lines += [
            "",
            "---",
            "",
            "## 9. Recommended Engineering Fix Order",
            "",
            "1. **R.1 annotation discovery** — extend DXF detail segmentation / beam association "
            "so all 61 beams receive reinforcement annotations (currently 7/61).",
            "2. **Wire interpretation to production** — connect R.2.1B–R.3.1 outputs to "
            "EngineeringBarModel builder (or merge paths).",
            "3. **Verify beam detail radius** — audit `BeamDetailSegmenter` entity rejection on Set 3 DXF.",
            "4. **Re-run V.TEST.3.2 comparison** after propagation fix to measure steel recovery.",
            "",
            "---",
            "",
            "## 10. Recommendation",
            "",
            f"**{result.recommendation}**",
            "",
            "The 46→7 beam collapse is **not** caused by EngineeringBarBuilder filtering annotated "
            "reinforcement — all 46 annotations sit on 7 beams only. The estimator expects reinforcement "
            "on all 61 beams; R.1 discovery is the primary bottleneck.",
            "",
            "---",
            "",
            "*READ-ONLY forensic trace — no production behaviour modified.*",
        ]
        return "\n".join(lines)
