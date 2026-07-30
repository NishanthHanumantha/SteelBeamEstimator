"""
json_exporter.py — Write per-drawing-set and compiled JSON artefacts.
MODEL_VERSION: 8.9.0
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

MODEL_VERSION = "8.9.0"


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def export_drawing_set(out_dir: Path, comparison: Dict[str, Any]) -> Dict[str, Path]:
    """Export all per-drawing-set JSON artefacts. Returns map of name → path."""
    ds_name = comparison.get("drawing_set") or "unknown"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in ds_name)
    root = out_dir / safe
    root.mkdir(parents=True, exist_ok=True)

    paths = {
        "drawing_summary": root / "drawing_summary.json",
        "beam_accuracy": root / "beam_accuracy.json",
        "bar_accuracy": root / "bar_accuracy.json",
        "diameter_accuracy": root / "diameter_accuracy.json",
        "steel_quantity_comparison": root / "steel_quantity_comparison.json",
        "error_summary": root / "error_summary.json",
    }
    _write(paths["drawing_summary"], comparison.get("summary") or {})
    _write(paths["beam_accuracy"], {
        "model_version": MODEL_VERSION,
        "drawing_set": ds_name,
        "beam_detection": comparison.get("beam_detection"),
        "beam_identification": comparison.get("beam_identification"),
        "beam_rows": comparison.get("beam_rows"),
        "beam_level": comparison.get("beam_level") or [],
    })
    _write(paths["bar_accuracy"], {
        "model_version": MODEL_VERSION,
        "drawing_set": ds_name,
        "bar_detection": comparison.get("bar_detection"),
        "bar_accuracy": comparison.get("bar_accuracy"),
        "bar_rows": comparison.get("bar_rows"),
        "missing_bars": comparison.get("missing_bars"),
    })
    _write(paths["diameter_accuracy"], {
        "model_version": MODEL_VERSION,
        "drawing_set": ds_name,
        "diameter_comparison": comparison.get("diameter_comparison"),
        "diameter_steel": comparison.get("diameter_steel"),
    })
    _write(paths["steel_quantity_comparison"], {
        "model_version": MODEL_VERSION,
        "drawing_set": ds_name,
        "steel_quantity": comparison.get("steel_quantity"),
    })
    _write(paths["error_summary"], {
        "model_version": MODEL_VERSION,
        "drawing_set": ds_name,
        "errors": comparison.get("errors"),
    })
    return paths


def export_compiled(out_dir: Path, compiled: Dict[str, Any]) -> Dict[str, Path]:
    paths = {
        "compiled_benchmark": out_dir / "compiled_benchmark.json",
        "compiled_statistics": out_dir / "compiled_statistics.json",
        "compiled_error_summary": out_dir / "compiled_error_summary.json",
        "compiled_accuracy_dashboard": out_dir / "compiled_accuracy_dashboard.json",
    }
    _write(paths["compiled_benchmark"], compiled.get("benchmark") or compiled)
    _write(paths["compiled_statistics"], compiled.get("statistics") or {})
    _write(paths["compiled_error_summary"], compiled.get("errors") or {})
    _write(paths["compiled_accuracy_dashboard"], compiled.get("dashboard") or {})
    return paths


def export_markdown(out_dir: Path, compiled: Dict[str, Any], elapsed_s: float) -> Path:
    path = out_dir / "phase_qa2_summary.md"
    bench = compiled.get("benchmark") or {}
    dash = compiled.get("dashboard") or {}
    errs = compiled.get("errors") or {}
    lines = [
        "# Phase QA.2 — Multi-Drawing Accuracy & Error Benchmark",
        "",
        f"**MODEL_VERSION:** {MODEL_VERSION}",
        f"**Status:** {bench.get('validation_status', 'COMPLETE')}",
        f"**Execution time:** {elapsed_s:.1f} s",
        "",
        "## Compiled Accuracy Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Drawing Sets | {bench.get('total_drawing_sets', 0)} |",
        f"| Total Beams | {bench.get('total_beams', 0)} |",
        f"| Detected Beams | {bench.get('detected_beams', 0)} |",
        f"| Correct Beams | {bench.get('correct_beams', 0)} |",
        f"| Total Bars | {bench.get('total_bars', 0)} |",
        f"| Detected Bars | {bench.get('detected_bars', 0)} |",
        f"| Correct Bars | {bench.get('correct_bars', 0)} |",
        f"| Missing Bars | {bench.get('missing_bars', 0)} |",
        f"| Beam Detection % | {bench.get('beam_detection_pct', 0)} |",
        f"| Bar Detection % | {bench.get('bar_detection_pct', 0)} |",
        f"| Bar Accuracy % | {bench.get('bar_accuracy_pct', 0)} |",
        f"| Steel Accuracy % | {bench.get('steel_accuracy_pct', 0)} |",
        f"| Overall Accuracy % | {bench.get('overall_accuracy_pct', 0)} |",
        "",
        "## Drawing Set Dashboard",
        "",
    ]
    for row in dash.get("drawing_sets") or []:
        lines.append(
            f"- **{row.get('drawing_set')}**: "
            f"beam_det={row.get('beam_detection_pct')}% "
            f"bar_det={row.get('bar_detection_pct')}% "
            f"bar_acc={row.get('bar_accuracy_pct')}% "
            f"steel={row.get('steel_accuracy_pct')}%"
        )
    lines.extend(["", "## Top Error Categories", ""])
    for etype, count in (errs.get("frequency") or {}).items():
        lines.append(f"- {etype}: {count}")
    lines.extend([
        "",
        "## Recommendation",
        "",
        bench.get("recommendation", "Review per-drawing-set error summaries before production promotion."),
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
