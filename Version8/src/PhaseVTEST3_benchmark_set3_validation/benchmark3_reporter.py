"""
benchmark3_reporter.py — Generate benchmark_set3_validation_report.md.
MODEL_VERSION: 8.1.1
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from benchmark3_models import FullBenchmark3Result, ReadinessScore


class Benchmark3Reporter:

    def generate_markdown(self, result: FullBenchmark3Result) -> str:
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        lines = [
            "# Phase V.TEST.3 — Benchmark Set 3 Generalization Validation",
            f"**MODEL_VERSION:** {result.model_version}",
            f"**BENCHMARK_ID:** {result.benchmark_id}",
            f"**Generated:** {ts}",
            "",
            "---",
            "",
            "## 1. Pipeline Execution Summary",
            "",
        ]

        pipe = result.pipeline
        if pipe:
            lines += [
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Stages executed | {pipe.stages_executed} |",
                f"| Stages passed | {pipe.stages_passed} |",
                f"| Stages failed | {pipe.stages_failed} |",
                f"| Success rate | {pipe.success_rate_pct}% |",
                f"| Total elapsed | {pipe.total_elapsed_seconds:.1f}s |",
                "",
                "**Stage Results:**",
                "",
                "| Stage | Status | Elapsed |",
                "|-------|--------|---------|",
            ]
            for s in pipe.stages:
                status = "PASS" if s.success else "FAIL"
                lines.append(f"| {s.stage_id} — {s.stage_name[:40]} | {status} | {s.elapsed_seconds:.1f}s |")
            lines.append("")

        lines += ["---", "", "## 2. Beam Discovery Summary", ""]
        b = result.beam_summary
        lines += [
            f"| Property | Value |",
            f"|----------|-------|",
            f"| Total beams | {b.get('total_beams', 0)} |",
            f"| Geometry coverage | {b.get('geometry_coverage_pct', 0)}% |",
            f"| Duplicate beams | {len(b.get('duplicate_beams', []))} |",
            f"| Sample IDs | {', '.join(b.get('beam_naming_sample', [])[:8])} |",
            "",
        ]

        lines += ["---", "", "## 3. Engineering Context Summary", ""]
        gn = result.general_notes_summary
        lines += [
            f"| Parameter | Value |",
            f"|-----------|-------|",
            f"| Steel grades | {gn.get('steel_grades', [])} |",
            f"| Concrete grades | {gn.get('concrete_grades', [])} |",
            f"| DL table entries | {gn.get('development_length_table', 0)} |",
            f"| Cover rules | {gn.get('cover_rules', 0)} |",
            f"| Hook rules | {gn.get('hook_rules', 0)} |",
            f"| Lap rules | {gn.get('lap_rules', 0)} |",
            f"| Spacer rules | {gn.get('spacer_rules', 0)} |",
            f"| Parse confidence | {gn.get('parse_confidence', 0):.1%} |",
            "",
        ]

        lines += ["---", "", "## 4. Reinforcement Discovery Summary", ""]
        r = result.reinforcement_summary
        lines += [
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| TEXT entities | {r.get('text_entities', 0)} |",
            f"| MTEXT entities | {r.get('mtext_entities', 0)} |",
            f"| Recovered MTEXT | {r.get('recovered_mtext', 0)} |",
            f"| Reinforcement annotations | {r.get('reinforcement_annotations', 0)} |",
            f"| Y10 detections | {r.get('y10_detected', 0)} |",
            f"| Stirrup detections | {r.get('stirrup_detected', 0)} |",
            f"| Spacer detections | {r.get('spacer_detected', 0)} |",
            "",
        ]

        lines += ["---", "", "## 5. Engineering Interpretation Summary", ""]
        i = result.interpretation_summary
        lines += [
            f"| Stage | Count | Coverage |",
            f"|-------|-------|----------|",
            f"| Semantic Objects | {i.get('semantic_objects', 0)} | {i.get('semantic_coverage_pct', 0)}% |",
            f"| Engineering Facts | {i.get('engineering_facts', 0)} | {i.get('facts_coverage_pct', 0)}% |",
            f"| Intent Hypotheses | {i.get('intent_hypotheses', 0)} | — |",
            f"| Geometry Contexts | {i.get('geometry_contexts', 0)} | {i.get('geometry_coverage_pct', 0)}% |",
            f"| Drawing Relationships | {i.get('drawing_relationships', 0)} | {i.get('relationship_coverage_pct', 0)}% |",
            f"| Intent still UNKNOWN | {i.get('intent_still_unknown', True)} | — |",
            "",
        ]

        lines += ["---", "", "## 6. Production Output Summary", ""]
        p = result.production_summary
        lines += [
            f"| Output | Status |",
            f"|--------|--------|",
            f"| Workbook generated | {p.get('workbook_generated', False)} |",
            f"| Steel quantity (kg) | {p.get('steel_quantity_kg', 0):.2f} |",
            f"| Diameter summary | {p.get('diameter_summary_generated', False)} |",
            f"| Beam summary | {p.get('beam_summary_generated', False)} |",
            f"| BBS generated | {p.get('bbs_generated', False)} |",
            f"| BBS rows | {p.get('bbs_rows', 0)} |",
            "",
        ]

        lines += ["---", "", "## 7. Estimator Readiness Score", ""]
        lines += [
            f"**Overall Score: {result.overall_readiness_score}/100**",
            f"**Classification: {result.readiness_classification}**",
            "",
            "| Dimension | Score | Detail |",
            "|-----------|-------|--------|",
        ]
        for s in result.readiness_scores:
            lines.append(f"| {s.dimension} | {s.score}/100 | {s.detail} |")
        lines.append("")

        lines += ["---", "", "## 8. Generalization Assessment", ""]
        audit = result.generalization_audit
        lines.append(f"**{audit.get('summary', 'N/A')}**")
        lines.append("")
        for check, passed in (audit.get("checks") or {}).items():
            icon = "PASS" if passed else "FAIL"
            lines.append(f"- [{icon}] {check}")
        if audit.get("findings"):
            lines += ["", "**Findings:**", ""]
            for f in audit["findings"][:15]:
                lines.append(f"- [{f.get('severity')}] {f.get('category')}: {f.get('detail')} ({f.get('module')})")
        lines.append("")

        lines += ["---", "", "## 9. Remaining Engineering Gaps", ""]
        gaps = self._identify_gaps(result)
        for g in gaps:
            lines.append(f"- {g}")
        lines.append("")

        lines += [
            "---",
            "",
            "## 10. Recommended Next Phase",
            "",
            f"**{result.recommended_next_phase}**",
            "",
            "Proceed with Phase R.4 only if generalization audit passes and "
            "readiness classification is ENGINEERING READY or above.",
            "",
            "---",
            "",
            "## Validation Rules",
            "",
            "| Rule | Status | Detail |",
            "|------|--------|--------|",
        ]
        for rid, res in sorted(result.validation_rules.items()):
            if isinstance(res, dict):
                icon = "PASS" if res.get("passed") else "FAIL"
                lines.append(f"| {rid} | {icon} | {res.get('detail', '')} |")
            else:
                icon = "PASS" if res else "FAIL"
                lines.append(f"| {rid} | {icon} | |")

        if result.warnings:
            lines += ["", "---", "", "## Warnings", ""]
            for w in result.warnings:
                lines.append(f"- {w}")

        lines += [
            "",
            "---",
            "",
            f"*Phase V.TEST.3 | MODEL_VERSION {result.model_version} | READ-ONLY VALIDATION*",
        ]
        return "\n".join(lines)

    def _identify_gaps(self, result: FullBenchmark3Result) -> List[str]:
        gaps: List[str] = []
        if result.pipeline and result.pipeline.stages_failed > 0:
            failed = [s.stage_id for s in result.pipeline.stages if not s.success]
            gaps.append(f"Pipeline stages failed: {', '.join(failed)}")
        if result.interpretation_summary.get("relationship_coverage_pct", 0) < 90:
            gaps.append("Drawing relationship coverage below 90% — leader-bar chain may need tuning for TF drawings")
        if result.engineering_bar_summary.get("empty_beams", 0) > 0:
            gaps.append(f"{result.engineering_bar_summary['empty_beams']} beams without engineering bars")
        if not result.generalization_audit.get("all_checks_passed"):
            gaps.append("Benchmark-specific dependencies detected — resolve before R.4")
        if result.overall_readiness_score < 60:
            gaps.append("Overall readiness below ENGINEERING READY threshold")
        if not gaps:
            gaps.append("No critical engineering gaps — pipeline generalizes to Benchmark Set 3")
        return gaps

    def build_json_report(self, result: FullBenchmark3Result) -> Dict[str, Any]:
        return {
            "model_version": result.model_version,
            "benchmark_id": result.benchmark_id,
            "timestamp": result.timestamp,
            "overall_passed": result.overall_passed,
            "overall_readiness_score": result.overall_readiness_score,
            "readiness_classification": result.readiness_classification,
            "recommended_next_phase": result.recommended_next_phase,
            "discovery": result.discovery_summary,
            "beams": result.beam_summary,
            "general_notes": result.general_notes_summary,
            "reinforcement": result.reinforcement_summary,
            "interpretation": result.interpretation_summary,
            "engineering_bars": result.engineering_bar_summary,
            "production": result.production_summary,
            "generalization_audit": result.generalization_audit,
            "validation": result.validation_rules,
            "warnings": result.warnings,
        }
