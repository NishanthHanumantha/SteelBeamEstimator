"""P2.6.8 reports. Shadow diagnostic — not production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    m = result.get("metrics") or {}
    rec = result.get("recommendation") or {}
    tests = result.get("unit_tests") or {}
    prod = result.get("production") or {}
    controls = m.get("controls") or {}
    cases = controls.get("cases") or {}
    b128 = cases.get("Fifth/B128") or {}
    b141 = cases.get("Fourth/B141") or {}
    records: List[Dict[str, Any]] = result.get("records") or []

    status = [
        "# P2.6.8 — Evidence-Conflict Arbitration / Layer-Aware Semantic Resolver",
        "",
        "Shadow / research only. Observed production routing remains P2.6.4 / P2.6.5.",
        "NEVER PRODUCTION_READY. No DUPLICATE→SKIP. No DISTINCT→CALL.",
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
        "When semantic evidence and deterministic evidence disagree, what exactly",
        "are they disagreeing about (specification vs physical target vs layer)?",
        "",
        "------------------------------------------------------------",
        "DATASET",
        "------------------------------------------------------------",
        "",
        f"- target beams: {m.get('target_beams')}",
        "- source: P2.6.6 target_records.json + stored P2.6.7 live decisions (not resampled)",
        "- GT_USED_FOR_RESOLVER = FALSE",
        "- ESTIMATOR_USED_FOR_RESOLVER = FALSE",
        "- LIVE_API default = FALSE",
        "",
        "------------------------------------------------------------",
        "CONFLICT DISTRIBUTION",
        "------------------------------------------------------------",
        "",
    ]
    dist = m.get("conflict_distribution") or {}
    for key, val in dist.items():
        status.append(f"- {key}: {val}")
    status.extend(
        [
            "",
            "------------------------------------------------------------",
            "ARBITRATION DISTRIBUTION",
            "------------------------------------------------------------",
            "",
        ]
    )
    adist = m.get("arbitration_distribution") or {}
    for key, val in adist.items():
        status.append(f"- {key}: {val}")
    status.extend(
        [
            "",
            "------------------------------------------------------------",
            "CRITICAL CASES",
            "------------------------------------------------------------",
            "",
            f"- Fifth/B128 det=`{b128.get('deterministic')}` sem=`{b128.get('semantic')}`",
            f"  conflict=`{b128.get('conflict_type')}` arb=`{b128.get('arbitration_result')}`",
            f"  layer=`{b128.get('resolved_layer')}` winner=`{b128.get('winning_evidence_source')}`",
            f"  action=`{b128.get('production_action')}` shadow=`{b128.get('shadow_only')}`",
            f"- Fourth/B141 det=`{b141.get('deterministic')}` sem=`{b141.get('semantic')}`",
            f"  conflict=`{b141.get('conflict_type')}` arb=`{b141.get('arbitration_result')}`",
            f"  layer=`{b141.get('resolved_layer')}` winner=`{b141.get('winning_evidence_source')}`",
            f"  action=`{b141.get('production_action')}` shadow=`{b141.get('shadow_only')}`",
            f"- b128_physical_distinct_protected: `{controls.get('b128_physical_distinct_protected')}`",
            f"- b141_not_overclassified: `{controls.get('b141_not_overclassified')}`",
            "",
            "------------------------------------------------------------",
            "SAFETY",
            "------------------------------------------------------------",
            "",
            f"- PRODUCTION MUTATION: {prod.get('production_mutation_count', 0)}",
            f"- P2.6.4 UNCHANGED: `{prod.get('p264_artefacts_unchanged')}`",
            f"- P2.6.5 UNCHANGED: `{prod.get('p265_artefacts_unchanged')}`",
            f"- P2.6.6 UNCHANGED: `{prod.get('p266_artefacts_unchanged')}`",
            f"- P2.6.7 UNCHANGED: `{prod.get('p267_artefacts_unchanged')}`",
            f"- all shadow_only: `{prod.get('all_shadow_only')}`",
            f"- all NO_CHANGE: `{prod.get('all_no_change')}`",
            "",
            "------------------------------------------------------------",
            "DECISION",
            "------------------------------------------------------------",
            "",
            f"- **STRENGTH**: {rec.get('strength')}",
            f"- **DECISION**: {rec.get('decision')}",
            f"- {rec.get('note')}",
            "",
            "Allowed: SAFE_SHADOW_DIAGNOSTIC | UNSAFE_SHADOW_DIAGNOSTIC | BENCHMARK_FAILED | IMPLEMENTATION_FAILED.",
            "NEVER: PRODUCTION_READY.",
            "",
        ]
    )
    status_text = "\n".join(status) + "\n"
    (out_root / "P2.6.8_STATUS.md").write_text(status_text, encoding="utf-8")
    (reports / "P2.6.8_STATUS.md").write_text(status_text, encoding="utf-8")

    (out_root / "P2.6.8_ARBITRATION_DECISIONS.json").write_text(
        json.dumps(records, indent=2, default=str), encoding="utf-8"
    )
    (out_root / "P2.6.8_METRICS.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    results_doc = {
        "phase_id": result.get("phase_id"),
        "model_version": result.get("model_version"),
        "gate_version": result.get("gate_version"),
        "mode": result.get("mode"),
        "pass_fail": result.get("pass_fail"),
        "decision": rec.get("decision"),
        "target_beams": m.get("target_beams"),
        "conflict_distribution": m.get("conflict_distribution"),
        "arbitration_distribution": m.get("arbitration_distribution"),
        "controls": controls,
        "production_mutation_count": prod.get("production_mutation_count", 0),
        "production_routing_changed": False,
        "recommendation": rec,
    }
    (out_root / "P2.6.8_RESULTS.json").write_text(json.dumps(results_doc, indent=2, default=str), encoding="utf-8")
    (reports / "metrics.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    safety = [
        "# P2.6.8 — Safety",
        "",
        f"- production mutation = {prod.get('production_mutation_count', 0)}",
        f"- all shadow_only = `{prod.get('all_shadow_only')}`",
        f"- all NO_CHANGE = `{prod.get('all_no_change')}`",
        "- GT_USED_FOR_RESOLVER = FALSE",
        "- ESTIMATOR_USED_FOR_RESOLVER = FALSE",
        "- no DUPLICATE -> SKIP rule",
        "- no DISTINCT -> CALL rule",
        "- no hard-coded beam IDs in arbitrator / conflict / evidence runtime",
        "",
    ]
    (out_root / "P2.6.8_SAFETY.md").write_text("\n".join(safety) + "\n", encoding="utf-8")
    return {"status": str(out_root / "P2.6.8_STATUS.md"), "results": str(out_root / "P2.6.8_RESULTS.json")}


__all__ = ["write_reports"]
