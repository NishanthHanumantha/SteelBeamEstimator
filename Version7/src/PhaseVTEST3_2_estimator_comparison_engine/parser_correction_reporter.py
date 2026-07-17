"""
parser_correction_reporter.py — V.TEST.3.2.1 markdown report.
MODEL_VERSION: 8.1.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from comparison_models import ComparisonResult


class ParserCorrectionReporter:

    def generate(
        self,
        result: ComparisonResult,
        summary_validation: Dict[str, Any],
        parser_validation: Dict[str, Any],
        corrections: Dict[str, Any],
        previous_steel_kg: float = 32092.30,
    ) -> str:
        am = result.accuracy_metrics
        est = result.estimator_summary
        mod = result.model_summary
        lines: List[str] = []

        lines += [
            "# Phase V.TEST.3.2.1 — Estimator Workbook Parser Correction Report",
            "",
            f"**MODEL_VERSION:** {result.model_version}  ",
            f"**Phase:** {result.phase_id}  ",
            f"**Timestamp:** {result.timestamp}  ",
            "",
            "---",
            "",
            "## 1. Parser Corrections Applied",
            "",
        ]
        for c in corrections.get("corrections_applied", []):
            lines.append(f"- {c}")

        lines += [
            "",
            "### Previous vs Corrected Project Steel Parser",
            "",
            f"| | Previous (V.TEST.3.2) | Corrected (V.TEST.3.2.1) |",
            f"|--|----------------------|--------------------------|",
            f"| Estimator total | {previous_steel_kg:,.2f} kg (incorrect — C24×1000) | "
            f"{est.total_steel_kg:,.2f} kg ({est.total_steel_source}) |",
            f"| Parser source | Detail C24 × 1000 | Pink table kg column (row {est.source_row}) |",
            "",
            "---",
            "",
            "## 2. Correct Project Steel",
            "",
            f"| Metric | Estimator | Model | Δ | Accuracy |",
            f"|--------|-----------|-------|---|----------|",
        ]
        ts = result.summary_comparison.get("total_steel", {})
        lines.append(
            f"| Total Steel (kg) | {ts.get('estimator', 0):,.2f} | {ts.get('model', 0):,.2f} | "
            f"{ts.get('absolute_difference', 0):,.2f} | {ts.get('accuracy_pct', 0):.2f}% |"
        )
        lines += [
            "",
            f"- Estimator TOTAL-MT: **{est.total_steel_mt:.4f} MT**",
            f"- Estimator kg column: **{summary_validation.get('kg_column', est.total_steel_kg):,.2f} kg**",
            f"- Canonical source: **{est.total_steel_source}**",
            "",
        ]
        if est.parser_warnings:
            lines.append("**Parser warnings:**")
            for w in est.parser_warnings:
                lines.append(f"- {w}")
            lines.append("")

        lines += [
            "---",
            "",
            "## 3. Corrected Diameter Comparison",
            "",
            "| Rank | Dia | Estimator (kg) | Model (kg) | Δ (kg) | Accuracy |",
            "|------|-----|----------------|------------|--------|----------|",
        ]
        for d in result.diameter_comparison:
            lines.append(
                f"| {d['rank']} | {d['diameter_mm']}mm | {d['estimator_kg']:,.2f} | "
                f"{d['model_kg']:,.2f} | {d['absolute_difference_kg']:,.2f} | {d['accuracy_pct']:.2f}% |"
            )

        lines += [
            "",
            "---",
            "",
            "## 4. Corrected Similarity Score",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Overall Estimator Similarity | **{am.get('overall_estimator_similarity_score', 0)}/100** |",
            f"| Overall Steel Accuracy | {am.get('overall_steel_accuracy_pct', 0):.2f}% |",
            f"| Diameter Accuracy | {am.get('diameter_accuracy_pct', 0):.2f}% |",
            f"| Beam Coverage | {am.get('beam_coverage_pct', 0):.2f}% |",
            f"| Role Accuracy | {am.get('engineering_role_accuracy_pct', 0):.2f}% |",
            "",
            f"*{am.get('scope_note', '')}*",
            "",
            "### Informational Only (excluded from metrics)",
            "",
        ]
        for info in result.summary_comparison.get("informational_only", []):
            lines.append(
                f"- **{info['metric']}**: Estimator {info['estimator']:,.2f} {info['unit']} — "
                f"not compared for accuracy"
            )

        lines += [
            "",
            "---",
            "",
            "## 5. Validation Results",
            "",
            f"**{parser_validation.get('passed', 0)}/{parser_validation.get('total', 0)} rules passed**",
            "",
            "| Rule | Pass | Detail |",
            "|------|------|--------|",
        ]
        for r in parser_validation.get("rules", []):
            lines.append(
                f"| {r['rule_id']}: {r['rule']} | {'✓' if r['passed'] else '✗'} | {r.get('detail', '')} |"
            )

        lines += [
            "",
            "---",
            "",
            "## 6. Remaining Engineering Differences",
            "",
            "Parser correction resolves the **2× steel total** error. "
            "Remaining gaps are genuine reinforcement discovery differences:",
            "",
            f"- Model steel **{mod.total_steel_kg:,.2f} kg** vs corrected estimator **{est.total_steel_kg:,.2f} kg** "
            f"({ts.get('accuracy_pct', 0):.1f}% accuracy)",
            f"- **{len(result.beam_coverage.get('model_incomplete_reinforcement_beams', []))}** beams "
            "with estimator steel but zero model steel",
            f"- Top difference beam: **{result.top_20_differences[0]['beam_id']}** "
            f"(Δ {result.top_20_differences[0]['difference_kg']:,.2f} kg)"
            if result.top_20_differences else "",
            "",
            "---",
            "",
            "*READ-ONLY parser correction — no production or estimation model code modified.*",
        ]
        return "\n".join(lines)
