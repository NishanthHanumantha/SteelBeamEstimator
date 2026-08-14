"""Run one isolated strategy: overlay + existing VB.1 + QA.2A. No production write."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP258_controlled_vision_field_repair.qa_benchmark import (
    normalize_workbooks,
    run_fifth_benchmark,
)
from PhaseP258_controlled_vision_field_repair.r13_overlay import apply_repairs
from PhaseP258_controlled_vision_field_repair.shadow_recompute import (
    copy_isolated,
    run_shadow_recompute,
)

from .arbitration import evaluate_strategy, promoted_only
from .config import MODEL_VERSION, PHASE_ID, PRODUCTION_WRITE


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def run_strategy_shadow(
    *,
    engine_root: Path,
    strategy: str,
    audits: List[Dict[str, Any]],
    r13_doc: Dict[str, Any],
    beam_contexts: Dict[str, Dict[str, Any]],
    source_run_root: Path,
    ownership: Dict[str, Any],
    scoped: Optional[Dict[str, Any]],
    estimator_excel: Path,
    baseline_excel: Path,
    baseline_bench: Dict[str, Any],
    strategy_dir: Path,
) -> Dict[str, Any]:
    strategy_dir = Path(strategy_dir)
    strategy_dir.mkdir(parents=True, exist_ok=True)
    candidates = evaluate_strategy(
        audits=audits, strategy=strategy, beam_contexts=beam_contexts
    )
    promoted = promoted_only(candidates)
    _dump(strategy_dir / "promotion_candidates.json", candidates)
    _dump(strategy_dir / "promoted_repairs.json", promoted)
    patched, provenance = apply_repairs(
        r13_doc=r13_doc, audits=audits, promoted=promoted
    )
    _dump(strategy_dir / "overlay_provenance.json", provenance)
    _dump(strategy_dir / "beam_reinforcement_models_shadow.json", patched)
    sandbox = strategy_dir / "sandbox"
    recompute = run_shadow_recompute(
        engine_root=engine_root,
        source_run_root=source_run_root,
        ownership=ownership,
        patched_r13=patched,
        sandbox_root=sandbox,
        scoped=scoped,
    )
    _dump(strategy_dir / "vb1_result.json", recompute)
    shadow_xlsx = None
    if recompute.get("success") and (recompute.get("vb1") or {}).get("workbook_path"):
        shadow_xlsx = copy_isolated(
            Path(recompute["vb1"]["workbook_path"]),
            strategy_dir / "Estimation_Output.xlsx",
        )
    ok = bool(shadow_xlsx and Path(shadow_xlsx).exists())
    shadow_bench: Dict[str, Any] = {}
    books: Dict[str, Any] = {}
    if ok:
        shadow_bench = run_fifth_benchmark(
            engine_root=engine_root,
            model_excel=Path(shadow_xlsx),
            estimator_excel=estimator_excel,
            set_output_dir=strategy_dir / "benchmark",
            label=strategy,
        )
        books = normalize_workbooks(
            engine_root=engine_root,
            estimator_excel=estimator_excel,
            baseline_excel=baseline_excel,
            shadow_excel=Path(shadow_xlsx),
        )
        _dump(
            strategy_dir / "normalized_totals.json",
            {k: {kk: vv for kk, vv in rec.items() if kk != "beams"} for k, rec in books.items()},
        )
    return {
        "strategy": strategy,
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "production_write": PRODUCTION_WRITE,
        "success": ok,
        "candidates": candidates,
        "promoted": promoted,
        "overlay": provenance,
        "recompute": recompute,
        "shadow_excel": shadow_xlsx,
        "shadow_bench": shadow_bench,
        "baseline_bench": baseline_bench,
        "books": books,
    }


__all__ = ["run_strategy_shadow"]
