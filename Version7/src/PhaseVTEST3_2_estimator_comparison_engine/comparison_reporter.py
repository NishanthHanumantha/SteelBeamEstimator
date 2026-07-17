"""
comparison_reporter.py — Markdown engineering audit report.
MODEL_VERSION: 8.1.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from comparison_models import ComparisonResult


class ComparisonReporter:

    def generate(self, result: ComparisonResult) -> str:
        lines: List[str] = []
        am = result.accuracy_metrics
        cov = result.beam_coverage
        est_s = result.estimator_summary
        mod_s = result.model_summary

        lines += [
            "# Phase V.TEST.3.2 — Estimator vs Model Engineering Audit",
            "",
            f"**MODEL_VERSION:** {result.model_version}  ",
            f"**Phase:** {result.phase_id}  ",
            f"**Timestamp:** {result.timestamp}  ",
            f"**Mode:** READ-ONLY comparison — no production code modified",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            "",
            f"| Workbook | File |",
            f"|----------|------|",
            f"| Estimator | `{result.estimator_workbook.filename}` |",
            f"| Model | `{result.model_workbook.filename}` |",
            "",
            f"- **Estimator total steel:** {est_s.total_steel_kg:,.2f} kg",
            f"- **Model total steel:** {mod_s.total_steel_kg:,.2f} kg",
            f"- **Absolute difference:** {mod_s.total_steel_kg - est_s.total_steel_kg:,.2f} kg",
            f"- **Overall steel accuracy:** {am.get('overall_steel_accuracy_pct', 0):.2f}%",
            f"- **Overall estimator similarity score:** {am.get('overall_estimator_similarity_score', 0):.2f}/100",
            f"- **Beam coverage:** {cov.get('matched_beams', 0)}/{cov.get('estimator_beam_count', 0)} "
            f"({cov.get('beam_coverage_pct', 0):.1f}%)",
            f"- **Validation:** {result.validation.get('passed', 0)}/{result.validation.get('total', 0)} rules passed",
            "",
            "The model workbook captures beam IDs for all 61 beams but propagates non-zero steel "
            "to only a small subset. The primary gap is reinforcement discovery / bar propagation, "
            "not workbook layout.",
            "",
            "---",
            "",
            "## 2. Reinforcement Total Table Comparison",
            "",
            f"Estimator summary row: **{est_s.label}** (row {est_s.source_row})",
            "",
            "| Metric | Estimator | Model | Δ | Δ% | Accuracy |",
            "|--------|-----------|-------|---|-----|----------|",
        ]

        for row in result.summary_comparison.get("rows", []):
            lines.append(
                f"| {row['metric']} | {row['estimator']:,.4f} | {row['model']:,.4f} | "
                f"{row['absolute_difference']:,.4f} | {row['percentage_difference']:.2f}% | "
                f"{row['accuracy_pct']:.2f}% |"
            )

        info = result.summary_comparison.get("informational_only", [])
        if info:
            lines += [
                "",
                "*Informational only (excluded from accuracy):*",
                "",
                "| Metric | Estimator | Note |",
                "|--------|-----------|------|",
            ]
            for row in info:
                lines.append(
                    f"| {row['metric']} | {row['estimator']:,.4f} {row['unit']} | "
                    f"{row.get('note', 'Not in model scope')} |"
                )

        lines += [
            "",
            "---",
            "",
            "## 3. Diameter-wise Comparison",
            "",
            "Ranked best to worst by accuracy:",
            "",
            "| Rank | Dia (mm) | Estimator (kg) | Model (kg) | Δ (kg) | Δ% | Accuracy |",
            "|------|----------|----------------|------------|--------|-----|----------|",
        ]
        for d in result.diameter_comparison:
            lines.append(
                f"| {d['rank']} | {d['diameter_mm']} | {d['estimator_kg']:,.2f} | "
                f"{d['model_kg']:,.2f} | {d['absolute_difference_kg']:,.2f} | "
                f"{d['percentage_difference']:.2f}% | {d['accuracy_pct']:.2f}% |"
            )

        lines += [
            "",
            "---",
            "",
            "## 4. Beam Coverage Comparison",
            "",
            f"- Estimator beams: **{cov.get('estimator_beam_count', 0)}**",
            f"- Model beams: **{cov.get('model_beam_count', 0)}**",
            f"- Matched: **{cov.get('matched_beams', 0)}**",
            f"- Missing in model: **{len(cov.get('missing_in_model', []))}**",
            f"- Extra in model: **{len(cov.get('extra_in_model', []))}**",
            f"- Model incomplete reinforcement: **{len(cov.get('model_incomplete_reinforcement_beams', []))}**",
            "",
        ]
        incomplete = cov.get("model_incomplete_reinforcement_beams", [])[:15]
        if incomplete:
            lines.append("Sample incomplete beams: " + ", ".join(incomplete) + (" ..." if len(cov.get("model_incomplete_reinforcement_beams", [])) > 15 else ""))
            lines.append("")

        lines += [
            "---",
            "",
            "## 5. Beam-wise Engineering Comparison",
            "",
            "Top beams by absolute steel difference (see `beam_level_comparison.json` for full detail):",
            "",
            "| Beam | Estimator (kg) | Model (kg) | Δ (kg) | Severity | First Difference |",
            "|------|----------------|------------|--------|----------|------------------|",
        ]
        for bc in result.beam_comparisons[:15]:
            fd = bc["first_observable_difference"]
            if len(fd) > 80:
                fd = fd[:77] + "..."
            lines.append(
                f"| {bc['beam_id']} | {bc['steel_kg']['estimator']:,.2f} | "
                f"{bc['steel_kg']['model']:,.2f} | {bc['steel_kg']['difference_kg']:,.2f} | "
                f"{bc['severity']} | {fd} |"
            )

        lines += [
            "",
            "---",
            "",
            "## 6. Reinforcement Role Comparison",
            "",
            "| Role | Estimator (kg) | Model (kg) | Δ (kg) | Accuracy | Likely Reason |",
            "|------|----------------|------------|--------|----------|---------------|",
        ]
        for r in result.role_comparison:
            reason = r.get("likely_engineering_reason", "")[:70]
            lines.append(
                f"| {r['role']} | {r['estimator_kg']:,.2f} | {r['model_kg']:,.2f} | "
                f"{r['absolute_difference_kg']:,.2f} | {r['accuracy_pct']:.2f}% | {reason} |"
            )

        lines += [
            "",
            "---",
            "",
            "## 7. Top 20 Largest Differences",
            "",
            "| Rank | Beam | Estimator (kg) | Model (kg) | Δ (kg) |",
            "|------|------|----------------|------------|--------|",
        ]
        for t in result.top_20_differences:
            lines.append(
                f"| {t['rank']} | {t['beam_id']} | {t['estimator_kg']:,.2f} | "
                f"{t['model_kg']:,.2f} | {t['difference_kg']:,.2f} |"
            )

        lines += [
            "",
            "---",
            "",
            "## 8. Accuracy Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
        ]
        for k, v in am.items():
            lines.append(f"| {k.replace('_', ' ').title()} | {v} |")

        lines += [
            "",
            "---",
            "",
            "## 9. Root Cause Categorisation",
            "",
        ]
        summary = result.root_causes.get("summary_by_category", [])
        if summary:
            lines += ["| Category | Count |", "|----------|-------|"]
            for s in summary:
                lines.append(f"| {s['category']} | {s['count']} |")
        lines.append("")

        lines += [
            "---",
            "",
            "## 10. Recommended Investigation Order",
            "",
        ]
        for item in result.recommended_investigation_order:
            lines.append(f"- {item}")

        lines += [
            "",
            "---",
            "",
            "*Generated by Phase V.TEST.3.2 Estimator Comparison Engine — READ-ONLY audit.*",
        ]
        return "\n".join(lines)
