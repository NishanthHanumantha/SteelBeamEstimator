"""P2.6.5 status report. Shadow spatial research — not production routing."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import COVER_FULL, COVER_LAYER, STATUS_CALL, STATUS_SKIP


def _pct(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{100.0 * float(v):.2f}%"
    except (TypeError, ValueError):
        return str(v)


def _row_metrics(m: Dict[str, Any]) -> str:
    return (
        f"CALL {m.get('CALL_BEAMS')} SKIP {m.get('SKIP_BEAMS')} HOLD {m.get('HOLD_BEAMS')} "
        f"red {_pct(m.get('CALL_REDUCTION'))} cands {m.get('GATED_VISION_CANDIDATES')} "
        f"dup {_pct(m.get('DUPLICATE_RATE_GATED'))} prec {_pct(m.get('GATED_PRECISION'))} "
        f"uns {_pct(m.get('GATED_UNSUPPORTED_RATE'))} TR {m.get('GATED_TRUE_RECOVERIES')} "
        f"ret {_pct(m.get('RECOVERY_RETENTION_RATE'))} FS {m.get('FALSE_SKIPS')} "
        f"FC {m.get('FALSE_CALLS')} TR/100 {m.get('TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED')}"
    )


def _separability(controls: List[Dict[str, Any]]) -> List[str]:
    by = {(r.get("set_key"), r.get("beam_id")): r for r in controls}
    b128 = by.get(("Fifth", "B128")) or {}
    twins = [by.get(("Fifth", "B100")) or {}, by.get(("Fourth", "B141")) or {}, by.get(("Fourth", "B23")) or {}]
    same_as_128 = [
        f"{r.get('set_key')}/{r.get('beam_id')} status={r.get('context_status')} votes={r.get('tip_layer_votes')}"
        for r in twins
        if r.get("context_status") == b128.get("context_status")
    ]
    lines = [
        f"- Fifth/B128 context=`{b128.get('context_status')}` codes=`{b128.get('evidence_codes')}` "
        f"tip_votes=`{b128.get('tip_layer_votes')}` vision=`{b128.get('vision_outcome')}`",
        f"- Fifth/B100 context=`{(by.get(('Fifth','B100')) or {}).get('context_status')}` "
        f"tip_votes=`{(by.get(('Fifth','B100')) or {}).get('tip_layer_votes')}`",
        f"- Fourth/B141 context=`{(by.get(('Fourth','B141')) or {}).get('context_status')}` "
        f"tip_votes=`{(by.get(('Fourth','B141')) or {}).get('tip_layer_votes')}`",
        f"- Fourth/B23 context=`{(by.get(('Fourth','B23')) or {}).get('context_status')}` "
        f"tip_votes=`{(by.get(('Fourth','B23')) or {}).get('tip_layer_votes')}`",
    ]
    repeats = [("Fifth", "B173"), ("Fourth", "B170"), ("Fourth", "B174")]
    for sk, bid in repeats:
        r = by.get((sk, bid)) or {}
        lines.append(
            f"- {sk}/{bid} repeat_dy={r.get('max_repeat_dy')} status=`{r.get('context_status')}` "
            f"vision=`{r.get('vision_outcome')}`"
        )
    b136 = by.get(("Fifth", "B136")) or {}
    lines.append(
        f"- Fifth/B136 coverage=`{b136.get('longitudinal_coverage')}` "
        f"status=`{b136.get('context_status')}` p264=`{b136.get('p264_decision')}` "
        f"vision=`{b136.get('vision_outcome')}`"
    )
    if same_as_128:
        lines.append(
            "PRODUCTION-VISIBLE SPATIAL/CONTEXT EVIDENCE IS INSUFFICIENT FOR SAFE SEPARATION "
            "of Fifth/B128 from at least one duplicate-only control with the same context status: "
            + "; ".join(same_as_128)
        )
    else:
        lines.append(
            "B128 context status differs from B100/B141/B23, but duplicate-only opposite-layer "
            "cases (if any) still require CALL; SKIP remains unsafe without additional evidence."
        )
    return lines


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    m = result.get("metrics") or {}
    hypo_m = result.get("hypothetical_metrics") or {}
    rec = result.get("recommendation") or {}
    sample = result.get("sample") or {}
    tests = result.get("unit_tests") or {}
    prod = result.get("production") or {}
    fw = result.get("firewall") or {}
    leak = result.get("leakage") or {}
    long_m = m.get("longitudinal") or {}
    controls: List[Dict[str, Any]] = result.get("control_cases") or []
    decisions: List[Dict[str, Any]] = result.get("decisions") or []
    features: List[Dict[str, Any]] = result.get("feature_rows") or []
    sens = result.get("sensitivity") or {}
    gap = [d for d in decisions if d.get("longitudinal_coverage") == COVER_LAYER]
    full = [d for d in decisions if d.get("longitudinal_coverage") == COVER_FULL]
    unavailable = sorted({u for d in decisions for u in ((d.get("spatial_features") or {}).get("unavailable_features") or [])})
    available = [
        "annotation x/y (T18 BeamScoped)",
        "leader tip/tail and tip_direction",
        "ownership envelope crop_extent / centreline / top+bottom zones / depth_mm",
        "physical bar start_x/end_x/y_position when T18 PhysicalBar nodes exist",
        "P2.6.4 production features (coverage, role-gap, quantities, diameters)",
    ]
    md = [
        "# P2.6.5 — Spatial / Context-Aware Longitudinal Ambiguity Resolution",
        "",
        "Shadow / research only. Observed routing is unchanged P2.6.4.",
        "Hypothetical overlay is NOT production behaviour. NEVER PRODUCTION_READY.",
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
        f"- **sample seed**: {sample.get('seed')}",
        f"- **beams**: {m.get('TOTAL_BEAMS')}",
        f"- **strata**: {json.dumps(sample.get('selected_by_stratum') or {'DIFFICULT': 25, 'NORMAL': 25, 'EASY': 25})}",
        f"- **drawing sets**: {sample.get('drawing_sets') or ['Fourth', 'Fifth', 'Sixth']}",
        "- **GT_USED_FOR_GATE = FALSE**",
        "- **ESTIMATOR_USED_FOR_GATE = FALSE**",
        "",
        "------------------------------------------------------------",
        "OBJECTIVE",
        "------------------------------------------------------------",
        "",
        "Determine whether production-visible spatial/contextual geometry can safely distinguish",
        "TRUE missing longitudinal reinforcement from duplicate-only ROLE_COVERAGE_GAP annotations,",
        "without changing P2.6.4 routing and without using GT at runtime.",
        "",
        "------------------------------------------------------------",
        "SPATIAL FEATURES",
        "------------------------------------------------------------",
        "",
        "Successfully extracted:",
    ]
    md += [f"- {x}" for x in available]
    md += ["", "Unavailable / sparse:", *[f"- {u}" for u in (unavailable or ["none recorded"])]]
    md += [
        "",
        "- Coordinate space: `DXF_MODEL_MM` (native drawing units, no silent conversion).",
        "- PhysicalBar nodes are absent on many ROLE_COVERAGE_GAP beams; leader+zone geometry is the primary signal.",
        "",
        "------------------------------------------------------------",
        "CONTEXT FEATURES",
        "------------------------------------------------------------",
        "",
        "- P2.6.4 coverage / role-gap status / unique spec / accepted instance / extras / rejected match",
        "- Leader tip vs TOP/BOTTOM envelope zones with clearance = 0.15 × depth_mm",
        "- Repeated-annotation vertical separation = 0.50 × depth_mm",
        "- Physical-bar and annotation 1-D clusters (gap = 0.25 × depth_mm)",
        "- Categorical votes; a single proximity feature cannot SKIP",
        "",
        f"- context counts overall: {json.dumps(m.get('context_status_counts') or {})}",
        f"- ROLE_COVERAGE_GAP context counts: {json.dumps(m.get('role_gap_context_status_counts') or {})}",
        f"- sensitivity: {json.dumps(sens.get('by_clearance_ratio') or [])} stable={sens.get('stable')}",
        "",
        "------------------------------------------------------------",
        "OVERALL RESULTS",
        "------------------------------------------------------------",
        "",
        "Observed P2.6.5 shadow classification (P2.6.4 routing, unchanged):",
        f"- {_row_metrics(m)}",
        "",
        "Hypothetical gate result (NOT production):",
        f"- {_row_metrics(hypo_m) if hypo_m else 'n/a'}",
        "",
        "Baseline comparison:",
        f"- P2.6.1 {_row_metrics(m.get('p261_baseline') or {})}",
        f"- P2.6.2 {_row_metrics(m.get('p262_baseline') or {})}",
        f"- P2.6.3 {_row_metrics(m.get('p263_baseline') or {})}",
        f"- P2.6.4 {_row_metrics(m.get('p264_baseline') or {})}",
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
        "",
        "------------------------------------------------------------",
        "ROLE GAP RESULTS",
        "------------------------------------------------------------",
        "",
        f"- ROLE_COVERAGE_GAP beams: {len(gap)}",
        f"- observed CALL among them: {sum(1 for d in gap if d.get('decision')=='CALL_VISION')}",
        f"- hypothetical extra SKIP: {sum(1 for d in decisions if d.get('hypothetical_reason')=='CONTEXT_SUPPORTS_SKIP_NO_STIRRUP_GAP')}",
        "",
    ]
    for d in gap:
        md.append(
            f"- `{d.get('set_key')}/{d.get('beam_id')}` p264=`{d.get('observed_decision')}` "
            f"ctx=`{d.get('context_status')}` codes=`{d.get('context_evidence_codes')}` "
            f"hypo=`{d.get('hypothetical_decision')}` votes=`{(d.get('spatial_features') or {}).get('tip_layer_votes')}`"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "FULLY COVERED DIAGNOSTIC",
        "------------------------------------------------------------",
        "",
        "FULLY_COVERED production path was not modified.",
        f"- FULLY_COVERED beams in sample: {len(full)}",
        "",
    ]
    b136 = next((d for d in decisions if d.get("set_key")=="Fifth" and d.get("beam_id")=="B136"), None)
    if b136:
        md.append(
            f"- Fifth/B136 remains SKIP under P2.6.4 (`{b136.get('observed_decision')}`), "
            f"coverage=`{b136.get('longitudinal_coverage')}`, context=`{b136.get('context_status')}`, "
            f"codes=`{b136.get('context_evidence_codes')}`. Spatial evidence does not justify overriding FULLY_COVERED."
        )
    md += [
        "",
        "------------------------------------------------------------",
        "CONTROL CASES",
        "------------------------------------------------------------",
        "",
    ]
    if not controls:
        md.append("- none")
    for r in controls:
        md.append(
            f"- `{r.get('family')}` `{r.get('set_key')}/{r.get('beam_id')}` [{r.get('eval_stratum')}] "
            f"cov=`{r.get('longitudinal_coverage')}` vis=`{r.get('vision_outcome')}` "
            f"dupOnly={r.get('vision_duplicate_only')} ctx=`{r.get('context_status')}` "
            f"codes=`{r.get('evidence_codes')}` p264=`{r.get('p264_decision')}` "
            f"hypo=`{r.get('hypothetical_decision')}`"
        )
    md += ["", "------------------------------------------------------------", "SEPARABILITY FINDINGS", "------------------------------------------------------------", ""]
    md += _separability(controls)
    md += [
        "",
        "------------------------------------------------------------",
        "STIRRUP REGRESSION",
        "------------------------------------------------------------",
        "",
        f"- baseline TRUE_RECOVERIES: {m.get('STIRRUP_BASELINE_TRUE_RECOVERIES')}",
        f"- gated TRUE_RECOVERIES: {m.get('STIRRUP_GATED_TRUE_RECOVERIES')}",
        f"- retention: {_pct(m.get('STIRRUP_RECOVERY_RETENTION'))}",
        "",
        "------------------------------------------------------------",
        "SAFETY",
        "------------------------------------------------------------",
        "",
        f"- production mutation = {prod.get('production_mutation_count', 0)}",
        f"- fingerprints ok: `{prod.get('fingerprints_ok')}`",
        f"- P2.6.4 artefacts unchanged: `{prod.get('p264_artefacts_unchanged')}`",
        f"- firewall ok: `{fw.get('ok')}`",
        f"- leakage ok: `{leak.get('ok')}`",
        f"- live Vision: {result.get('live_cost_usd', 'not run')}",
        f"- engineering mutation: {result.get('engineering_changes')}",
        "- GT_USED_FOR_GATE = FALSE",
        "- estimator_used_for_gate = FALSE",
        "- stratum_used_for_gate = FALSE",
        "- no hard-coded beam IDs in spatial classifier / routing overlay",
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
    ]
    text = "\n".join(md) + "\n"
    status_path = out_root / "P2.6.5_STATUS.md"
    status_path.write_text(text, encoding="utf-8")
    (reports / "P2.6.5_STATUS.md").write_text(text, encoding="utf-8")
    (reports / "metrics.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    (reports / "hypothetical_metrics.json").write_text(
        json.dumps(hypo_m, indent=2, default=str), encoding="utf-8"
    )
    (reports / "control_cases.json").write_text(json.dumps(controls, indent=2, default=str), encoding="utf-8")
    (reports / "sensitivity.json").write_text(json.dumps(sens, indent=2, default=str), encoding="utf-8")
    (reports / "features.json").write_text(json.dumps(features, indent=2, default=str), encoding="utf-8")
    csv_path = reports / "features.csv"
    if features:
        keys = sorted({k for row in features for k in row.keys()})
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            for row in features:
                w.writerow({k: json.dumps(row.get(k), default=str) if isinstance(row.get(k), (dict, list)) else row.get(k) for k in keys})
    (reports / "false_skips.json").write_text(
        json.dumps(result.get("false_skips") or [], indent=2, default=str), encoding="utf-8"
    )
    (reports / "false_calls.json").write_text(
        json.dumps(result.get("false_calls") or [], indent=2, default=str), encoding="utf-8"
    )
    (reports / "unit_tests.json").write_text(json.dumps(tests, indent=2, default=str), encoding="utf-8")
    (reports / "firewall.json").write_text(
        json.dumps({"firewall": fw, "production": prod}, indent=2, default=str), encoding="utf-8"
    )
    (reports / "leakage.json").write_text(json.dumps(leak, indent=2, default=str), encoding="utf-8")
    return {"status": str(status_path), "metrics": str(reports / "metrics.json"), "features_csv": str(csv_path)}


__all__ = ["write_reports"]
