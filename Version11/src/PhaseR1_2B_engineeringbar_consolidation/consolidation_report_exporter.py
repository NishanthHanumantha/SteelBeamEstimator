"""Export all Phase R.1.2B artefacts."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict


class ConsolidationReportExporter:

    OUT_DIR_NAME = "PhaseR1_2B_engineeringbar_consolidation"

    def __init__(self, v7_root: pathlib.Path):
        self._out = v7_root / "data/output" / self.OUT_DIR_NAME
        self._out.mkdir(parents=True, exist_ok=True)

    @property
    def out_dir(self) -> pathlib.Path:
        return self._out

    def export_all(self, result: Dict[str, Any], report_md: str) -> Dict[str, str]:
        written: Dict[str, str] = {}
        payloads = {
            "engineeringbar_audit.json": result.get("audit_before", {}),
            "duplicate_groups.json": {
                "model_version": result.get("model_version"),
                "groups": (result.get("detection") or {}).get("groups", []),
                "duplicate_group_count": (result.get("detection") or {}).get(
                    "duplicate_group_count"
                ),
                "redundant_bar_count": (result.get("detection") or {}).get(
                    "redundant_bar_count"
                ),
            },
            "duplicate_similarity_scores.json": {
                "model_version": result.get("model_version"),
                "threshold": (result.get("detection") or {}).get("threshold"),
                "scores": (result.get("detection") or {}).get(
                    "similarity_scores", []
                ),
            },
            "physical_reinforcement_members.json": {
                "model_version": result.get("model_version"),
                "member_count": len(result.get("physical_members") or []),
                "members": result.get("physical_members") or [],
            },
            "engineeringbar_consolidation.json": result.get("consol_report") or {},
            "consolidation_traceability.json": {
                "model_version": result.get("model_version"),
                "entries": result.get("traceability") or [],
            },
            "diameter_distribution_before.json": result.get("diameter_before") or {},
            "diameter_distribution_after.json": {
                **(result.get("diameter_after") or {}),
                "comparison": result.get("diameter_comparison") or {},
            },
            "bbs_consolidation_validation.json": result.get("bbs_validation") or {},
            "benchmark_regression_consolidation.json": result.get("regression") or {},
        }
        for name, data in payloads.items():
            path = self._out / name
            path.write_text(
                json.dumps(data, indent=2, default=str, ensure_ascii=False),
                encoding="utf-8",
            )
            written[name] = str(path)

        md_path = self._out / "engineeringbar_consolidation_report.md"
        md_path.write_text(report_md, encoding="utf-8")
        written["engineeringbar_consolidation_report.md"] = str(md_path)
        return written

    def generate_report(self, result: Dict[str, Any]) -> str:
        val = result.get("validation") or {}
        det = result.get("detection") or {}
        cr = result.get("consol_report") or {}
        dia = result.get("diameter_comparison") or {}
        bbs = result.get("bbs_validation") or {}
        reg = result.get("regression") or {}
        rec = result.get("recommendation", "B")
        totals = dia.get("totals") or {}

        lines = [
            "# Phase R.1.2B — EngineeringBar Deduplication & Consolidation Engine",
            "",
            "**MODEL_VERSION:** 8.3.1",
            f"**Validation:** {val.get('passed', 0)}/{val.get('total', 8)} rules passed",
            f"**Recommendation:** {rec}",
            "",
            "## 1. Executive Summary",
            "",
            "Duplicate EngineeringBarModels were produced when multiple identical "
            "annotation callouts for the same physical reinforcement were each "
            "expanded into independent bars. R.1.2B consolidates evidence-equivalent "
            "bars into Physical Reinforcement Members while preserving full lineage.",
            "",
            f"- EngineeringBars before: **{cr.get('bars_before')}**",
            f"- EngineeringBars after: **{cr.get('bars_after')}**",
            f"- Duplicate groups merged: **{cr.get('duplicate_groups_merged')}**",
            f"- Redundant bars removed: **{cr.get('bars_removed_as_duplicates')}**",
            f"- Approx. steel weight change: **{totals.get('weight_pct_change')}%**",
            "",
            "## 2. Root Cause Analysis",
            "",
            "`EngineeringBarBuilder._expand_group` creates one EngineeringBar per "
            "label in a discovery group. Repeated callouts (e.g. four `4Y16` "
            "TOP_EXTRA labels) become four bars, inflating diameter totals.",
            "",
            "Annotation discovery is correct; the defect is independent treatment "
            "of equivalent engineering evidence at the EngineeringBarBuilder stage.",
            "",
            "## 3. EngineeringBar Audit Summary",
            "",
            f"- Beams audited: {result.get('audit_before', {}).get('total_beams')}",
            f"- Bars audited: {result.get('audit_before', {}).get('total_engineering_bars')}",
            f"- Role counts: `{result.get('audit_before', {}).get('role_counts')}`",
            "",
            "## 4. Duplicate Detection Statistics",
            "",
            f"- Threshold: {det.get('threshold')}",
            f"- Duplicate groups: {det.get('duplicate_group_count')}",
            f"- Bars in groups: {det.get('bars_in_duplicate_groups')}",
            f"- Redundant bars: {det.get('redundant_bar_count')}",
            f"- Similarity pairs scored: {len(det.get('similarity_scores') or [])}",
            "",
            "## 5. Consolidation Results",
            "",
            f"- Physical members: {len(result.get('physical_members') or [])}",
            f"- Traceability entries: {len(result.get('traceability') or [])}",
            f"- Quantities are **not summed** on merge (canonical qty retained).",
            "",
            "## 6. Physical Reinforcement Summary",
            "",
            "Each Physical Reinforcement Member maps to exactly one EngineeringBarModel "
            "after consolidation (Top/Bottom Main/Extra, Side Face, Spacer, Stirrups).",
            "",
            "## 7. Diameter Distribution Improvement",
            "",
            "| Diameter | Rows Before | Rows After | Qty Before | Qty After | Weight Δ% |",
            "|----------|-------------|------------|------------|-----------|-----------|",
        ]
        for key, row in sorted((dia.get("by_diameter") or {}).items()):
            lines.append(
                f"| {key} | {row.get('rows_before')} | {row.get('rows_after')} | "
                f"{row.get('bar_count_before')} | {row.get('bar_count_after')} | "
                f"{row.get('steel_weight_pct_change')} |"
            )
        lines.extend([
            "",
            f"Total weight: {totals.get('weight_before_kg')} → "
            f"{totals.get('weight_after_kg')} kg "
            f"({totals.get('weight_pct_change')}%).",
            "",
            "## 8. BBS Validation Results",
            "",
            f"- Passed: {bbs.get('passed')}",
            f"- L2 role duplicate counts: `{bbs.get('l2_role_duplicate_counts')}`",
            f"- Issues: {bbs.get('issue_count')}",
            "",
            "## 9. Regression Results",
            "",
            f"- No regression: {reg.get('no_regression')}",
            f"- Summary: {reg.get('summary')}",
            "",
            "## 10. Remaining Engineering Accuracy Gaps",
            "",
            "- Role / diameter misclassification may still deviate from estimator "
            "(addressed in R.1.2C).",
            "- Cut-length / zone extent accuracy remains a geometry/interpretation "
            "concern, not a duplication concern.",
            "- Stirrup zone spacing interpretation may still differ from workbook.",
            "",
            "## 11. Exported Artefacts",
            "",
        ])
        for name in (
            "engineeringbar_audit.json",
            "duplicate_groups.json",
            "duplicate_similarity_scores.json",
            "physical_reinforcement_members.json",
            "engineeringbar_consolidation.json",
            "consolidation_traceability.json",
            "diameter_distribution_before.json",
            "diameter_distribution_after.json",
            "bbs_consolidation_validation.json",
            "benchmark_regression_consolidation.json",
            "engineeringbar_consolidation_report.md",
        ):
            lines.append(f"- `{self.OUT_DIR_NAME}/{name}`")

        lines.extend([
            "",
            "## 12. Recommendation",
            "",
        ])
        if rec == "A":
            lines.append(
                "**Recommendation A** — Ready for Phase R.1.2C — "
                "Reinforcement Role & Diameter Accuracy Engine"
            )
        else:
            lines.append(
                "**Recommendation B** — Additional EngineeringBar consolidation required."
            )
        lines.extend([
            "",
            "---",
            "*Phase R.1.2B | MODEL_VERSION 8.3.1*",
            "",
        ])
        return "\n".join(lines)
