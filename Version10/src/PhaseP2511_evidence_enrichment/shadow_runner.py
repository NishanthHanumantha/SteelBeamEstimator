"""Isolated P2.5.11 shadow recompute. Evaluation layer may read workbooks; the gate does not."""
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
from PhaseP259_beam_safe_arbitration.arbitration import evaluate_strategy, promoted_only
from PhaseP259_beam_safe_arbitration.config import STRATEGY_UNKNOWN_ONLY
from PhaseP2510_new_stirrup_safety.shadow_runner import (
    build_contexts as build_p2510_contexts,
    _owned,
)

from .config import MODEL_VERSION, PHASE_ID, PRODUCTION_WRITE, STRATEGY_P2511
from .enrichment_gate import filter_promoted_enriched
from .evidence_resolver import build_enrichment_context


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def build_p2511_contexts(
    *,
    r13_doc: Dict[str, Any],
    audits: List[Dict[str, Any]],
    ownership: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    models = {m.get("beam_id"): m for m in (r13_doc.get("models") or []) if isinstance(m, dict)}
    ownership = ownership or {}
    out: Dict[str, Dict[str, Any]] = {}
    for audit in audits:
        bid = str(audit.get("beam_id") or "")
        if not bid:
            continue
        ann = str(audit.get("annotation_id") or "")
        out[bid] = build_enrichment_context(
            beam=models.get(bid),
            audit=audit,
            peer_audits=audits,
            owned_by_beam=_owned(ownership, bid, ann),
        )
    return out


def run_enriched_shadow(
    *,
    engine_root: Path,
    audits: List[Dict[str, Any]],
    r13_doc: Dict[str, Any],
    p259_contexts: Dict[str, Dict[str, Any]],
    source_run_root: Path,
    ownership: Dict[str, Any],
    scoped: Optional[Dict[str, Any]],
    estimator_excel: Path,
    baseline_excel: Path,
    strategy_dir: Path,
) -> Dict[str, Any]:
    strategy_dir = Path(strategy_dir)
    strategy_dir.mkdir(parents=True, exist_ok=True)
    candidates = evaluate_strategy(
        audits=audits, strategy=STRATEGY_UNKNOWN_ONLY, beam_contexts=p259_contexts
    )
    promoted = promoted_only(candidates)
    p2510_ctx = build_p2510_contexts(r13_doc=r13_doc, audits=audits, ownership=ownership)
    p2511_ctx = build_p2511_contexts(r13_doc=r13_doc, audits=audits, ownership=ownership)
    gated = filter_promoted_enriched(
        r13_doc=r13_doc,
        audits=audits,
        promoted=promoted,
        p2510_contexts=p2510_ctx,
        p2511_contexts=p2511_ctx,
    )
    allowed = gated["allowed_promoted"]
    _dump(strategy_dir / "p259_unknown_candidates.json", candidates)
    _dump(strategy_dir / "p259_unknown_promoted.json", promoted)
    _dump(strategy_dir / "gate_decisions.json", gated["decisions"])
    _dump(strategy_dir / "allowed_promoted.json", allowed)

    patched, provenance = apply_repairs(r13_doc=r13_doc, audits=audits, promoted=allowed)
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
            label=STRATEGY_P2511,
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
        "strategy": STRATEGY_P2511,
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "production_write": PRODUCTION_WRITE,
        "success": ok,
        "candidates": candidates,
        "promoted": promoted,
        "allowed": allowed,
        "gate": gated,
        "overlay": provenance,
        "recompute": recompute,
        "shadow_excel": shadow_xlsx,
        "shadow_bench": shadow_bench,
        "books": books,
    }


__all__ = ["build_p2511_contexts", "run_enriched_shadow"]
