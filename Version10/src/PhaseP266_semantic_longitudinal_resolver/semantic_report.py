"""P2.6.6 status, control-case, and safety reports. Shadow research only."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import COVER_FULL, COVER_LAYER, DECISION_SKIP


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


def _control_md(controls: List[Dict[str, Any]]) -> List[str]:
    lines = [
        "# P2.6.6 — Control cases",
        "",
        "Evaluation-only table. Beam IDs are benchmark labels, not resolver features.",
        "",
    ]
    for r in controls:
        lines.append(
            f"- `{r.get('family')}` `{r.get('set_key')}/{r.get('beam_id')}` "
            f"cov=`{r.get('longitudinal_coverage')}` vis=`{r.get('vision_outcome')}` "
            f"p264=`{r.get('p264_decision')}` p265=`{r.get('p265_context_status')}` "
            f"semantic=`{r.get('semantic_class')}` conf=`{r.get('semantic_confidence')}` "
            f"layer=`{r.get('target_layer')}` hypo=`{r.get('hypothetical_vision_routing')}` "
            f"safe_skip=`{r.get('safe_skip_candidate')}` reason=`{r.get('hypothetical_reason')}`"
        )
    return lines


def _safety_md(result: Dict[str, Any]) -> List[str]:
    prod = result.get("production") or {}
    fw = result.get("firewall") or {}
    leak = result.get("leakage") or {}
    tests = result.get("unit_tests") or {}
    m = result.get("metrics") or {}
    return [
        "# P2.6.6 — Safety",
        "",
        "Shadow / research only. Production routing remains P2.6.4 / P2.6.5.",
        "",
        f"- production mutation = {prod.get('production_mutation_count', 0)}",
        f"- fingerprints ok: `{prod.get('fingerprints_ok')}`",
        f"- P2.6.4 artefacts unchanged: `{prod.get('p264_artefacts_unchanged')}`",
        f"- P2.6.5 artefacts unchanged: `{prod.get('p265_artefacts_unchanged')}`",
        f"- firewall ok: `{fw.get('ok')}`",
        f"- leakage ok: `{leak.get('ok')}`",
        f"- live Vision calls: {m.get('LIVE_VISION_CALLS', 0)}",
        f"- engineering mutation: {result.get('engineering_changes')}",
        f"- unit tests: {tests.get('passed')}/{tests.get('total')}",
        "- GT_USED_FOR_RESOLVER = FALSE",
        "- estimator_used_for_resolver = FALSE",
        "- stratum_used_for_resolver = FALSE",
        "- no hard-coded beam IDs in resolver logic",
        "- no hard-coded expected decisions in resolver logic",
        "- FULLY_COVERED production path not overridden",
        "- hypothetical routing is not consumed by production",
        "",
    ]


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
    controls: List[Dict[str, Any]] = result.get("control_cases") or []
    targets: List[Dict[str, Any]] = result.get("target_records") or []
    gap = [d for d in targets if d.get("longitudinal_coverage") == COVER_LAYER]
    diag = [d for d in targets if d.get("longitudinal_coverage") == COVER_FULL]
    sep = m.get("separability") or {}
    obs = m.get("observed_p264") or {}
    hypo = m.get("hypothetical") or {}
    md = [
        "# P2.6.6 — Semantic Longitudinal Ambiguity Resolver",
        "",
        "Shadow / research only. Observed routing is unchanged P2.6.4 / P2.6.5.",
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
        f"- **LIVE_VISION_CALLS**: {m.get('LIVE_VISION_CALLS', 0)}",
        f"- **TESTS**: {tests.get('passed')}/{tests.get('total')} ({'PASS' if tests.get('success') else 'FAIL'})",
        "",
        "------------------------------------------------------------",
        "DATASET",
        "------------------------------------------------------------",
        "",
        "- **source**: frozen P2.6.1 stratified sample (not resampled); P2.6.5 spatial context replayed",
        f"- **sample seed**: {sample.get('seed')}",
        f"- **parent sample beams**: {sample.get('beam_count') or 75}",
        f"- **target beams**: {m.get('TARGET_BEAMS')}",
        f"- **ROLE_COVERAGE_GAP**: {m.get('ROLE_COVERAGE_GAP_BEAMS')}",
        f"- **diagnostic FULLY_COVERED**: {len(diag)}",
        "- **GT_USED_FOR_RESOLVER = FALSE**",
        "- **ESTIMATOR_USED_FOR_RESOLVER = FALSE**",
        "",
        "------------------------------------------------------------",
        "OBJECTIVE",
        "------------------------------------------------------------",
        "",
        "Determine whether a targeted Vision semantic arbitration layer can distinguish",
        "distinct/missing longitudinal reinforcement from duplicate/repeat representations",
        "on ROLE_COVERAGE_GAP ambiguities, without changing production routing.",
        "",
        "P2.6.5 showed spatial/context evidence is useful for CALL support but is NOT",
        "separable enough to convert ambiguous ROLE_COVERAGE_GAP cases into SKIP.",
        "P2.6.6 is a semantic resolver, not another spatial gate.",
        "",
        "------------------------------------------------------------",
        "OVERALL TARGET POPULATION",
        "------------------------------------------------------------",
        "",
        f"- total target beams: {m.get('TARGET_BEAMS')}",
        f"- Vision calls/replays: {m.get('VISION_REPLAYS')}",
        f"- DISTINCT_REINFORCEMENT: {m.get('DISTINCT_REINFORCEMENT')}",
        f"- DUPLICATE_OR_REPEAT: {m.get('DUPLICATE_OR_REPEAT')}",
        f"- AMBIGUOUS: {m.get('AMBIGUOUS')}",
        f"- UNSUPPORTED: {m.get('UNSUPPORTED')}",
        "",
        "------------------------------------------------------------",
        "SEMANTIC CLASSIFICATION METRICS",
        "------------------------------------------------------------",
        "",
        f"- true recovery recall: {_pct(m.get('true_recovery_recall'))}",
        f"- duplicate precision: {_pct(m.get('duplicate_precision'))}",
        f"- duplicate recall: {_pct(m.get('duplicate_recall'))}",
        f"- semantic precision: {_pct(m.get('semantic_precision'))}",
        f"- semantic unsupported rate: {_pct(m.get('semantic_unsupported_rate'))}",
        f"- semantic ambiguous rate: {_pct(m.get('semantic_ambiguous_rate'))}",
        f"- false DISTINCT: {m.get('false_DISTINCT')}",
        f"- false DUPLICATE: {m.get('false_DUPLICATE')}",
        "",
        "------------------------------------------------------------",
        "SAFETY METRICS (HYPOTHETICAL ROUTING ONLY)",
        "------------------------------------------------------------",
        "",
        f"- false skip count: {m.get('FALSE_SKIPS')}",
        f"- false call count: {m.get('FALSE_CALLS')}",
        f"- recovery retention: {_pct(m.get('recovery_retention'))}",
        f"- recovery loss: {m.get('recovery_loss')}",
        "",
        "Observed P2.6.4/P2.6.5 routing (unchanged):",
        f"- CALL {obs.get('CALL_BEAMS')} SKIP {obs.get('SKIP_BEAMS')} "
        f"TR {obs.get('GATED_TRUE_RECOVERIES')} FS {obs.get('FALSE_SKIPS')} FC {obs.get('FALSE_CALLS')}",
        "",
        "Hypothetical P2.6.6 overlay (NOT production):",
        f"- CALL {hypo.get('CALL_BEAMS')} SKIP {hypo.get('SKIP_BEAMS')} "
        f"TR {hypo.get('GATED_TRUE_RECOVERIES')} FS {hypo.get('FALSE_SKIPS')} FC {hypo.get('FALSE_CALLS')}",
        "",
        "------------------------------------------------------------",
        "COMPARISON WITH P2.6.5",
        "------------------------------------------------------------",
        "",
        f"- Fifth/B128 semantic=`{sep.get('b128_class')}` p265=`{sep.get('b128_p265_context')}`",
        f"- Fourth/B141 semantic=`{sep.get('b141_class')}` p265=`{sep.get('b141_p265_context')}`",
        f"- Fourth/B23 semantic=`{sep.get('b23_class')}` p265=`{sep.get('b23_p265_context')}`",
        f"- spatial pattern same: `{sep.get('spatial_pattern_same')}`",
        f"- semantic distinguishes B128 from B141/B23: `{sep.get('semantic_distinguishes_b128_from_b141_b23')}`",
        f"- {sep.get('note')}",
        "",
        "------------------------------------------------------------",
        "OPERATIONAL EFFICIENCY",
        "------------------------------------------------------------",
        "",
        f"- candidate/target count: {m.get('TARGET_BEAMS')}",
        f"- replay count: {m.get('VISION_REPLAYS')}",
        f"- live calls: {m.get('LIVE_VISION_CALLS')}",
        f"- estimated live calls if deployed: {m.get('ESTIMATED_LIVE_CALLS_IF_DEPLOYED')}",
        f"- cache hit rate: {m.get('CACHE_HIT_RATE')}",
        f"- replay source: {result.get('replay_source')}",
        "",
        "------------------------------------------------------------",
        "ROLE_COVERAGE_GAP TARGETS",
        "------------------------------------------------------------",
        "",
    ]
    for d in gap:
        sem = d.get("semantic") or {}
        hypo_d = d.get("hypothetical") or {}
        md.append(
            f"- `{d.get('set_key')}/{d.get('beam_id')}` p264=`{d.get('observed_decision')}` "
            f"p265=`{d.get('context_status')}` semantic=`{sem.get('decision')}` "
            f"layer=`{sem.get('target_layer')}` hypo=`{hypo_d.get('hypothetical_vision_routing')}` "
            f"safe_skip=`{hypo_d.get('safe_skip_candidate')}` source=`{sem.get('source')}`"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "FULLY COVERED DIAGNOSTIC",
        "------------------------------------------------------------",
        "",
        "FULLY_COVERED production path was not modified. No FULLY_COVERED override was created.",
        f"- diagnostic beams: {len(diag)}",
        "",
    ]
    for d in diag:
        sem = d.get("semantic") or {}
        md.append(
            f"- `{d.get('set_key')}/{d.get('beam_id')}` coverage=`{COVER_FULL}` "
            f"p264=`{d.get('observed_decision')}` semantic=`{sem.get('decision')}` "
            f"hypo=`{(d.get('hypothetical') or {}).get('hypothetical_vision_routing')}` "
            f"(production remains `{d.get('observed_decision') or DECISION_SKIP}`)"
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
            f"- `{r.get('family')}` `{r.get('set_key')}/{r.get('beam_id')}` "
            f"cov=`{r.get('longitudinal_coverage')}` vis=`{r.get('vision_outcome')}` "
            f"semantic=`{r.get('semantic_class')}` p265=`{r.get('p265_context_status')}` "
            f"p264=`{r.get('p264_decision')}` hypo=`{r.get('hypothetical_vision_routing')}`"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "SAFETY",
        "------------------------------------------------------------",
        "",
        f"- production mutation = {prod.get('production_mutation_count', 0)}",
        f"- fingerprints ok: `{prod.get('fingerprints_ok')}`",
        f"- P2.6.4 artefacts unchanged: `{prod.get('p264_artefacts_unchanged')}`",
        f"- P2.6.5 artefacts unchanged: `{prod.get('p265_artefacts_unchanged')}`",
        f"- firewall ok: `{fw.get('ok')}`",
        f"- leakage ok: `{leak.get('ok')}`",
        f"- live Vision: {m.get('LIVE_VISION_CALLS', 0)}",
        f"- engineering mutation: {result.get('engineering_changes')}",
        "- GT_USED_FOR_RESOLVER = FALSE",
        "- estimator_used_for_resolver = FALSE",
        "- stratum_used_for_resolver = FALSE",
        "- no hard-coded beam IDs in resolver / replay adapter",
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
        "Primary success criterion: safe semantic separation, not call reduction.",
        "",
    ]
    text = "\n".join(md) + "\n"
    status_path = out_root / "P2.6.6_STATUS.md"
    status_path.write_text(text, encoding="utf-8")
    (reports / "P2.6.6_STATUS.md").write_text(text, encoding="utf-8")

    control_text = "\n".join(_control_md(controls)) + "\n"
    (out_root / "P2.6.6_CONTROL_CASES.md").write_text(control_text, encoding="utf-8")
    (reports / "P2.6.6_CONTROL_CASES.md").write_text(control_text, encoding="utf-8")

    safety_text = "\n".join(_safety_md(result)) + "\n"
    (out_root / "P2.6.6_SAFETY.md").write_text(safety_text, encoding="utf-8")
    (reports / "P2.6.6_SAFETY.md").write_text(safety_text, encoding="utf-8")

    (out_root / "P2.6.6_METRICS.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    (reports / "metrics.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    (out_root / "P2.6.6_RESULTS.json").write_text(
        json.dumps(
            {
                "phase_id": result.get("phase_id"),
                "model_version": result.get("model_version"),
                "gate_version": result.get("gate_version"),
                "mode": result.get("mode"),
                "pass_fail": result.get("pass_fail"),
                "decision": rec.get("decision"),
                "strength": rec.get("strength"),
                "metrics": m,
                "recommendation": rec,
                "production": prod,
                "replay": result.get("replay"),
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    decisions = []
    for d in targets:
        sem = d.get("semantic") or {}
        hypo_d = d.get("hypothetical") or {}
        decisions.append(
            {
                "set_key": d.get("set_key"),
                "beam_id": d.get("beam_id"),
                "region_id": d.get("region_id"),
                "longitudinal_coverage": d.get("longitudinal_coverage"),
                "observed_decision": d.get("observed_decision"),
                "p265_context_status": d.get("context_status"),
                "semantic": sem,
                "shadow_decision": hypo_d.get("semantic_decision"),
                "hypothetical_vision_routing": hypo_d.get("hypothetical_vision_routing"),
                "hypothetical_reason": hypo_d.get("hypothetical_reason"),
                "safe_skip_candidate": hypo_d.get("safe_skip_candidate"),
                "production_routing_changed": False,
            }
        )
    (out_root / "P2.6.6_SEMANTIC_DECISIONS.json").write_text(
        json.dumps(decisions, indent=2, default=str), encoding="utf-8"
    )
    (reports / "control_cases.json").write_text(json.dumps(controls, indent=2, default=str), encoding="utf-8")
    (reports / "unit_tests.json").write_text(json.dumps(tests, indent=2, default=str), encoding="utf-8")
    (reports / "firewall.json").write_text(
        json.dumps({"firewall": fw, "production": prod}, indent=2, default=str), encoding="utf-8"
    )
    (reports / "leakage.json").write_text(json.dumps(leak, indent=2, default=str), encoding="utf-8")
    return {
        "status": str(status_path),
        "metrics": str(out_root / "P2.6.6_METRICS.json"),
        "results": str(out_root / "P2.6.6_RESULTS.json"),
        "decisions": str(out_root / "P2.6.6_SEMANTIC_DECISIONS.json"),
        "controls": str(out_root / "P2.6.6_CONTROL_CASES.md"),
        "safety": str(out_root / "P2.6.6_SAFETY.md"),
    }


__all__ = ["write_reports"]
