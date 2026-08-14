"""P2.5.9 STATUS + strategy comparison artefacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import ENGINEERING_CHANGES, MODEL_VERSION, PHASE_ID, PHASE_NAME


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _fmt(v: Any) -> str:
    return "N/A" if v is None else str(v)


def write_reports(*, out_root: Path, summary: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    (out_root / "reports").mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = summary.get("strategy_rows") or []
    analysis = summary.get("class_analysis") or {}
    rec = summary.get("recommendation") or {}
    counting = summary.get("counting") or {}
    unit = summary.get("unit_tests") or {}
    prod = summary.get("production") or {}
    cost = summary.get("cost") or {}

    table = [
        "",
        "| Strategy | Baseline kg | Shadow kg | Estimator kg | Accuracy | Abs err | Err red | Stirrup acc | Improved | Unchanged | Worsened | Unknown acc | Partial acc | Partial hold | Partial rej | Prod mut |",
        "|----------|-------------|-----------|--------------|----------|---------|---------|-------------|----------|-----------|----------|-------------|-------------|--------------|-------------|----------|",
    ]
    for r in rows:
        table.append(
            "| {strategy} | {baseline_steel} | {vision_shadow_steel} | {estimator_steel} | {steel_accuracy} | {absolute_error} | {error_reduction} | {stirrup_accuracy} | {improved_beams} | {unchanged_beams} | {worsened_beams} | {unknown_fields_accepted} | {partial_fields_accepted} | {partial_fields_held} | {partial_fields_rejected} | {production_mutations} |".format(
                **{k: _fmt(r.get(k)) for k in (
                    "strategy", "baseline_steel", "vision_shadow_steel", "estimator_steel",
                    "steel_accuracy", "absolute_error", "error_reduction", "stirrup_accuracy",
                    "improved_beams", "unchanged_beams", "worsened_beams",
                    "unknown_fields_accepted", "partial_fields_accepted", "partial_fields_held",
                    "partial_fields_rejected", "production_mutations",
                )}
            )
        )

    lines = [
        "# P2.5.9 STATUS",
        "",
        "---------------------------------------------------",
        "IDENTITY",
        "---------------------------------------------------",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"PHASE_ID: {PHASE_ID}",
        f"PHASE_NAME: {PHASE_NAME}",
        f"STATUS: {summary.get('pass_fail')}",
        f"FINAL_DECISION: {summary.get('decision')}",
        "",
        "P2.5.9 does NOT authorize production promotion.",
        "",
        "---------------------------------------------------",
        "COUNTING UNIT",
        "---------------------------------------------------",
        "",
        str(counting.get("note") or ""),
        f"estimator_beam_ids: {counting.get('estimator_beam_ids')}",
        f"model_detected_beam_ids: {counting.get('baseline_model_beam_ids')}",
        f"union_beam_ids (P2.5.8 method): {counting.get('union_beam_ids')}",
        "Primary P2.5.9 impact counts use unique_model_detected beams.",
        "",
        "---------------------------------------------------",
        "STRATEGY COMPARISON (unique model-detected beams)",
        "---------------------------------------------------",
        *table,
        "",
        "---------------------------------------------------",
        "CLASS ANALYSIS",
        "---------------------------------------------------",
        "",
        f"P2.5.8 improvement pp: {_fmt(analysis.get('p258_improvement_pp'))}",
        f"UNKNOWN_ONLY improvement pp: {_fmt(analysis.get('unknown_only_improvement_pp'))}",
        f"CONSERVATIVE_PARTIAL improvement pp: {_fmt(analysis.get('conservative_improvement_pp'))}",
        f"UNKNOWN_ONLY vs P258 accuracy delta: {_fmt(analysis.get('unknown_only_vs_p258_accuracy_delta'))}",
        f"CONSERVATIVE vs UNKNOWN accuracy delta: {_fmt(analysis.get('conservative_vs_unknown_accuracy_delta'))}",
        f"P258 worsened that disappear under UNKNOWN_ONLY: {analysis.get('p258_worsened_disappear_under_unknown_only')}",
        f"P258 worsened remaining under UNKNOWN_ONLY: {analysis.get('p258_worsened_remaining_under_unknown_only')}",
        f"Conservative new worsened vs UNKNOWN: {analysis.get('conservative_new_worsened_vs_unknown')}",
        "",
        "---------------------------------------------------",
        "SAFETY / FIREWALL",
        "---------------------------------------------------",
        "",
        f"production mutations: {prod.get('production_mutation_count')}",
        f"steel / BBS / Excel production difference: {prod.get('steel_production_difference')} / {prod.get('bbs_production_difference')} / {prod.get('excel_production_difference')}",
        f"ground-truth leakage tests: {summary.get('gt_leakage_ok')}",
        f"P2.5.1–P2.5.8 regressions: {summary.get('regression_ok')}",
        "",
        "---------------------------------------------------",
        "COST",
        "---------------------------------------------------",
        "",
        f"new Claude calls: {cost.get('live_claude_calls', 0)}",
        f"estimated cost: {cost.get('estimated_cost_usd', 0.0)}",
        "replay: True",
        "",
        "---------------------------------------------------",
        "ENGINEERING CHANGES",
        "---------------------------------------------------",
        "",
        ENGINEERING_CHANGES,
        "",
        "---------------------------------------------------",
        "TESTS",
        "---------------------------------------------------",
        "",
        f"passed: {unit.get('passed')}/{unit.get('total')}",
        f"success: {unit.get('success')}",
        "",
        "---------------------------------------------------",
        "RECOMMENDATION",
        "---------------------------------------------------",
        "",
        f"recommended_promotion_class: {rec.get('class')}",
        f"proceed_to_P2.5.10: {rec.get('proceed_p2510')}",
        str(rec.get("rationale") or ""),
        "",
        "P2.5.9 does NOT authorize production promotion.",
        "",
    ]
    md = "\n".join(lines)
    (out_root / "P2.5.9_STATUS.md").write_text(md, encoding="utf-8")
    (out_root / "reports" / "P2.5.9_STATUS.md").write_text(md, encoding="utf-8")
    _dump(out_root / "evaluation" / "summary.json", summary)
    _dump(out_root / "comparison" / "strategy_comparison.json", rows)
    _dump(out_root / "comparison" / "class_analysis.json", analysis)
    return {"status_md": str(out_root / "P2.5.9_STATUS.md")}


__all__ = ["write_reports"]
