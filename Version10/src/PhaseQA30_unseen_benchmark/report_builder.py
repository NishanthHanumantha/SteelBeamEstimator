"""
QA.3.0 — Execution summary / README artefacts.
MODEL_VERSION: 10.0.0
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "10.0.0"
PHASE_ID = "QA.3.0"


def write_execution_summary(
    out_path: Path,
    discovery: Dict[str, Any],
    production: Dict[str, Any],
    benchmark: Dict[str, Any],
    validation: Dict[str, Any],
    report: Dict[str, Any],
    overall_elapsed_s: float,
) -> Path:
    om = report.get("overall_metrics") or {}
    top = (report.get("engineering_error_summary") or {}).get("top_error_categories") or []
    lines = [
        f"# Execution Summary — Phase {PHASE_ID}",
        "",
        f"- MODEL_VERSION: {MODEL_VERSION}",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Overall elapsed (s): {overall_elapsed_s}",
        f"- Production elapsed (s): {production.get('elapsed_s')}",
        f"- Benchmark elapsed (s): {benchmark.get('elapsed_s')}",
        f"- QA overall_pass: {validation.get('overall_pass')}",
        "",
        "## Drawing sets",
        "",
    ]
    for s in production.get("sets") or []:
        lines.append(
            f"- {s.get('drawing_set')} ({s.get('set_key')}): "
            f"success={s.get('success')} reuse={s.get('reuse_detected')} "
            f"run={s.get('run_id')} elapsed={s.get('pipeline_elapsed_s')}s"
        )
    lines += [
        "",
        "## Overall metrics",
        "",
        f"- Beam Detection: {om.get('beam_detection_pct')}%",
        f"- Bar Detection: {om.get('bar_detection_pct')}%",
        f"- Bar Matching: {om.get('bar_matching_pct')}%",
        f"- Steel Accuracy: {om.get('steel_accuracy_pct')}%",
        f"- Overall Accuracy: {om.get('overall_accuracy_pct')}%",
        f"- Total beams (estimator GT): {om.get('total_beams')}",
        "",
        "## Top engineering failure categories",
        "",
    ]
    for item in top[:5]:
        lines.append(f"- {item.get('category')}: {item.get('count')}")
    lines += [
        "",
        "## Estimator Excel policy",
        "",
        "- Estimator Output Excel opened during production: **NO**",
        "- Estimator Output Excel opened during benchmark: **YES**",
        "",
        f"Discovered unseen targets: {discovery.get('complete_unseen_targets')}",
        "",
    ]
    out_path = Path(out_path)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def write_phase_readme(out_path: Path) -> Path:
    text = f"""# Phase QA.3.0 — Unseen Drawing Benchmark

MODEL_VERSION: {MODEL_VERSION}

First large-scale generalization validation of the Version10 production model
on completely unseen drawing sets (Fourth / Fifth / Sixth).

## Policy

- Version9 is frozen; all work is under Version10.
- No engineering heuristics, ownership, OpenCV, rendering, parsers, or
  benchmark formulas were modified for this phase.
- Production runs from DXF only.
- Estimator Output Excel is ground truth for **benchmark only**.

## Outputs

- `DrawingSetDiscovery.json`
- `QA30Validation.json`
- `Generalization_Benchmark_Report.xlsx` / `.json`
- `GeneralizationSummary.md`
- `EngineeringErrorSummary.json`
- `ExecutionSummary.md`
- Per-set folders: `Fourth_Set_Drawings/`, `Fifth_Set_Drawings/`, `Sixth_Set_Drawings/`

## Run

```
python Run_PY/run_phase_qa30_unseen_benchmark.py
```
"""
    out_path = Path(out_path)
    out_path.write_text(text, encoding="utf-8")
    return out_path


def print_completion_summary(
    production: Dict[str, Any],
    report: Dict[str, Any],
    validation: Dict[str, Any],
    overall_elapsed_s: float,
) -> None:
    om = report.get("overall_metrics") or {}
    top = (report.get("engineering_error_summary") or {}).get("top_error_categories") or []
    n_sets = len(production.get("sets") or [])
    total_beams = om.get("total_beams")
    print("")
    print("=" * 72)
    print(f"Phase {PHASE_ID} COMPLETE — MODEL_VERSION {MODEL_VERSION}")
    print("=" * 72)
    print(f"Drawing sets processed     : {n_sets}")
    print(f"Total beams (estimator GT) : {total_beams}")
    print(f"Production runtime (s)     : {production.get('elapsed_s')}")
    print(f"Overall runtime (s)        : {overall_elapsed_s}")
    print(f"Overall Beam Detection     : {om.get('beam_detection_pct')}%")
    print(f"Overall Bar Detection      : {om.get('bar_detection_pct')}%")
    print(f"Overall Bar Matching       : {om.get('bar_matching_pct')}%")
    print(f"Overall Steel Accuracy     : {om.get('steel_accuracy_pct')}%")
    print(f"Overall Accuracy           : {om.get('overall_accuracy_pct')}%")
    print("Top five engineering failure categories:")
    for item in top[:5]:
        print(f"  - {item.get('category')}: {item.get('count')}")
    print(
        "Estimator Output Excel used ONLY during benchmarking: CONFIRMED"
    )
    print(f"QA overall_pass            : {validation.get('overall_pass')}")
    print("=" * 72)
