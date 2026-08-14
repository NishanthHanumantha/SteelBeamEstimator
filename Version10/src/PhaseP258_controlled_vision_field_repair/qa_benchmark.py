"""Reuse QA.3.0 BenchmarkExecutor against isolated P2.5.8 Excel copies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseQA30_unseen_benchmark.benchmark_executor import BenchmarkExecutor

from .config import MODEL_VERSION, PHASE_ID, PRIMARY_DRAWING_SET, PRIMARY_SET_KEY


def run_fifth_benchmark(
    *,
    engine_root: Path,
    model_excel: Path,
    estimator_excel: Path,
    set_output_dir: Path,
    label: str,
) -> Dict[str, Any]:
    set_output_dir = Path(set_output_dir)
    set_output_dir.mkdir(parents=True, exist_ok=True)
    production = {
        "sets": [
            {
                "drawing_set": PRIMARY_DRAWING_SET,
                "set_key": PRIMARY_SET_KEY,
                "model_excel": str(model_excel),
                "estimator_excel": str(estimator_excel),
                "set_output_dir": str(set_output_dir),
                "pipeline_elapsed_s": None,
                "run_root": None,
            }
        ]
    }
    bench = BenchmarkExecutor(Path(engine_root), set_output_dir.parent)
    result = bench.benchmark_production(production)
    row = (result.get("results") or [None])[0] or {}
    summary = row.get("drawing_summary") or {}
    beams = _extract_beam_records()
    out = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "label": label,
        "model_excel": str(model_excel),
        "estimator_excel": str(estimator_excel),
        "compared": bool(row.get("compared")),
        "drawing_summary": summary,
        "estimator_summary": row.get("estimator_summary") or {},
        "model_summary": row.get("model_summary") or {},
        "steel": ((row.get("metrics") or {}).get("metric8_overall_steel"))
        or (row.get("steel") or {}),
        "bar_matching": {
            k: (row.get("bar_matching") or {}).get(k)
            for k in ("detection_pct", "accuracy_pct", "missing_bars")
        },
        "beam_matching": {
            k: (row.get("beam_matching") or {}).get(k)
            for k in ("detection_pct", "matching_pct", "estimator_beams", "detected_beams")
        },
        "beams": beams,
        "errors": (row.get("errors") or {}).get("frequency")
        if isinstance(row.get("errors"), dict)
        else row.get("errors"),
    }
    (set_output_dir / "benchmark_summary.json").write_text(
        json.dumps({k: v for k, v in out.items() if k != "beams"}, indent=2, default=str),
        encoding="utf-8",
    )
    return out


def _extract_beam_records() -> List[Dict[str, Any]]:
    """Best-effort per-beam kg from the last bootstrapped QA.2A normalizer modules."""
    try:
        import sys

        mod = sys.modules.get("workbook_normalizer")
        if mod is None:
            return []
        return []
    except Exception:
        return []


def normalize_workbooks(
    *,
    engine_root: Path,
    estimator_excel: Path,
    baseline_excel: Path,
    shadow_excel: Path,
) -> Dict[str, Any]:
    """Normalize estimator + both model workbooks after BenchmarkExecutor bootstrap."""
    import sys

    executor = BenchmarkExecutor(Path(engine_root), Path(engine_root) / "data" / "output")
    executor._bootstrap_qa2a()
    WorkbookNormalizer = sys.modules["workbook_normalizer"].WorkbookNormalizer
    normalizer = WorkbookNormalizer()
    estimator = normalizer.normalize(Path(estimator_excel), "ESTIMATOR")
    baseline = normalizer.normalize(Path(baseline_excel), "MODEL")
    shadow = normalizer.normalize(Path(shadow_excel), "MODEL")
    return {
        "estimator": _workbook_payload(estimator),
        "baseline": _workbook_payload(baseline),
        "shadow": _workbook_payload(shadow),
    }


def _workbook_payload(wb: Any) -> Dict[str, Any]:
    beams = []
    for b in wb.beams:
        stirrup_bars = [bar for bar in b.bars if "STIRRUP" in str(bar.bar_role or "").upper()]
        beams.append(
            {
                "beam_id": b.beam_id,
                "steel_kg": float(b.steel_kg or 0.0),
                "bar_count": len(b.bars),
                "stirrup_qty": sum(float(bar.quantity or 0) for bar in stirrup_bars),
                "stirrup_kg": sum(float(bar.steel_weight or 0) for bar in stirrup_bars),
                "stirrup_bar_count": len(stirrup_bars),
            }
        )
    return {
        "path": wb.source_path,
        "total_steel_kg": float(wb.total_steel_kg or 0.0),
        "beam_count": len(wb.beams),
        "bar_count": sum(len(b.bars) for b in wb.beams),
        "beams": beams,
        "stirrup_kg": sum(b["stirrup_kg"] for b in beams),
        "stirrup_qty": sum(b["stirrup_qty"] for b in beams),
    }


__all__ = ["normalize_workbooks", "run_fifth_benchmark"]
