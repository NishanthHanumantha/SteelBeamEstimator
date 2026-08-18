"""P2.6.3 status report. Gated replay — not a new Vision benchmark."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _pct(v: Any) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, str):
        return v
    try:
        return f"{100.0 * float(v):.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def _num(v: Any, digits: int = 2) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return str(v)


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    m = result.get("metrics") or {}
    rec = result.get("recommendation") or {}
    sample = result.get("sample") or {}
    tests = result.get("unit_tests") or {}
    prod = result.get("production") or {}
    fw = result.get("firewall") or {}
    leak = result.get("leakage") or {}
    by_s = m.get("by_stratum") or {}
    by_t = m.get("by_candidate_type") or {}
    long_m = m.get("longitudinal") or {}
    p262 = m.get("p262_baseline") or {}
    false_skips: List[Dict[str, Any]] = result.get("false_skips") or []
    false_calls: List[Dict[str, Any]] = result.get("false_calls") or []
    examples = (result.get("evidence") or {}).get("examples") or []
    p261_prec = m.get("BASELINE_PRECISION")
    p261_uns = m.get("BASELINE_UNSUPPORTED_RATE")
    p261_dup = m.get("DUPLICATE_RATE_BASELINE")
    p261_tr = m.get("BASELINE_TRUE_RECOVERIES")

    md = [
        "# P2.6.3 — Longitudinal-Aware Selective Vision Gate Status",
        "",
        "Gated replay using frozen P2.6.1 Vision responses. This is not a new Vision benchmark.",
        "Shadow / research only. Production promotion is NOT AUTHORIZED.",
        "",
        "------------------------------------------------------------",
        "IDENTITY",
        "------------------------------------------------------------",
        "",
        f"- **MODEL_VERSION**: {result.get('model_version')}",
        f"- **PHASE**: {result.get('phase_id')} {result.get('phase_name')}",
        f"- **GATE_VERSION**: {result.get('gate_version')}",
        f"- **STATUS**: Shadow / research only. NEVER PRODUCTION_READY.",
        f"- **EXECUTION_MODE**: {result.get('mode')}",
        f"- **PRODUCTION_MUTATION**: {prod.get('production_mutation_count', 0)}",
        f"- **TESTS**: {tests.get('passed')}/{tests.get('total')} ({'PASS' if tests.get('success') else 'FAIL'})",
        "",
        "------------------------------------------------------------",
        "DATASET",
        "------------------------------------------------------------",
        "",
        "- **source**: frozen P2.6.1 stratified sample (not resampled)",
        f"- **beams**: {m.get('TOTAL_BEAMS')}",
        f"- **drawing sets**: {sample.get('drawing_sets') or ['Fourth', 'Fifth', 'Sixth']}",
        f"- **strata**: {json.dumps(sample.get('selected_by_stratum') or {'DIFFICULT': 25, 'NORMAL': 25, 'EASY': 25})}",
        f"- **seed**: {sample.get('seed')}",
        "- **GT_USED_FOR_GATE = FALSE**",
        "",
        "------------------------------------------------------------",
        "BASELINE",
        "------------------------------------------------------------",
        "",
        "P2.6.1 (ungated frozen Vision):",
        f"- candidates: {m.get('TOTAL_BASELINE_VISION_CANDIDATES')}",
        f"- duplicate rate: {_pct(p261_dup)}",
        f"- precision: {_pct(p261_prec)}",
        f"- unsupported: {_pct(p261_uns)}",
        f"- TRUE_RECOVERIES: {p261_tr}",
        "",
        "P2.6.2 V1.1 gated replay:",
        f"- CALL: {p262.get('CALL_BEAMS')} SKIP: {p262.get('SKIP_BEAMS')} HOLD: {p262.get('HOLD_BEAMS')}",
        f"- call reduction: {_pct(p262.get('CALL_REDUCTION'))}",
        f"- gated candidates: {p262.get('GATED_VISION_CANDIDATES')}",
        f"- gated duplicate rate: {_pct(p262.get('DUPLICATE_RATE_GATED'))}",
        f"- gated precision: {_pct(p262.get('GATED_PRECISION'))}",
        f"- gated unsupported: {_pct(p262.get('GATED_UNSUPPORTED_RATE'))}",
        f"- gated TRUE_RECOVERIES: {p262.get('GATED_TRUE_RECOVERIES')}",
        f"- recovery retention: {_pct(p262.get('RECOVERY_RETENTION_RATE'))}",
        f"- false skips: {p262.get('FALSE_SKIPS')} false calls: {p262.get('FALSE_CALLS')}",
        f"- stirrup retained: {p262.get('STIRRUP_RETAINED')}/18",
        f"- longitudinal retained: {p262.get('LONGITUDINAL_RETAINED')}/8",
        "",
        "------------------------------------------------------------",
        "P2.6.3 RESULTS",
        "------------------------------------------------------------",
        "",
        f"- **total beams**: {m.get('TOTAL_BEAMS')}",
        f"- **CALL**: {m.get('CALL_BEAMS')}",
        f"- **SKIP**: {m.get('SKIP_BEAMS')}",
        f"- **HOLD**: {m.get('HOLD_BEAMS')}",
        f"- **call reduction**: {_pct(m.get('CALL_REDUCTION'))}",
        f"- **baseline candidates**: {m.get('TOTAL_BASELINE_VISION_CANDIDATES')}",
        f"- **gated candidates**: {m.get('GATED_VISION_CANDIDATES')}",
        f"- **baseline duplicate rate**: {_pct(m.get('DUPLICATE_RATE_BASELINE'))}",
        f"- **gated duplicate rate**: {_pct(m.get('DUPLICATE_RATE_GATED'))}",
        f"- **baseline precision**: {_pct(m.get('BASELINE_PRECISION'))}",
        f"- **gated precision**: {_pct(m.get('GATED_PRECISION'))}",
        f"- **baseline unsupported**: {_pct(m.get('BASELINE_UNSUPPORTED_RATE'))}",
        f"- **gated unsupported**: {_pct(m.get('GATED_UNSUPPORTED_RATE'))}",
        f"- **gated ambiguous**: {_pct(m.get('GATED_AMBIGUOUS_RATE'))}",
        f"- **baseline TRUE_RECOVERIES**: {m.get('BASELINE_TRUE_RECOVERIES')}",
        f"- **gated TRUE_RECOVERIES**: {m.get('GATED_TRUE_RECOVERIES')}",
        f"- **recovery retention**: {_pct(m.get('RECOVERY_RETENTION_RATE'))}",
        f"- **false skips**: {m.get('FALSE_SKIPS')}",
        f"- **false calls**: {m.get('FALSE_CALLS')}",
        f"- **TRUE_RECOVERIES per 100 calls**: {m.get('TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED')}",
        "",
        "------------------------------------------------------------",
        "LONGITUDINAL RESULTS",
        "------------------------------------------------------------",
        "",
        f"- baseline candidates: {long_m.get('baseline_candidates')}",
        f"- gated candidates: {long_m.get('gated_candidates')}",
        f"- baseline duplicates: {long_m.get('baseline_duplicates')}",
        f"- gated duplicates: {long_m.get('gated_duplicates')}",
        f"- baseline true recoveries: {long_m.get('baseline_true_recoveries')}",
        f"- gated true recoveries: {long_m.get('gated_true_recoveries')}",
        f"- retained recoveries: {long_m.get('retained_recoveries')}",
        f"- lost recoveries: {long_m.get('lost_recoveries')}",
        f"- longitudinal recovery retention: {_pct(m.get('LONGITUDINAL_RECOVERY_RETENTION'))}",
        f"- precision: {_pct(long_m.get('precision'))}",
        f"- unsupported: {_pct(long_m.get('unsupported_rate'))}",
        f"- ambiguous: {_pct(long_m.get('ambiguous_rate'))}",
        f"- false skips: {long_m.get('false_skips')}",
        f"- false calls: {long_m.get('false_calls')}",
        "",
        "Coverage-condition beam counts (production-only classification):",
        f"- `{json.dumps(m.get('longitudinal_coverage_counts') or {})}`",
        f"- conditions `{json.dumps(m.get('coverage_condition_counts') or {})}`",
        "",
        "------------------------------------------------------------",
        "STIRRUP REGRESSION",
        "------------------------------------------------------------",
        "",
        f"- baseline TRUE_RECOVERIES: {m.get('STIRRUP_BASELINE_TRUE_RECOVERIES')}",
        f"- gated TRUE_RECOVERIES: {m.get('STIRRUP_GATED_TRUE_RECOVERIES')}",
        f"- recovery retention: {_pct(m.get('STIRRUP_RECOVERY_RETENTION'))}",
        "- expected: 18/18",
        "",
        "------------------------------------------------------------",
        "STRATUM (evaluation-only)",
        "------------------------------------------------------------",
        "",
        "Stratum is not a runtime gate feature.",
        "",
    ]
    for name in ("DIFFICULT", "NORMAL", "EASY"):
        b = by_s.get(name) or {}
        md.append(
            f"- **{name}**: beams={b.get('beams')} call={b.get('call')} "
            f"call_rate={_pct(b.get('call_rate'))} saved={b.get('calls_saved')} "
            f"retained={b.get('recoveries_retained')} lost={b.get('recoveries_lost')}"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "CANDIDATE TYPE",
        "------------------------------------------------------------",
        "",
    ]
    for name in ("STIRRUP", "LONGITUDINAL_REINFORCEMENT", "SIDE_FACE_REINFORCEMENT", "OTHER"):
        b = by_t.get(name) or {}
        md.append(
            f"- **{name}**: baseline={b.get('baseline_candidates')} gated={b.get('gated_candidates')} "
            f"dup {b.get('baseline_duplicates')}→{b.get('gated_duplicates')} "
            f"recoveries {b.get('baseline_true_recoveries')}→{b.get('gated_true_recoveries')} "
            f"lost={b.get('lost_recoveries')}"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "GATE REASONS",
        "------------------------------------------------------------",
        "",
        f"- **CALL**: `{json.dumps(m.get('call_reason_counts') or {})}`",
        f"- **SKIP**: `{json.dumps(m.get('skip_reason_counts') or {})}`",
        "",
        "------------------------------------------------------------",
        "FALSE SKIPS",
        "------------------------------------------------------------",
        "",
    ]
    if not false_skips:
        md.append("- none")
    for fs in false_skips:
        md.append(
            f"- `{fs.get('set_key')}/{fs.get('beam_id')}` text=`{fs.get('annotation')}` "
            f"role=`{fs.get('role')}` dia=`{fs.get('diameter')}` qty=`{fs.get('quantity')}` "
            f"coverage=`{fs.get('production_coverage')}` "
            f"decision=`{fs.get('gate_decision')}` reasons=`{fs.get('why_gate_skipped')}`"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "FALSE CALLS",
        "------------------------------------------------------------",
        "",
    ]
    if not false_calls:
        md.append("- none")
    for fc in false_calls:
        md.append(
            f"- `{fc.get('set_key')}/{fc.get('beam_id')}` reasons=`{fc.get('reason_codes')}` "
            f"cands={fc.get('candidate_count')} coverage=`{fc.get('production_coverage')}` "
            f"statuses=`{fc.get('gt_status_counts')}`"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "VISUAL EVIDENCE",
        "------------------------------------------------------------",
        "",
    ]
    if not examples:
        md.append("- No representative overlays were written.")
    for ex in examples:
        md.append(
            f"- `{ex.get('example_class')}`: `{ex.get('set_key')}/{ex.get('beam_id')}` "
            f"gate=`{ex.get('gate_decision')}` coverage=`{ex.get('production_coverage')}` "
            f"text=`{ex.get('annotation_text')}`"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "SAFETY",
        "------------------------------------------------------------",
        "",
        f"- production mutation = {prod.get('production_mutation_count', 0)}",
        f"- steel / BBS / Excel / R1.3 / SI unchanged: `{prod.get('fingerprints_ok')}`",
        f"- P2.6.2 artefacts unchanged: `{prod.get('fingerprints_ok')}`",
        f"- firewall ok: `{fw.get('ok')}`",
        f"- leakage ok: `{leak.get('ok')}`",
        f"- live Vision calls: {result.get('live_cost_usd', 'not run')}",
        f"- engineering mutation: {result.get('engineering_changes')}",
        "- GT_USED_FOR_GATE = FALSE",
        "",
        "------------------------------------------------------------",
        "DECISION",
        "------------------------------------------------------------",
        "",
        f"- **STRENGTH**: {rec.get('strength')}",
        f"- **DECISION**: {rec.get('decision')}",
        f"- {rec.get('note')}",
        "",
        "Allowed: READY_FOR_ENGINEERING_RECOMPUTE_PILOT | REFINE_LONGITUDINAL_GATE.",
        "NEVER: PRODUCTION_READY.",
        "",
        "P2.6.3 does not authorize production promotion or engineering recompute by itself;",
        "READY_FOR_ENGINEERING_RECOMPUTE_PILOT is a research classification only.",
        "",
    ]
    status_path = out_root / "P2.6.3_STATUS.md"
    text = "\n".join(md) + "\n"
    status_path.write_text(text, encoding="utf-8")
    (reports / "P2.6.3_STATUS.md").write_text(text, encoding="utf-8")
    (reports / "metrics.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    (reports / "longitudinal_metrics.json").write_text(
        json.dumps(long_m, indent=2, default=str), encoding="utf-8"
    )
    coverage_diag = {
        "longitudinal_coverage_counts": m.get("longitudinal_coverage_counts") or {},
        "coverage_condition_counts": m.get("coverage_condition_counts") or {},
        "by_coverage": long_m.get("by_coverage") or {},
        "call_reason_counts": m.get("call_reason_counts") or {},
        "skip_reason_counts": m.get("skip_reason_counts") or {},
        "by_stratum": by_s,
        "by_candidate_type": by_t,
        "per_beam": [
            {
                "set_key": d.get("set_key"),
                "beam_id": d.get("beam_id"),
                "eval_stratum": d.get("eval_stratum"),
                "decision": d.get("decision"),
                "reason_codes": d.get("reason_codes"),
                "longitudinal_coverage": d.get("longitudinal_coverage"),
                "coverage_conditions": d.get("coverage_conditions"),
            }
            for d in (result.get("decisions") or [])
        ],
    }
    (reports / "coverage_diagnostics.json").write_text(
        json.dumps(coverage_diag, indent=2, default=str), encoding="utf-8"
    )
    (reports / "false_skips.json").write_text(
        json.dumps(false_skips, indent=2, default=str), encoding="utf-8"
    )
    (reports / "false_calls.json").write_text(
        json.dumps(false_calls, indent=2, default=str), encoding="utf-8"
    )
    (reports / "unit_tests.json").write_text(
        json.dumps(tests, indent=2, default=str), encoding="utf-8"
    )
    (reports / "firewall.json").write_text(
        json.dumps({"firewall": fw, "production": prod}, indent=2, default=str), encoding="utf-8"
    )
    (reports / "leakage.json").write_text(json.dumps(leak, indent=2, default=str), encoding="utf-8")
    return {
        "status": str(status_path),
        "metrics": str(reports / "metrics.json"),
        "longitudinal_metrics": str(reports / "longitudinal_metrics.json"),
        "coverage_diagnostics": str(reports / "coverage_diagnostics.json"),
    }


__all__ = ["write_reports"]
