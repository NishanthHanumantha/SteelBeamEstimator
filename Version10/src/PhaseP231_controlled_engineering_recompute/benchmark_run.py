"""
QA.3.0 Fourth-set benchmark against a specific Estimation_Output.xlsx.
MODEL_VERSION: 10.5.6
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from PhaseQA30_unseen_benchmark.benchmark_executor import BenchmarkExecutor

from .config import MODEL_VERSION, PHASE_ID


def run_fourth_benchmark(
    *,
    engine_root: Path,
    model_excel: Path,
    estimator_excel: Path,
    set_output_dir: Path,
    label: str,
) -> Dict[str, Any]:
    engine_root = Path(engine_root)
    set_output_dir = Path(set_output_dir)
    set_output_dir.mkdir(parents=True, exist_ok=True)

    production = {
        "sets": [
            {
                "drawing_set": "Fourth Set Drawings",
                "set_key": "Fourth",
                "model_excel": str(model_excel),
                "estimator_excel": str(estimator_excel),
                "set_output_dir": str(set_output_dir),
                "pipeline_elapsed_s": None,
                "run_root": None,
            }
        ]
    }
    bench = BenchmarkExecutor(engine_root, set_output_dir.parent)
    result = bench.benchmark_production(production)
    rows = result.get("results") or result.get("sets") or []
    # BenchmarkExecutor returns dict with "results" key? check return
    if not rows and isinstance(result, dict):
        # may return {drawing_set_results: ...} or list under "results"
        for key in ("results", "drawing_set_results", "sets"):
            if isinstance(result.get(key), list):
                rows = result[key]
                break
    row = None
    if isinstance(result, dict) and "results" in result:
        row = (result.get("results") or [None])[0]
    elif isinstance(rows, list) and rows:
        row = rows[0]
    else:
        # read written benchmark_result.json
        br = set_output_dir / "benchmark_result.json"
        if br.exists():
            row = json.loads(br.read_text(encoding="utf-8"))

    summary = {}
    if isinstance(row, dict):
        summary = row.get("drawing_summary") or {
            "beam_detection_pct": (row.get("beam_matching") or {}).get("detection_pct"),
            "bar_detection_pct": (row.get("bar_matching") or {}).get("detection_pct"),
            "bar_accuracy_pct": (row.get("bar_matching") or {}).get("accuracy_pct"),
            "steel_accuracy_pct": (
                ((row.get("metrics") or {}).get("metric8_overall_steel") or {}).get(
                    "accuracy_pct"
                )
            ),
            "estimator_kg": (
                ((row.get("metrics") or {}).get("metric8_overall_steel") or {}).get(
                    "estimator_total_kg"
                )
            ),
            "model_kg": (
                ((row.get("metrics") or {}).get("metric8_overall_steel") or {}).get(
                    "model_total_kg"
                )
            ),
        }
        if "estimator_summary" in row:
            summary["estimator_summary"] = row["estimator_summary"]
        if "model_summary" in row:
            summary["model_summary"] = row["model_summary"]

    # overall accuracy if available from metrics
    if isinstance(row, dict):
        metrics = row.get("metrics") or {}
        if "metric9_overall" in metrics:
            summary["overall_accuracy_pct"] = metrics["metric9_overall"].get(
                "accuracy_pct"
            )
        elif "overall_accuracy_pct" in (row.get("drawing_summary") or {}):
            summary["overall_accuracy_pct"] = row["drawing_summary"][
                "overall_accuracy_pct"
            ]

    out = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "label": label,
        "model_excel": str(model_excel),
        "estimator_excel": str(estimator_excel),
        "compared": bool(summary),
        "drawing_summary": summary,
        "raw_result_keys": list(result.keys()) if isinstance(result, dict) else [],
    }
    (set_output_dir / "benchmark_summary.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    return out
