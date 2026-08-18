"""P2.6.7 reports. Shadow live benchmark — not production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import COVER_FULL, COVER_LAYER, DECISION_SKIP
from .live_prompt import prompt_document


def _pct(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{100.0 * float(v):.2f}%"
    except (TypeError, ValueError):
        return str(v)


def _dec(obs: Any) -> str:
    if not isinstance(obs, dict) or not obs.get("ok"):
        return f"FAILED:{(obs or {}).get('error_class') or (obs or {}).get('error') or 'n/a'}"
    return str(((obs.get("payload") or {}).get("decision")) or "n/a")


def _conf(obs: Any) -> Any:
    if not isinstance(obs, dict) or not obs.get("ok"):
        return None
    return (obs.get("payload") or {}).get("confidence")


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    m = result.get("metrics") or {}
    acc = m.get("accuracy") or {}
    rep = m.get("repeatability") or {}
    crit = m.get("critical") or {}
    rec = result.get("recommendation") or {}
    tests = result.get("unit_tests") or {}
    prod = result.get("production") or {}
    fw = result.get("firewall") or {}
    leak = result.get("leakage") or {}
    records: List[Dict[str, Any]] = result.get("records") or []
    cases = crit.get("cases") or {}
    b128 = cases.get("Fifth/B128") or {}
    b141 = cases.get("Fourth/B141") or {}
    b23 = cases.get("Fourth/B23") or {}

    status = [
        "# P2.6.7 — Live Semantic Arbitration Benchmark & Repeatability Test",
        "",
        "Shadow / research only. Observed production routing remains P2.6.4 / P2.6.5.",
        "NEVER PRODUCTION_READY. No DUPLICATE→SKIP rule. No FULLY_COVERED override.",
        "",
        "------------------------------------------------------------",
        "IDENTITY",
        "------------------------------------------------------------",
        "",
        f"- **MODEL_VERSION**: {result.get('model_version')}",
        f"- **PHASE**: {result.get('phase_id')} {result.get('phase_name')}",
        f"- **GATE_VERSION**: {result.get('gate_version')}",
        f"- **STATUS**: Shadow / research only. NEVER PRODUCTION_READY.",
        f"- **MODE**: {result.get('mode')}",
        f"- **PASS/FAIL**: {result.get('pass_fail')}",
        f"- **TESTS**: {tests.get('passed')}/{tests.get('total')} ({'PASS' if tests.get('success') else 'FAIL'})",
        "",
        "------------------------------------------------------------",
        "OBJECTIVE",
        "------------------------------------------------------------",
        "",
        "Can a fresh live Claude Vision call independently reproduce the P2.6.6 semantic",
        "distinction (DISTINCT vs DUPLICATE vs AMBIGUOUS) on the same 29-beam population,",
        "and is that decision stable on an independent repeat?",
        "",
        "------------------------------------------------------------",
        "DATASET",
        "------------------------------------------------------------",
        "",
        f"- target beams: {m.get('target_beams')}",
        f"- ROLE_COVERAGE_GAP: {sum(1 for r in records if r.get('longitudinal_coverage')==COVER_LAYER)}",
        f"- FULLY_COVERED diagnostic: {sum(1 for r in records if r.get('longitudinal_coverage')==COVER_FULL)}",
        "- source: P2.6.6 target_records.json (not resampled)",
        "- GT_USED_FOR_RESOLVER = FALSE",
        "- ESTIMATOR_USED_FOR_RESOLVER = FALSE",
        "",
        "------------------------------------------------------------",
        "LIVE EXECUTION",
        "------------------------------------------------------------",
        "",
        f"- PRIMARY attempted: {m.get('primary_live_calls')}",
        f"- REPEAT attempted: {m.get('repeat_live_calls')}",
        f"- TOTAL attempted: {m.get('total_live_calls')}",
        f"- successful primary: {m.get('successful_primary')}",
        f"- successful repeat: {m.get('successful_repeat')}",
        f"- failed primary: {m.get('failed_primary')}",
        f"- failed repeat: {m.get('failed_repeat')}",
        f"- retries: {m.get('retry_count_total')}",
        f"- cache hits: {m.get('cache_hits')} (must be 0)",
        f"- schema-coerced reparses: {m.get('schema_reparsed_total', 0)} "
        f"(primary={m.get('schema_reparsed_primary', 0)}, repeat={m.get('schema_reparsed_repeat', 0)})",
        f"- remaining API/credit failures: {m.get('api_failures_remaining', 0)}",
        "- schema coercion stringifies nested evidence/interpretation/notes only; it does not invent decision.",
        "",
        "------------------------------------------------------------",
        "SEMANTIC RESULTS (PRIMARY VALID)",
        "------------------------------------------------------------",
        "",
        f"- DISTINCT: {acc.get('DISTINCT')}",
        f"- DUPLICATE: {acc.get('DUPLICATE')}",
        f"- AMBIGUOUS: {acc.get('AMBIGUOUS')}",
        f"- UNSUPPORTED: {acc.get('UNSUPPORTED')}",
        "",
        "------------------------------------------------------------",
        "REPEATABILITY",
        "------------------------------------------------------------",
        "",
        f"- SEMANTIC AGREEMENT: {_pct(rep.get('semantic_repeatability_rate'))} "
        f"({rep.get('exact_semantic_decision_agreement')}/{rep.get('valid_paired_cases')})",
        f"- CRITICAL CASE AGREEMENT: {_pct((m.get('critical_repeatability') or {}).get('critical_case_repeatability'))}",
        f"- DISTINCT→DUPLICATE: {rep.get('DISTINCT_to_DUPLICATE')}",
        f"- DUPLICATE→DISTINCT: {rep.get('DUPLICATE_to_DISTINCT')}",
        f"- DISTINCT↔AMBIGUOUS: {rep.get('DISTINCT_to_AMBIGUOUS')} / {rep.get('AMBIGUOUS_to_DISTINCT')}",
        f"- mean confidence delta: {rep.get('mean_confidence_delta')}",
        "",
        "------------------------------------------------------------",
        "ACCURACY vs P2.6.6 REFERENCE (AFTER INFERENCE)",
        "------------------------------------------------------------",
        "",
        f"- TRUE RECOVERY RECALL: {_pct(acc.get('true_recovery_recall'))}",
        f"- DISTINCT precision/recall: {_pct(acc.get('distinct_precision'))} / {_pct(acc.get('distinct_recall'))}",
        f"- DUPLICATE precision/recall: {_pct(acc.get('duplicate_precision'))} / {_pct(acc.get('duplicate_recall'))}",
        f"- FALSE DISTINCT: {acc.get('false_DISTINCT')}",
        f"- FALSE DUPLICATE: {acc.get('false_DUPLICATE')}",
        f"- recovery retention: {_pct(acc.get('recovery_retention'))}",
        f"- ambiguous rate: {_pct(acc.get('ambiguous_rate'))}",
        f"- unsupported rate: {_pct(acc.get('unsupported_rate'))}",
        "",
        "------------------------------------------------------------",
        "CRITICAL CASES",
        "------------------------------------------------------------",
        "",
        f"- Fifth/B128 primary=`{b128.get('primary')}` repeat=`{b128.get('repeat')}` "
        f"p266=`{b128.get('p266_reference')}` p265=`{b128.get('p265_context')}`",
        f"- Fourth/B141 primary=`{b141.get('primary')}` repeat=`{b141.get('repeat')}` "
        f"p266=`{b141.get('p266_reference')}` p265=`{b141.get('p265_context')}`",
        f"- Fourth/B23 primary=`{b23.get('primary')}` repeat=`{b23.get('repeat')}` "
        f"p266=`{b23.get('p266_reference')}` p265=`{b23.get('p265_context')}`",
        f"- strong_split: `{crit.get('strong_split')}`",
        f"- b128_duplicate_failure: `{crit.get('b128_duplicate_failure')}`",
        "",
        "------------------------------------------------------------",
        "SAFETY",
        "------------------------------------------------------------",
        "",
        f"- PRODUCTION MUTATION: {prod.get('production_mutation_count', 0)}",
        f"- P2.6.4 UNCHANGED: `{prod.get('p264_artefacts_unchanged')}`",
        f"- P2.6.5 UNCHANGED: `{prod.get('p265_artefacts_unchanged')}`",
        f"- P2.6.6 UNCHANGED: `{prod.get('p266_artefacts_unchanged')}`",
        f"- fingerprints ok: `{prod.get('fingerprints_ok')}`",
        f"- firewall ok: `{fw.get('ok')}`",
        f"- leakage ok: `{leak.get('ok')}`",
        "- no DUPLICATE→SKIP production rule",
        "- FULLY_COVERED path unchanged",
        "",
        "------------------------------------------------------------",
        "DECISION",
        "------------------------------------------------------------",
        "",
        f"- **STRENGTH**: {rec.get('strength')}",
        f"- **DECISION**: {rec.get('decision')}",
        f"- {rec.get('note')}",
        "",
        "Allowed: LIVE_SEMANTIC_VALIDATED | LIVE_SEMANTIC_PARTIALLY_VALIDATED | "
        "REFINE_SEMANTIC_ARBITRATION | LIVE_BENCHMARK_FAILED.",
        "NEVER: PRODUCTION_READY.",
        "",
        "------------------------------------------------------------",
        "FINAL INTERPRETATION",
        "------------------------------------------------------------",
        "",
        result.get("interpretation")
        or "See decision note. Live results are evidence only and do not change production routing.",
        "",
    ]
    status_text = "\n".join(status) + "\n"
    (out_root / "P2.6.7_STATUS.md").write_text(status_text, encoding="utf-8")
    (reports / "P2.6.7_STATUS.md").write_text(status_text, encoding="utf-8")

    control_lines = [
        "# P2.6.7 — Control cases",
        "",
        "Evaluation-only. Reference labels were not sent to Claude.",
        "",
        "| set | beam | P2.6.4 | P2.6.5 | P2.6.6 ref | LIVE_PRIMARY | LIVE_REPEAT | p_conf | r_conf | agree | family | notes |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        prim = r.get("primary") or {}
        rpt = r.get("repeat") or {}
        agree = _dec(prim) == _dec(rpt) and prim.get("ok") and rpt.get("ok")
        note = ""
        if r.get("longitudinal_coverage") == COVER_FULL:
            note = f"diagnostic; production remains {r.get('observed_decision') or DECISION_SKIP}"
        control_lines.append(
            f"| {r.get('set_key')} | {r.get('beam_id')} | {r.get('observed_decision')} | "
            f"{r.get('p265_context_status')} | {r.get('p266_reference')} | {_dec(prim)} | {_dec(rpt)} | "
            f"{_conf(prim)} | {_conf(rpt)} | {agree} | {r.get('family')} | {note} |"
        )
    control_text = "\n".join(control_lines) + "\n"
    (out_root / "P2.6.7_CONTROL_CASES.md").write_text(control_text, encoding="utf-8")

    safety = [
        "# P2.6.7 — Safety",
        "",
        f"- production mutation = {prod.get('production_mutation_count', 0)}",
        f"- P2.6.4 unchanged: `{prod.get('p264_artefacts_unchanged')}`",
        f"- P2.6.5 unchanged: `{prod.get('p265_artefacts_unchanged')}`",
        f"- P2.6.6 unchanged: `{prod.get('p266_artefacts_unchanged')}`",
        f"- fingerprints: `{prod.get('fingerprints_ok')}`",
        "- live API enabled only in this isolated shadow benchmark",
        "- GT_USED_FOR_RESOLVER = FALSE",
        "- ESTIMATOR_USED_FOR_RESOLVER = FALSE",
        "- no hard-coded expected decisions in live caller / prompt / schema",
        "- no hard-coded beam IDs in resolver logic",
        "- FULLY_COVERED production path unchanged",
        "- semantic output cannot alter production routing",
        "- no DUPLICATE -> SKIP rule",
        "- no semantic confidence -> SKIP rule",
        "- no API secrets written",
        "- repeat calls independently executed with cache bypass",
        "",
    ]
    (out_root / "P2.6.7_SAFETY.md").write_text("\n".join(safety) + "\n", encoding="utf-8")
    (out_root / "P2.6.7_PROMPT.md").write_text(prompt_document(), encoding="utf-8")

    live_decisions = []
    for r in records:
        live_decisions.append(
            {
                "set_key": r.get("set_key"),
                "beam_id": r.get("beam_id"),
                "region_id": r.get("region_id"),
                "longitudinal_coverage": r.get("longitudinal_coverage"),
                "observed_decision": r.get("observed_decision"),
                "p265_context_status": r.get("p265_context_status"),
                "p266_reference": r.get("p266_reference"),
                "primary": {
                    "ok": (r.get("primary") or {}).get("ok"),
                    "decision": _dec(r.get("primary")),
                    "confidence": _conf(r.get("primary")),
                    "error_class": (r.get("primary") or {}).get("error_class"),
                    "source": (r.get("primary") or {}).get("source"),
                    "cache_hit": (r.get("primary") or {}).get("cache_hit"),
                    "payload": (r.get("primary") or {}).get("payload"),
                },
                "repeat": {
                    "ok": (r.get("repeat") or {}).get("ok"),
                    "decision": _dec(r.get("repeat")),
                    "confidence": _conf(r.get("repeat")),
                    "error_class": (r.get("repeat") or {}).get("error_class"),
                    "source": (r.get("repeat") or {}).get("source"),
                    "cache_hit": (r.get("repeat") or {}).get("cache_hit"),
                    "payload": (r.get("repeat") or {}).get("payload"),
                },
                "production_routing_changed": False,
            }
        )
    (out_root / "P2.6.7_LIVE_DECISIONS.json").write_text(
        json.dumps(live_decisions, indent=2, default=str), encoding="utf-8"
    )
    (out_root / "P2.6.7_REPEATABILITY.json").write_text(
        json.dumps(
            {"repeatability": rep, "critical_repeatability": m.get("critical_repeatability")},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    (out_root / "P2.6.7_METRICS.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    results_doc = {
        "phase_id": result.get("phase_id"),
        "model_version": result.get("model_version"),
        "gate_version": result.get("gate_version"),
        "mode": result.get("mode"),
        "pass_fail": result.get("pass_fail"),
        "decision": rec.get("decision"),
        "target_beams": m.get("target_beams"),
        "primary_live_calls": m.get("primary_live_calls"),
        "repeat_live_calls": m.get("repeat_live_calls"),
        "total_live_calls": m.get("total_live_calls"),
        "successful_primary": m.get("successful_primary"),
        "successful_repeat": m.get("successful_repeat"),
        "semantic_repeatability_rate": rep.get("semantic_repeatability_rate"),
        "critical_case_repeatability": (m.get("critical_repeatability") or {}).get("critical_case_repeatability"),
        "distinct_precision": acc.get("distinct_precision"),
        "distinct_recall": acc.get("distinct_recall"),
        "duplicate_precision": acc.get("duplicate_precision"),
        "duplicate_recall": acc.get("duplicate_recall"),
        "false_distinct": acc.get("false_DISTINCT"),
        "false_duplicate": acc.get("false_DUPLICATE"),
        "true_recovery_recall": acc.get("true_recovery_recall"),
        "recovery_retention": acc.get("recovery_retention"),
        "ambiguous_rate": acc.get("ambiguous_rate"),
        "unsupported_rate": acc.get("unsupported_rate"),
        "production_mutation_count": prod.get("production_mutation_count", 0),
        "production_routing_changed": False,
        "recommendation": rec,
    }
    (out_root / "P2.6.7_RESULTS.json").write_text(json.dumps(results_doc, indent=2, default=str), encoding="utf-8")
    (reports / "metrics.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    (reports / "unit_tests.json").write_text(json.dumps(tests, indent=2, default=str), encoding="utf-8")
    return {
        "status": str(out_root / "P2.6.7_STATUS.md"),
        "results": str(out_root / "P2.6.7_RESULTS.json"),
        "metrics": str(out_root / "P2.6.7_METRICS.json"),
    }


__all__ = ["write_reports"]
