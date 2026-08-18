"""P2.6.4 status report. Gated replay — not a new Vision benchmark."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import DECISION_CALL, DECISION_SKIP, ROLE_GAP_EXPLAINED, ROLE_GAP_REQUIRED


def _pct(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{100.0 * float(v):.2f}%"
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
    long_m = m.get("longitudinal") or {}
    p263 = m.get("p263_baseline") or {}
    p262 = m.get("p262_baseline") or {}
    false_skips: List[Dict[str, Any]] = result.get("false_skips") or []
    false_calls: List[Dict[str, Any]] = result.get("false_calls") or []
    diag: List[Dict[str, Any]] = result.get("role_gap_diagnostics") or []
    examples = (result.get("evidence") or {}).get("examples") or []
    decisions = result.get("decisions") or []
    explained = [d for d in decisions if d.get("role_gap_status") == ROLE_GAP_EXPLAINED]
    required = [d for d in decisions if d.get("role_gap_status") == ROLE_GAP_REQUIRED]
    converted = [d for d in explained if d.get("decision") == DECISION_SKIP]
    preserved = [d for d in required if d.get("decision") == DECISION_CALL]

    md = [
        "# P2.6.4 — Selective XOR / Role-Gap Refinement Status",
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
        "P2.6.1 ungated: candidates 207, precision 73.91%, unsupported 6.28%, TRUE_RECOVERIES 26.",
        "",
        "P2.6.2 V1.1:",
        f"- CALL {p262.get('CALL_BEAMS')} SKIP {p262.get('SKIP_BEAMS')} reduction {_pct(p262.get('CALL_REDUCTION'))} "
        f"retention {_pct(p262.get('RECOVERY_RETENTION_RATE'))} false skips {p262.get('FALSE_SKIPS')}",
        "",
        "------------------------------------------------------------",
        "P2.6.3 COMPARISON",
        "------------------------------------------------------------",
        "",
        f"- CALL {p263.get('CALL_BEAMS')} SKIP {p263.get('SKIP_BEAMS')} HOLD {p263.get('HOLD_BEAMS')}",
        f"- call reduction {_pct(p263.get('CALL_REDUCTION'))}",
        f"- gated candidates {p263.get('GATED_VISION_CANDIDATES')} duplicate {_pct(p263.get('DUPLICATE_RATE_GATED'))}",
        f"- precision {_pct(p263.get('GATED_PRECISION'))} unsupported {_pct(p263.get('GATED_UNSUPPORTED_RATE'))}",
        f"- TRUE_RECOVERIES {p263.get('GATED_TRUE_RECOVERIES')} retention {_pct(p263.get('RECOVERY_RETENTION_RATE'))}",
        f"- false skips {p263.get('FALSE_SKIPS')} false calls {p263.get('FALSE_CALLS')}",
        f"- TR/100 calls {p263.get('TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED')}",
        f"- stirrup {p263.get('STIRRUP_RETAINED')}/18 longitudinal {p263.get('LONGITUDINAL_RETAINED')}/8",
        f"- ROLE_COVERAGE_GAP beams {p263.get('ROLE_COVERAGE_GAP_BEAMS')}",
        "",
        "------------------------------------------------------------",
        "P2.6.4 RESULTS",
        "------------------------------------------------------------",
        "",
        f"- **CALL**: {m.get('CALL_BEAMS')}  **SKIP**: {m.get('SKIP_BEAMS')}  **HOLD**: {m.get('HOLD_BEAMS')}",
        f"- **call reduction**: {_pct(m.get('CALL_REDUCTION'))}",
        f"- **baseline candidates**: {m.get('TOTAL_BASELINE_VISION_CANDIDATES')}",
        f"- **gated candidates**: {m.get('GATED_VISION_CANDIDATES')}",
        f"- **gated duplicate rate**: {_pct(m.get('DUPLICATE_RATE_GATED'))}",
        f"- **gated precision**: {_pct(m.get('GATED_PRECISION'))}",
        f"- **gated unsupported**: {_pct(m.get('GATED_UNSUPPORTED_RATE'))}",
        f"- **gated ambiguous**: {_pct(m.get('GATED_AMBIGUOUS_RATE'))}",
        f"- **TRUE_RECOVERIES**: {m.get('GATED_TRUE_RECOVERIES')}",
        f"- **recovery retention**: {_pct(m.get('RECOVERY_RETENTION_RATE'))}",
        f"- **false skips**: {m.get('FALSE_SKIPS')}",
        f"- **false calls**: {m.get('FALSE_CALLS')}",
        f"- **TRUE_RECOVERIES per 100 calls**: {m.get('TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED')}",
        "",
        "------------------------------------------------------------",
        "LONGITUDINAL RESULTS",
        "------------------------------------------------------------",
        "",
        f"- candidates {long_m.get('baseline_candidates')}→{long_m.get('gated_candidates')}",
        f"- duplicates {long_m.get('baseline_duplicates')}→{long_m.get('gated_duplicates')}",
        f"- TRUE_RECOVERIES {long_m.get('baseline_true_recoveries')}→{long_m.get('gated_true_recoveries')}",
        f"- lost {long_m.get('lost_recoveries')} retention {_pct(m.get('LONGITUDINAL_RECOVERY_RETENTION'))}",
        f"- false skips {long_m.get('false_skips')} false calls {long_m.get('false_calls')}",
        f"- ROLE_COVERAGE_GAP calls P2.6.3={p263.get('ROLE_COVERAGE_GAP_BEAMS')} P2.6.4={m.get('ROLE_COVERAGE_GAP_CALLS')}",
        f"- ROLE_COVERAGE_GAP skips={m.get('ROLE_COVERAGE_GAP_SKIPS')} explained={m.get('ROLE_GAP_EXPLAINED_BEAMS')}",
        f"- ROLE_COVERAGE_GAP duplicate-only calls={m.get('ROLE_COVERAGE_GAP_DUPLICATE_ONLY_CALLS')}",
        "",
        "------------------------------------------------------------",
        "ROLE-GAP DIAGNOSTICS",
        "------------------------------------------------------------",
        "",
        "Runtime uses production-only evidence. Vision outcome columns below are OFFLINE EVALUATION ONLY.",
        "",
        "Rule (ROLE_COVERAGE_GAP only):",
        "- REQUIRES_VISION when unique accepted specs > 1, or repeated accepted instances lack a matching rejected spec, or a single spec has neither extras nor a rejected match.",
        "- EXPLAINED (SKIP) when a single unique spec matches a MAIN object on the populated layer AND (extras exist OR a rejected longitudinal spec is already covered by that layer), unless repeated accepted instances exist without a rejected match.",
        "",
        f"- explained / converted to SKIP: {len(converted)}",
        f"- unresolved / preserved CALL: {len(preserved)}",
        "",
    ]
    md.append("Converted SKIP (deterministic explanation):")
    if not converted:
        md.append("- none")
    for d in converted:
        md.append(
            f"- `{d.get('set_key')}/{d.get('beam_id')}` reason=`{d.get('role_gap_reason')}` "
            f"codes=`{d.get('reason_codes')}`"
        )
    md.append("")
    md.append("Preserved CALL (unresolved role gap):")
    if not preserved:
        md.append("- none")
    for d in preserved:
        md.append(
            f"- `{d.get('set_key')}/{d.get('beam_id')}` reason=`{d.get('role_gap_reason')}`"
        )
    md.append("")
    md.append("Per-beam diagnostic table:")
    for r in diag:
        md.append(
            f"- `{r.get('set_key')}/{r.get('beam_id')}` topQ={r.get('top_quantity')} "
            f"botQ={r.get('bottom_quantity')} topDia={r.get('top_diameters')} "
            f"botDia={r.get('bottom_diameters')} extras={r.get('extra_object_count')} "
            f"unkAnn={r.get('unknown_annotation_count')} knownAnn={r.get('known_role_annotation_count')} "
            f"uniq={r.get('unique_accepted_spec_count')} inst={r.get('accepted_instance_count')} "
            f"qtySF={r.get('quantity_shortfall_count')} roleC={r.get('role_conflict_count')} "
            f"diaC={r.get('diameter_conflict_count')} assoc={r.get('association')} "
            f"p263=`{r.get('p263_decision')}` p264=`{r.get('gate_decision')}` "
            f"status=`{r.get('role_gap_status')}`/{r.get('role_gap_reason')} "
            f"vis={r.get('p263_recovery_status')} dupOnly={r.get('vision_duplicate_only')}"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "STIRRUP REGRESSION",
        "------------------------------------------------------------",
        "",
        f"- baseline TRUE_RECOVERIES: {m.get('STIRRUP_BASELINE_TRUE_RECOVERIES')}",
        f"- gated TRUE_RECOVERIES: {m.get('STIRRUP_GATED_TRUE_RECOVERIES')}",
        f"- retention: {_pct(m.get('STIRRUP_RECOVERY_RETENTION'))}",
        "- expected: 18/18",
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
            f"coverage=`{fs.get('production_coverage')}` rg=`{fs.get('role_gap_status')}` "
            f"reasons=`{fs.get('why_gate_skipped')}`"
        )
    md += ["", "------------------------------------------------------------", "FALSE CALLS", "------------------------------------------------------------", ""]
    if not false_calls:
        md.append("- none")
    for fc in false_calls:
        md.append(
            f"- `{fc.get('set_key')}/{fc.get('beam_id')}` reasons=`{fc.get('reason_codes')}` "
            f"coverage=`{fc.get('production_coverage')}` rg=`{fc.get('role_gap_status')}` "
            f"cands={fc.get('candidate_count')}"
        )
    md += ["", "------------------------------------------------------------", "VISUAL EVIDENCE", "------------------------------------------------------------", ""]
    if not examples:
        md.append("- none")
    for ex in examples:
        md.append(
            f"- `{ex.get('example_class')}`: `{ex.get('set_key')}/{ex.get('beam_id')}` "
            f"gate=`{ex.get('gate_decision')}`"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "SAFETY",
        "------------------------------------------------------------",
        "",
        f"- production mutation = {prod.get('production_mutation_count', 0)}",
        f"- fingerprints ok: `{prod.get('fingerprints_ok')}`",
        f"- P2.6.3 artefacts unchanged: `{prod.get('p263_artefacts_unchanged')}`",
        f"- firewall ok: `{fw.get('ok')}`",
        f"- leakage ok: `{leak.get('ok')}`",
        f"- live Vision: {result.get('live_cost_usd', 'not run')}",
        f"- engineering mutation: {result.get('engineering_changes')}",
        "- GT_USED_FOR_GATE = FALSE",
        "- estimator_used_for_gate = FALSE",
        "- stratum_used_for_gate = FALSE",
        "",
        "------------------------------------------------------------",
        "DECISION",
        "------------------------------------------------------------",
        "",
        "1. Deterministic role-gap signal: extras on the populated layer and/or a rejected longitudinal spec already covered by that layer, with a single unique accepted spec matching a MAIN object.",
        f"2. Calls converted to SKIP: {len(converted)} ROLE_COVERAGE_GAP beams.",
        f"3. Calls preserved: {len(preserved)} unresolved ROLE_COVERAGE_GAP beams (including genuine missing opposite-layer recoveries).",
        f"4. True recoveries lost vs P2.6.1: {m.get('RECOVERIES_LOST')}.",
        "5. B136-class FULLY_COVERED false skip is unchanged: the FULLY_COVERED path is frozen; ROLE_COVERAGE_GAP refinement cannot apply.",
        f"6. ROLE_COVERAGE_GAP duplicate-only CALL count: {m.get('ROLE_COVERAGE_GAP_DUPLICATE_ONLY_CALLS')}.",
        f"7. Precision P2.6.3 {_pct(p263.get('GATED_PRECISION'))} → P2.6.4 {_pct(m.get('GATED_PRECISION'))}.",
        f"8. Unsupported P2.6.3 {_pct(p263.get('GATED_UNSUPPORTED_RATE'))} → P2.6.4 {_pct(m.get('GATED_UNSUPPORTED_RATE'))}.",
        f"9. TR/100 calls P2.6.3 {p263.get('TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED')} → P2.6.4 {m.get('TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED')}.",
        f"10. Final decision is `{rec.get('decision')}` because: {rec.get('note')}",
        "",
        f"- **STRENGTH**: {rec.get('strength')}",
        f"- **DECISION**: {rec.get('decision')}",
        "",
        "Allowed: READY_FOR_ENGINEERING_RECOMPUTE_PILOT | REFINE_LONGITUDINAL_GATE.",
        "NEVER: PRODUCTION_READY.",
        "",
    ]
    status_path = out_root / "P2.6.4_STATUS.md"
    text = "\n".join(md) + "\n"
    status_path.write_text(text, encoding="utf-8")
    (reports / "P2.6.4_STATUS.md").write_text(text, encoding="utf-8")
    (reports / "metrics.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    (reports / "longitudinal_metrics.json").write_text(
        json.dumps(long_m, indent=2, default=str), encoding="utf-8"
    )
    (reports / "role_gap_diagnostics.json").write_text(
        json.dumps(diag, indent=2, default=str), encoding="utf-8"
    )
    (reports / "false_skips.json").write_text(json.dumps(false_skips, indent=2, default=str), encoding="utf-8")
    (reports / "false_calls.json").write_text(json.dumps(false_calls, indent=2, default=str), encoding="utf-8")
    (reports / "unit_tests.json").write_text(json.dumps(tests, indent=2, default=str), encoding="utf-8")
    (reports / "firewall.json").write_text(
        json.dumps({"firewall": fw, "production": prod}, indent=2, default=str), encoding="utf-8"
    )
    (reports / "leakage.json").write_text(json.dumps(leak, indent=2, default=str), encoding="utf-8")
    coverage_diag = {
        "role_gap_explained": [
            {"set_key": d.get("set_key"), "beam_id": d.get("beam_id"), "reason": d.get("role_gap_reason")}
            for d in converted
        ],
        "role_gap_required": [
            {"set_key": d.get("set_key"), "beam_id": d.get("beam_id"), "reason": d.get("role_gap_reason")}
            for d in preserved
        ],
        "diagnostics": diag,
    }
    (reports / "coverage_diagnostics.json").write_text(
        json.dumps(coverage_diag, indent=2, default=str), encoding="utf-8"
    )
    return {"status": str(status_path), "metrics": str(reports / "metrics.json")}


__all__ = ["write_reports"]
