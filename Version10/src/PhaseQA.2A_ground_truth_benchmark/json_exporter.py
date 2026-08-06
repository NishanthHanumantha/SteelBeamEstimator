"""
json_exporter.py — QA.2A JSON artefacts.
MODEL_VERSION: 8.9.1
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

MODEL_VERSION = "9.1.0"


def _w(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def export_drawing_set(out_dir: Path, result: Dict[str, Any]) -> Path:
    name = result.get("drawing_set") or "unknown"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    root = out_dir / safe
    root.mkdir(parents=True, exist_ok=True)
    metrics = result.get("metrics") or {}

    _w(root / "model_generation_summary.json", result.get("pipeline") or {})
    _w(root / "beam_matching.json", result.get("beam_matching") or {})
    _w(root / "bar_matching.json", {
        "summary": {k: v for k, v in (result.get("bar_matching") or {}).items() if k != "rows"},
        "rows": (result.get("bar_matching") or {}).get("rows") or [],
    })
    _w(root / "diameter_comparison.json", {
        "quantity": metrics.get("metric6_diameter_accuracy"),
        "steel": metrics.get("metric7_diameter_steel"),
    })
    _w(root / "steel_comparison.json", metrics.get("metric8_overall_steel") or {})
    _w(root / "error_classification.json", result.get("errors") or {})
    _w(root / "acceptable_extra.json", {
        "count": (result.get("bar_matching") or {}).get("acceptable_extra_bars") or 0,
        "rows": (result.get("bar_matching") or {}).get("acceptable_extra_detail") or [],
        "from_errors": (result.get("errors") or {}).get("acceptable_extra") or [],
    })
    _w(root / "role_status_matrix.json",
       (result.get("bar_matching") or {}).get("role_status_matrix") or {})
    _w(root / "drawing_summary.json", result.get("drawing_summary") or {})
    return root


def export_compiled(out_dir: Path, compiled: Dict[str, Any], elapsed_s: float) -> None:
    _w(out_dir / "compiled_benchmark.json", compiled.get("benchmark") or {})
    _w(out_dir / "compiled_statistics.json", compiled.get("statistics") or {})
    _w(out_dir / "compiled_errors.json", compiled.get("errors") or {})
    _w(out_dir / "compiled_accuracy_dashboard.json", compiled.get("dashboard") or {})

    bench = compiled.get("benchmark") or {}
    errs = compiled.get("errors") or {}
    lines = [
        "# Phase QA.2A — Ground Truth Benchmark Comparison Engine",
        "",
        f"**MODEL_VERSION:** {MODEL_VERSION}",
        f"**Validation:** {bench.get('validation_status')}",
        f"**Elapsed:** {elapsed_s:.1f} s",
        f"**Avg pipeline runtime:** {bench.get('average_pipeline_runtime_s')} s",
        "",
        "## Overall Accuracy",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Drawing Sets | {bench.get('total_drawing_sets')} |",
        f"| Production Runs | {bench.get('production_runs_completed')} |",
        f"| Model Workbooks | {bench.get('model_workbooks_generated')} |",
        f"| Beam Detection % | {bench.get('beam_detection_pct')} |",
        f"| Bar Detection % | {bench.get('bar_detection_pct')} |",
        f"| Bar Accuracy % | {bench.get('bar_accuracy_pct')} |",
        f"| Steel Accuracy % | {bench.get('steel_accuracy_pct')} |",
        f"| Overall Accuracy % | {bench.get('overall_accuracy_pct')} |",
        "",
        "## Top Error Categories",
        "",
    ]
    for k, v in (errs.get("frequency") or {}).items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Recommendation", "", str(bench.get("recommendation") or ""), ""])
    (out_dir / "phase_qa2a_summary.md").write_text("\n".join(lines), encoding="utf-8")
