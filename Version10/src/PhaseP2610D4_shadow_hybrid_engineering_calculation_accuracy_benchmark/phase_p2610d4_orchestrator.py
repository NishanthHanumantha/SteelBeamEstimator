"""P2.6.10-D.4 orchestrator. Shadow hybrid engineering calculation. No Claude. No production."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .accuracy_metrics import beam_comparison, diameter_report, population_metrics
from .anti_hardcoding import run_anti_hardcoding
from .baseline_loader import load_deterministic_baseline
from .beam_calculator import calculate_population
from .benchmark_truth_loader import load_benchmark_truth
from .config import (
    ENGINEERING_CHANGES,
    GATE_VERSION,
    LIVE_CLAUDE_CALL,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SHADOW_ONLY,
    STATUS_NO_TRUTH,
)
from .contribution_analyzer import analyze_beam, summarize
from .population_loader import load_d3_bindings, load_d3_population, load_r13_catalog
from .provenance_audit import audit_population
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_artefacts_intact,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)
from .report import write_reports
from .unit_tests import run_unit_tests

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _recommendation(decision: str, metrics: Dict[str, Any]) -> str:
    if decision == "FAIL":
        return "STOP"
    delta = metrics.get("accuracy_improvement_delta_pp")
    amb = (metrics.get("calculation_completeness") or {}).get("SHADOW_AMBIGUOUS", 0)
    if delta is None:
        return "INVESTIGATE"
    if delta > 0 and amb >= 0:
        return "PROCEED_TO_NEXT_SHADOW_PHASE"
    if delta < 0:
        return "INVESTIGATE"
    return "INVESTIGATE"


def run_phase_p2610d4(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    pkg = Path(__file__).resolve().parent
    out_root.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  LIVE_CLAUDE_CALL: {LIVE_CLAUDE_CALL}")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-D.4 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-D.4 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-D.4 runtime leakage: {leak.get('hits')}")

    catalog = load_r13_catalog(v10)
    bundle = {}
    if catalog.get("path"):
        bundle["r13_models"] = Path(catalog["path"])
    if catalog.get("run_root"):
        bundle["steel_weight_summary"] = Path(catalog["run_root"]) / "data" / "output" / "Production_Output" / "steel_weight_summary.json"
        bundle["bbs_summary"] = Path(catalog["run_root"]) / "data" / "output" / "Production_Output" / "bbs_summary.json"
    fp_paths = fingerprint_paths(v10, bundle)
    before = capture_fingerprints(fp_paths)

    pop = load_d3_population(v10)
    _log(f"  discovered={pop.get('discovered_count')} artefact={pop.get('artefact_discovered_count')} ok={pop.get('ok')}")
    if not pop.get("ok"):
        raise RuntimeError(f"P2.6.10-D.4 fail-closed population: {pop.get('reason')}")
    bindings_payload = load_d3_bindings(v10)
    if not bindings_payload.get("ok"):
        raise RuntimeError(f"P2.6.10-D.4 fail-closed bindings: {bindings_payload.get('reason')}")
    missing = [bid for bid in (pop.get("beam_ids") or []) if bid not in (bindings_payload.get("by_id") or {})]
    if missing:
        raise RuntimeError("P2.6.10-D.4 fail-closed: D.3 binding missing for discovered beams")

    ordered = [bindings_payload["by_id"][bid] for bid in pop.get("beam_ids") or []]
    calcs = calculate_population(ordered, catalog.get("by_id") or {})
    baseline = load_deterministic_baseline(run_root=catalog.get("run_root"), beam_ids=pop.get("beam_ids") or [])
    truth = load_benchmark_truth(v10=v10, beam_ids=pop.get("beam_ids") or [])
    comparisons = []
    contributions = []
    ambiguous_rows = []
    for calc in calcs:
        bid = str(calc.get("beam_id"))
        cmp = beam_comparison(
            hybrid=calc,
            baseline=(baseline.get("by_id") or {}).get(bid),
            truth=(truth.get("by_id") or {}).get(bid),
        )
        if not (truth.get("coverage") or {}).get(bid, {}).get("available"):
            cmp["truth_source"] = STATUS_NO_TRUTH
        comparisons.append(cmp)
        contributions.append(analyze_beam(hybrid=calc, comparison=cmp))
        ambiguous_rows.extend(calc.get("withheld_ambiguous") or [])

    popm = population_metrics(comparisons, calcs)
    dia = diameter_report(comparisons)
    contrib_sum = summarize(contributions)
    prov = audit_population(ordered, calcs)
    anti = run_anti_hardcoding(package_dir=pkg)
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    intact = prior_artefacts_intact(v10)
    prior_ok = {
        "p2610d1": prior_phase_unit_ok(v10, "PhaseP2610D1_vision_semantic_contract_hybrid_foundation", 32),
        "p2610d2": prior_phase_unit_ok(v10, "PhaseP2610D2_shadow_hybrid_semantic_resolver", 30),
        "p2610d3": prior_phase_unit_ok(v10, "PhaseP2610D3_hybrid_engineering_binding_compatibility", 24),
    }
    runtime_s = round(time.perf_counter() - t0, 3)

    limitations = []
    if popm.get("no_benchmark_truth"):
        limitations.append("NO_BENCHMARK_TRUTH")
    if (popm.get("calculation_completeness") or {}).get("SHADOW_AMBIGUOUS"):
        limitations.append("AMBIGUOUS_WITHHELD")
    if (popm.get("calculation_completeness") or {}).get("SHADOW_PARTIAL"):
        limitations.append("PARTIAL_CALCULATIONS")

    decision = "PASS"
    if not unit.get("success") or not fp_cmp.get("unchanged") or not anti.get("ok") or not intact.get("ok") or not pop.get("ok") or not prov.get("ok"):
        decision = "FAIL"
    elif limitations:
        decision = "PASS_WITH_LIMITATIONS"

    rec = _recommendation(decision, popm)
    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": decision,
        "pass_fail": "PASS" if decision != "FAIL" else "FAIL",
        "live_claude_call": LIVE_CLAUDE_CALL,
        "runtime_s": runtime_s,
        "population": pop,
        "bindings": ordered,
        "hybrid_calculations": calcs,
        "baseline": baseline,
        "truth": truth,
        "comparisons": comparisons,
        "contributions": contributions,
        "contribution_summary": contrib_sum,
        "ambiguous_report": ambiguous_rows,
        "population_metrics": popm,
        "diameter_report": dia,
        "provenance_audit": prov,
        "limitations": limitations,
        "recommendation": rec,
        "anti_hardcoding": anti,
        "unit_tests": unit,
        "fingerprints": fp_cmp,
        "prior_phase_units": {k: bool(v.get("ok")) for k, v in prior_ok.items()},
        "production": {
            "production_mutation_count": 0 if fp_cmp.get("unchanged") else 1,
            "production_write": PRODUCTION_WRITE,
            "production_action": PRODUCTION_ACTION,
            "engineering_changes": ENGINEERING_CHANGES,
            "shadow_only": SHADOW_ONLY,
            "live_claude_call": LIVE_CLAUDE_CALL,
            "steel_delta": 0,
            "bbs_delta": 0,
            "workbook_delta": 0,
            "production_mutation_delta": 0 if fp_cmp.get("unchanged") else 1,
        },
        "output_root": str(out_root),
    }
    write_reports(out_root=out_root, result=result)
    _log(f"  decision={decision} runtime_s={runtime_s} recommendation={rec}")
    _print_summary(result)
    return result


def _print_summary(result: Dict[str, Any]) -> None:
    m = result.get("population_metrics") or {}
    st = m.get("calculation_completeness") or {}
    print()
    print("P2.6.10-D.4 - Shadow Hybrid Engineering Calculation & Accuracy Benchmark")
    print(f"MODEL_VERSION: {result.get('model_version')}")
    print(f"GATE: {result.get('gate_version')}")
    print(f"DECISION: {result.get('decision')}")
    print(f"Discovered: {m.get('population_discovered')}")
    print(f"COMPLETE={st.get('SHADOW_COMPLETE', 0)} PARTIAL={st.get('SHADOW_PARTIAL', 0)} AMBIGUOUS={st.get('SHADOW_AMBIGUOUS', 0)} INCOMPATIBLE={st.get('SHADOW_INCOMPATIBLE', 0)}")
    print(f"NO_BENCHMARK_TRUTH: {m.get('no_benchmark_truth')} coverage={m.get('benchmark_truth_coverage')}")
    print(f"HYBRID_TOTAL_KG: {m.get('hybrid_total_kg')}")
    print(f"DETERMINISTIC_TOTAL_KG: {m.get('deterministic_total_kg')}")
    print(f"BENCHMARK_TOTAL_KG: {m.get('benchmark_total_kg')}")
    print(f"HYBRID_ERROR_PCT: {m.get('hybrid_error_pct')}")
    print(f"DETERMINISTIC_ERROR_PCT: {m.get('deterministic_error_pct')}")
    print(f"HYBRID_ACCURACY_PCT: {m.get('hybrid_accuracy_pct')}")
    print(f"DETERMINISTIC_ACCURACY_PCT: {m.get('deterministic_accuracy_pct')}")
    print(f"ACCURACY_IMPROVEMENT_DELTA_PP: {m.get('accuracy_improvement_delta_pp')}")
    print(f"WINNERS: {m.get('winners')}")
    print(f"LIVE_CLAUDE_CALL: false")
    print(f"PRODUCTION_MUTATION_DELTA: {(result.get('production') or {}).get('production_mutation_delta')}")
    print(f"FINGERPRINTS: {'UNCHANGED' if (result.get('fingerprints') or {}).get('unchanged') else 'CHANGED'}")
    unit = result.get("unit_tests") or {}
    print(f"TESTS: {unit.get('passed')} / {unit.get('total')}")
    print(f"OUTPUT: {result.get('output_root')}")
    print(f"RECOMMENDATION: {result.get('recommendation')}")
    print()


__all__ = ["run_phase_p2610d4"]
