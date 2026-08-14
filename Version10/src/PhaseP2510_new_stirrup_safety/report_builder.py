"""P2.5.10 STATUS and comparison artefacts."""
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
    unknown = cmp.get("unknown_only") or {}
    gated = cmp.get("gated") or {}
    fixtures = summary.get("fixture_outcomes") or {}
    diags = summary.get("diagnostics") or []

    def _row(name: str, r: Dict[str, Any]) -> str:
        return (
            f"| {name} | {_fmt(r.get('baseline_steel'))} | {_fmt(r.get('vision_shadow_steel'))} | "
            f"{_fmt(r.get('estimator_steel'))} | {_fmt(r.get('steel_accuracy'))} | "
            f"{_fmt(r.get('absolute_error'))} | {_fmt(r.get('improved_beams'))} | "
            f"{_fmt(r.get('unchanged_beams'))} | {_fmt(r.get('worsened_beams'))} |"
        )

    diag_lines = [
        "",
        "| beam_id | insertion | gate | reasons | new_zone | new_piece | steel_before | steel_after | delta | effect |",
        "|---------|-----------|------|---------|----------|-----------|--------------|-------------|-------|--------|",
    ]
    for d in diags:
        diag_lines.append(
            f"| {d.get('beam_id')} | {d.get('insertion_classification')} | {d.get('gate_decision')} | "
            f"{','.join(d.get('reason_codes') or [])} | {d.get('new_zone')} | {d.get('new_piece')} | "
            f"{d.get('steel_before')} | {d.get('steel_after')} | {d.get('steel_delta')} | "
            f"{d.get('shadow_accuracy_effect')} |"
        )

    worse_lines = []
    for row in fixtures.get("worsening_fixtures") or []:
        worse_lines.append(
            f"- {row.get('beam_id')}: class={row.get('insertion_classification')} "
            f"decision={row.get('gate_decision')} reasons={row.get('reason_codes')} "
            f"delta={row.get('steel_delta')} effect={row.get('shadow_accuracy_effect')}"
        )
    if not worse_lines:
        worse_lines = ["- (no matching gate decisions for evaluation fixtures)"]

    lines = [
        "# P2.5.10 STATUS",
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
        "P2.5.10 does NOT authorize production promotion.",
        "P2.5.10 is a SAFETY GATE RESEARCH PHASE, not a promotion phase.",
        "",
        "---------------------------------------------------",
        "COUNTING UNIT",
        "---------------------------------------------------",
        "",
        "Primary KPIs use unique model-detected beams (Fifth Set = 143).",
        "P2.5.8 union counting (185) is retained as a documented secondary universe.",
        f"unique_model_detected_unknown: {cmp.get('unique_model_detected_unknown')}",
        f"unique_model_detected_gated: {cmp.get('unique_model_detected_gated')}",
        "",
        "---------------------------------------------------",
        "UNKNOWN_ONLY vs GATED (unique model-detected beams)",
        "---------------------------------------------------",
        "",
        "| Strategy | Baseline kg | Shadow kg | Estimator kg | Accuracy | Abs err | Improved | Unchanged | Worsened |",
        "|----------|-------------|-----------|--------------|----------|---------|----------|-----------|----------|",
        _row("P259_UNKNOWN_ONLY", unknown),
        _row("P2510_GATED_UNKNOWN_ONLY", gated),
        "",
        f"deterministic steel: {metrics.get('deterministic_steel')}",
        f"P2.5.9 UNKNOWN_ONLY steel: {metrics.get('p259_unknown_steel')}",
        f"P2.5.10 gated steel: {metrics.get('p2510_gated_steel')}",
        f"estimator steel: {metrics.get('estimator_steel')}",
        f"deterministic accuracy: {metrics.get('deterministic_accuracy')}",
        f"P2.5.9 accuracy: {metrics.get('p259_accuracy')}",
        f"P2.5.10 accuracy: {metrics.get('p2510_accuracy')}",
        f"accuracy delta vs deterministic: {cmp.get('accuracy_delta_vs_deterministic')}",
        f"accuracy delta vs P2.5.9: {cmp.get('accuracy_delta_vs_unknown')}",
        f"steel delta vs P2.5.9: {cmp.get('steel_delta_vs_unknown')}",
        "",
        "---------------------------------------------------",
        "GATE COUNTS",
        "---------------------------------------------------",
        "",
        f"ALLOW: {counts.get('ALLOW')}",
        f"HOLD: {counts.get('HOLD')}",
        f"REJECT: {counts.get('REJECT')}",
        f"NO_NEW_STIRRUP: {counts.get('NO_NEW_STIRRUP')}",
        f"SUPPLEMENTS_EXISTING_STIRRUP: {counts.get('SUPPLEMENTS_EXISTING_STIRRUP')}",
        f"CREATES_NEW_STIRRUP: {counts.get('CREATES_NEW_STIRRUP')}",
        f"new-zone: {counts.get('new_zone')}",
        f"new-piece: {counts.get('new_piece')}",
        f"new-steel: {counts.get('new_steel')}",
        "",
        "---------------------------------------------------",
        "TRADE-OFF",
        "---------------------------------------------------",
        "",
        f"worsenings prevented by gate: {cmp.get('worsenings_prevented')}",
        f"improvements lost because of gate: {cmp.get('improvements_lost')}",
        f"improvements retained: {cmp.get('improvements_retained')}",
        "",
        "---------------------------------------------------",
        "CURRENT UNKNOWN_ONLY WORSENING FIXTURES",
        "---------------------------------------------------",
        "",
        *worse_lines,
        "",
        "---------------------------------------------------",
        "CURRENT IMPROVEMENT FIXTURES",
        "---------------------------------------------------",
        "",
        f"decisions: {fixtures.get('improvement_fixture_decisions')}",
        "",
        "---------------------------------------------------",
        "BEAM-LEVEL DIAGNOSTICS",
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
        "P2.5.10 does NOT authorize production promotion.",
        "Do not change production arbitration from this phase.",
        "",
    ]
    md = "\n".join(lines)
    (out_root / "P2.5.10_STATUS.md").write_text(md, encoding="utf-8")
    (out_root / "reports" / "P2.5.10_STATUS.md").write_text(md, encoding="utf-8")
    _dump(out_root / "evaluation" / "summary.json", summary)
    _dump(out_root / "comparison" / "strategy_comparison.json", cmp)
    _dump(out_root / "comparison" / "beam_diagnostics.json", diags)
    _dump(out_root / "evaluation" / "safety_decisions.json", summary.get("gate_decisions") or [])
    return {"status_md": str(out_root / "P2.5.10_STATUS.md")}


__all__ = ["write_reports"]
