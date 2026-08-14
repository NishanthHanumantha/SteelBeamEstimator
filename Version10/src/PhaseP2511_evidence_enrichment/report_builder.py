"""P2.5.11 STATUS and comparison artefacts."""
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
    cmp = summary.get("comparison") or {}
    metrics = cmp.get("metrics") or {}
    counts = cmp.get("gate_counts") or {}
    rec = summary.get("recommendation") or {}
    unit = summary.get("unit_tests") or {}
    prod = summary.get("production") or {}
    fixtures = summary.get("fixture_outcomes") or {}
    diags = summary.get("diagnostics") or []
    trans = cmp.get("transition") or {}
    trans_c = trans.get("counts") or {}

    unknown = cmp.get("unknown_only") or {}
    det_row = {
        "baseline_steel": unknown.get("baseline_steel"),
        "vision_shadow_steel": unknown.get("baseline_steel"),
        "estimator_steel": unknown.get("estimator_steel"),
        "steel_accuracy": unknown.get("baseline_accuracy"),
        "absolute_error": unknown.get("baseline_absolute_error"),
        "stirrup_accuracy": (unknown.get("stirrup") or {}).get("stirrup_accuracy_before"),
        "improved_beams": 0,
        "unchanged_beams": 143,
        "worsened_beams": 0,
    }

    def _row(name: str, r: Dict[str, Any]) -> str:
        return (
            f"| {name} | {_fmt(r.get('baseline_steel'))} | {_fmt(r.get('vision_shadow_steel'))} | "
            f"{_fmt(r.get('estimator_steel'))} | {_fmt(r.get('steel_accuracy'))} | "
            f"{_fmt(r.get('absolute_error'))} | {_fmt(r.get('stirrup_accuracy'))} | "
            f"{_fmt(r.get('improved_beams'))} | {_fmt(r.get('unchanged_beams'))} | "
            f"{_fmt(r.get('worsened_beams'))} |"
        )

    diag_lines = [
        "",
        "| beam_id | p2510 | p2511 | strength | quality | reasons | effect |",
        "|---------|-------|-------|----------|---------|---------|--------|",
    ]
    for d in diags:
        diag_lines.append(
            f"| {d.get('beam_id')} | {d.get('p2510_decision')} | {d.get('p2511_decision')} | "
            f"{d.get('evidence_strength')} | {d.get('annotation_quality')} | "
            f"{','.join(d.get('reason_codes') or [])} | {d.get('shadow_accuracy_effect')} |"
        )

    lines = [
        "# P2.5.11 STATUS",
        "",
        "---------------------------------------------------",
        "IDENTITY",
        "---------------------------------------------------",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"PHASE_ID: {PHASE_ID}",
        f"PHASE_NAME: {PHASE_NAME}",
        f"STATUS: {summary.get('pass_fail')}",
        f"FINAL_DECISION: {rec.get('class')}",
        "",
        "P2.5.11 does NOT authorize production promotion.",
        "P2.5.11 is RESEARCH / SHADOW ONLY.",
        "",
        "---------------------------------------------------",
        "COUNTING UNIT",
        "---------------------------------------------------",
        "",
        "Primary KPIs use unique model-detected beams (Fifth Set = 143).",
        f"unique_model_detected: {cmp.get('unique_model_detected')}",
        "",
        "---------------------------------------------------",
        "STRATEGY COMPARISON",
        "---------------------------------------------------",
        "",
        "| Strategy | Baseline kg | Shadow kg | Estimator kg | Accuracy | Abs err | Stirrup acc | Improved | Unchanged | Worsened |",
        "|----------|-------------|-----------|--------------|----------|---------|-------------|----------|-----------|----------|",
        _row("Deterministic", det_row),
        _row("P259_UNKNOWN_ONLY", cmp.get("unknown_only") or {}),
        _row("P2510_GATED_UNKNOWN_ONLY", cmp.get("p2510_gated") or {}),
        _row("P2511_EVIDENCE_ENRICHED", cmp.get("p2511_enriched") or {}),
        "",
        f"deterministic accuracy: {metrics.get('deterministic_accuracy')}",
        f"P2.5.9 accuracy: {metrics.get('p259_accuracy')}",
        f"P2.5.10 accuracy: {metrics.get('p2510_accuracy')}",
        f"P2.5.11 accuracy: {metrics.get('p2511_accuracy')}",
        "",
        "---------------------------------------------------",
        "GATE COUNTS",
        "---------------------------------------------------",
        "",
        f"ALLOW: {counts.get('ALLOW')}",
        f"HOLD: {counts.get('HOLD')}",
        f"REJECT: {counts.get('REJECT')}",
        "",
        "---------------------------------------------------",
        "TRANSITION MATRIX (P2.5.10 → P2.5.11)",
        "---------------------------------------------------",
        "",
        f"P2.5.10 ALLOW → P2.5.11 ALLOW: {trans_c.get('P2510_ALLOW_TO_P2511_ALLOW')}",
        f"P2.5.10 HOLD  → P2.5.11 ALLOW: {trans_c.get('P2510_HOLD_TO_P2511_ALLOW')}",
        f"P2.5.10 HOLD  → P2.5.11 HOLD: {trans_c.get('P2510_HOLD_TO_P2511_HOLD')}",
        f"P2.5.10 ALLOW → P2.5.11 HOLD: {trans_c.get('P2510_ALLOW_TO_P2511_HOLD')}",
        "",
        f"P2.5.10 HOLDs recovered: {cmp.get('holds_promoted')}",
        f"P2.5.9 improvements recovered vs P2.5.10: {cmp.get('improvements_recovered_vs_p2510')}",
        f"known worsenings prevented: {cmp.get('worsenings_prevented')}",
        f"worsened beams: {(cmp.get('p2511_enriched') or {}).get('worsened_beams')}",
        "",
        "---------------------------------------------------",
        "FIXTURES",
        "---------------------------------------------------",
        "",
        f"known worsening decisions: {fixtures.get('worsening_fixture_decisions')}",
        f"P2.5.10 ALLOW fixtures: {fixtures.get('p2510_allow_fixture_decisions')}",
        f"held-recovery fixtures: {fixtures.get('hold_recovery_fixture_decisions')}",
        f"known worsenings blocked: {fixtures.get('known_worsenings_blocked')}",
        "",
        "---------------------------------------------------",
        "CASE DIAGNOSTICS",
        "---------------------------------------------------",
        *diag_lines,
        "",
        "---------------------------------------------------",
        "SAFETY / FIREWALL",
        "---------------------------------------------------",
        "",
        f"production mutations: {prod.get('production_mutation_count')}",
        f"steel / BBS / Excel production difference: {prod.get('steel_production_difference')} / {prod.get('bbs_production_difference')} / {prod.get('excel_production_difference')}",
        f"runtime leakage scan: {summary.get('gt_leakage_ok')}",
        f"P2.5.9 regression: {summary.get('p259_regression_ok')}",
        f"P2.5.10 regression: {summary.get('p2510_regression_ok')}",
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
        f"recommended_class: {rec.get('class')}",
        str(rec.get("rationale") or ""),
        "",
        "P2.5.11 does NOT authorize production promotion.",
        "",
    ]
    md = "\n".join(lines)
    (out_root / "P2.5.11_STATUS.md").write_text(md, encoding="utf-8")
    (out_root / "reports" / "P2.5.11_STATUS.md").write_text(md, encoding="utf-8")
    _dump(out_root / "P2.5.11_RESULTS.json", summary)
    _dump(out_root / "P2.5.11_CASE_DIAGNOSTICS.json", diags)
    _dump(out_root / "P2.5.11_TRANSITION_MATRIX.json", trans)
    _dump(out_root / "evaluation" / "summary.json", summary)
    return {"status_md": str(out_root / "P2.5.11_STATUS.md")}


__all__ = ["write_reports"]
