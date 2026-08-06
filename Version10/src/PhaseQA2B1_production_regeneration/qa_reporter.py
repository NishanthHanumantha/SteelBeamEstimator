"""
QA.2B.1 — QAReporter + ExecutionSummary + BenchmarkSummary
MODEL_VERSION: 9.6.1
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "9.6.1"
PHASE_ID = "QA.2B.1"


class QAReporter:
    def __init__(self, output_root: Path):
        self.output_root = Path(output_root)

    def write_production_qa(
        self,
        regeneration: Dict[str, Any],
        benchmark: Dict[str, Any],
        validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        bench_by_name = {
            r.get("drawing_set"): r for r in (benchmark.get("results") or [])
        }
        cmp_by_key = {
            c.get("set_key"): c
            for c in (validation.get("comparison") or {}).get("by_set") or []
        }
        for item in regeneration.get("sets") or []:
            key = item.get("set_key")
            br = bench_by_name.get(item.get("drawing_set")) or {}
            ms = br.get("model_summary") or {}
            cmp = cmp_by_key.get(key) or {}
            rows.append(
                {
                    "drawing_set": item.get("drawing_set"),
                    "set_key": key,
                    "production_output_generated": bool(
                        (item.get("workbook") or {}).get("exists")
                    ),
                    "workbook_regenerated": bool(cmp.get("workbook_regenerated")),
                    "benchmark_executed": bool(br.get("compared")),
                    "comparison_completed": bool(cmp.get("new_workbook_hash")),
                    "execution_success": bool(item.get("success"))
                    and bool(br.get("compared")),
                    "elapsed_time_s": item.get("pipeline_elapsed_s"),
                    "benchmark_elapsed_s": next(
                        (
                            t.get("benchmark_elapsed_s")
                            for t in (benchmark.get("per_set_timing") or [])
                            if t.get("drawing_set") == item.get("drawing_set")
                        ),
                        None,
                    ),
                    "beam_count": ms.get("beams"),
                    "bar_count": ms.get("bars"),
                    "steel_quantity": ms.get("kg"),
                    "reuse_detected": bool(cmp.get("reuse_detected")),
                }
            )

        doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "execution_success": bool(validation.get("overall_pass")),
            "sets": rows,
        }
        path = self.output_root / "ProductionRegenerationQA.json"
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return doc

    def write_execution_summary(
        self,
        regeneration: Dict[str, Any],
        benchmark: Dict[str, Any],
        validation: Dict[str, Any],
        qa: Dict[str, Any],
        *,
        overall_elapsed_s: float,
    ) -> Path:
        lines = [
            "# QA.2B.1 — Production Regeneration Summary",
            "",
            f"**MODEL_VERSION:** {MODEL_VERSION}",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"**Overall PASS:** {validation.get('overall_pass')}",
            f"**Overall elapsed:** {overall_elapsed_s}s",
            "",
            "## Purpose",
            "",
            "Fresh production workbooks from DXF using the integrated 9.6.0 pipeline, "
            "then QA.2A ground-truth benchmark on those workbooks only.",
            "",
            "## Per drawing set",
            "",
        ]
        timing = {
            t.get("drawing_set"): t for t in (benchmark.get("per_set_timing") or [])
        }
        for item in regeneration.get("sets") or []:
            t = timing.get(item.get("drawing_set")) or {}
            pipe_s = item.get("pipeline_elapsed_s")
            bench_s = t.get("benchmark_elapsed_s")
            lines.extend(
                [
                    f"### {item.get('drawing_set')} (`{item.get('set_key')}`)",
                    "",
                    f"- Pipeline execution time: **{pipe_s}s**",
                    f"- Workbook generation: included in pipeline (VB1)",
                    f"- Benchmark time: **{bench_s}s**",
                    f"- Workbook: `{((item.get('workbook') or {}).get('path'))}`",
                    f"- Pipeline success: `{item.get('success')}`",
                    "",
                ]
            )
        lines.extend(
            [
                "## Validation",
                "",
            ]
        )
        for name, ok in (validation.get("validation") or {}).get("checks", {}).items():
            lines.append(f"- [{'x' if ok else ' '}] {name}")
        lines.append("")
        path = self.output_root / "ProductionRegenerationSummary.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def write_benchmark_summary(self, benchmark: Dict[str, Any]) -> Path:
        compiled = benchmark.get("compiled") or {}
        bench = compiled.get("benchmark") or compiled
        stats = compiled.get("statistics") or {}
        lines = [
            "# Benchmark Summary — Version 9.6.1",
            "",
            f"**Phase:** {PHASE_ID}",
            f"**MODEL_VERSION:** {MODEL_VERSION}",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            "",
            "Ground-truth benchmark against **freshly regenerated** "
            "`Estimation_Output.xlsx` workbooks (no reuse).",
            "",
            "## Aggregate",
            "",
            f"- Recommendation: `{bench.get('recommendation')}`",
            f"- Compared drawing sets: **{benchmark.get('compared_count')}**",
            f"- Benchmark elapsed: **{benchmark.get('elapsed_s')}s**",
            "",
            "## Per drawing set",
            "",
        ]
        for r in benchmark.get("results") or []:
            if not r.get("compared"):
                lines.append(f"### {r.get('drawing_set')} — NOT COMPARED")
                lines.append("")
                continue
            ds = r.get("drawing_summary") or {}
            m = r.get("metrics") or {}
            steel = m.get("metric8_overall_steel") or {}
            bar = r.get("bar_matching") or {}
            beam = r.get("beam_matching") or {}
            lines.extend(
                [
                    f"### {r.get('drawing_set')}",
                    "",
                    f"- Model Excel: `{ds.get('model_excel')}`",
                    f"- Beam detection: **{beam.get('detection_pct')}%**",
                    f"- Bar detection: **{bar.get('detection_pct')}%**",
                    f"- Bar matching accuracy: **{bar.get('accuracy_pct')}%**",
                    f"- Steel accuracy: **{steel.get('accuracy_pct')}%**",
                    f"- Estimator kg / Model kg: "
                    f"**{steel.get('estimator_total_kg')}** / "
                    f"**{steel.get('model_total_kg')}**",
                    f"- Missing bars: **{bar.get('missing_bars')}**",
                    f"- False positives / extra: **{bar.get('extra_bars', bar.get('false_positives'))}**",
                    "",
                ]
            )
        if stats:
            lines.extend(["## Statistics", "", "```json", json.dumps(stats, indent=2)[:4000], "```", ""])

        path = self.output_root / "BenchmarkSummary.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Also refresh QA.2A summary mirror name expected by deliverables
        qa2a = self.output_root.parent / "QA2A_GroundTruthBenchmark"
        if qa2a.exists():
            (qa2a / "BenchmarkSummary.md").write_text(
                path.read_text(encoding="utf-8"), encoding="utf-8"
            )
        return path
