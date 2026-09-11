"""P2.6.10-E.1 orchestrator. Fifth Set hybrid accuracy benchmark. Offline default. No Claude."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .anti_hardcoding import run_anti_hardcoding
from .benchmark_mapper import calcs_to_workbook
from .benchmark_truth_loader import load_benchmark_truth
from .config import (
    DEFAULT_MODE,
    ENGINEERING_CHANGES,
    GATE_VERSION,
    LIVE_CLAUDE_CALL,
    MODE_LIVE,
    MODE_OFFLINE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SHADOW_ONLY,
)
from .error_analyzers import engineering_errors, semantic_errors, spacer_report, stirrup_errors
from .hybrid_runner_adapter import execute_population
from .kpis import compute_kpis, diameter_wise
from .pdf_report_writer import PDF_NAME, write_pdf
from .population_discovery import discover_population
from .provenance_analyzer import analyze as analyze_provenance
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
from .vision_artifact_loader import discover_vision_artefacts

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run_phase_p2610e1(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    mode: str = DEFAULT_MODE,
    run_tests: bool = True,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    pkg = Path(__file__).resolve().parent
    out_root.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    mode_u = str(mode or DEFAULT_MODE).upper()
    if mode_u == MODE_LIVE:
        raise RuntimeError("LIVE_HYBRID_BENCHMARK is not enabled in this runner. Default remains OFFLINE_REPLAY.")

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  MODE: {MODE_OFFLINE}")
    _log(f"  LIVE_CLAUDE_CALL: {LIVE_CLAUDE_CALL}")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-E.1 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-E.1 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-E.1 runtime leakage: {leak.get('hits')}")

    pop = discover_population(v10)
    _log(f"  discovered_model_beams={pop.get('model_beam_count')} ok={pop.get('ok')}")
    if not pop.get("ok"):
        raise RuntimeError(f"P2.6.10-E.1 fail-closed population: {pop.get('reason')}")

    catalog = (pop.get("catalog") or {}).get("by_id") or {}
    bundle = {}
    if pop.get("r13_path"):
        bundle["r13_models"] = Path(pop["r13_path"])
    if pop.get("run_root"):
        bundle["steel_weight_summary"] = Path(pop["run_root"]) / "data" / "output" / "Production_Output" / "steel_weight_summary.json"
        bundle["bbs_summary"] = Path(pop["run_root"]) / "data" / "output" / "Production_Output" / "bbs_summary.json"
    fp_paths = fingerprint_paths(v10, bundle)
    before = capture_fingerprints(fp_paths)

    vision = discover_vision_artefacts(v10)
    _log(f"  vision_usable={vision.get('usable_beam_count')} scanned={vision.get('scanned')} api_failed={vision.get('api_failed')}")

    truth = load_benchmark_truth(estimator_path=pop.get("estimator_path"))
    if not truth.get("ok"):
        raise RuntimeError("P2.6.10-E.1 fail-closed: estimator truth unavailable")

    beam_ids = list(pop.get("model_beam_ids") or [])
    calcs = execute_population(beam_ids=beam_ids, catalog=catalog, vision_by_id=vision.get("by_id") or {})
    model_wb = calcs_to_workbook(calcs, source_path="shadow-hybrid-fifth")
    kpis = compute_kpis(drawing_set=str(pop.get("drawing_set") or "Fifth Set Drawings"), estimator=truth["workbook"], model=model_wb)
    dia = diameter_wise(kpis)
    prov = analyze_provenance(calcs)
    sem = semantic_errors(bar_matching=kpis.get("bar_matching") or {}, beam_matching=kpis.get("beam_matching") or {}, calcs=calcs)
    eng = engineering_errors(calcs=calcs, bar_matching=kpis.get("bar_matching") or {})
    stir = stirrup_errors(calcs=calcs, bar_matching=kpis.get("bar_matching") or {})
    spacers = spacer_report(calcs=calcs)
    anti = run_anti_hardcoding(package_dir=pkg)
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    intact = prior_artefacts_intact(v10)
    prior_ok = {
        "p2610d4": prior_phase_unit_ok(v10, "PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark", 28),
        "p2610d1": prior_phase_unit_ok(v10, "PhaseP2610D1_vision_semantic_contract_hybrid_foundation", 32),
    }
    runtime_s = round(time.perf_counter() - t0, 3)

    limitations = []
    if int(vision.get("usable_beam_count") or 0) < len(beam_ids):
        limitations.append("VISION_COVERAGE_INCOMPLETE")
    if int(prov.get("withheld_groups") or 0):
        limitations.append("AMBIGUOUS_WITHHELD")
    if int(stir.get("engineering_unavailable_beams") or 0):
        limitations.append("STIRRUP_ENGINEERING_UNAVAILABLE")

    decision = "PASS"
    if not unit.get("success") or not fp_cmp.get("unchanged") or not anti.get("ok") or not intact.get("ok") or not pop.get("ok"):
        decision = "FAIL"
    elif limitations:
        decision = "PASS_WITH_LIMITATIONS"

    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": decision,
        "pass_fail": "PASS" if decision != "FAIL" else "FAIL",
        "mode": MODE_OFFLINE,
        "live_claude_call": LIVE_CLAUDE_CALL,
        "runtime_s": runtime_s,
        "population": {kk: vv for kk, vv in pop.items() if kk != "catalog"},
        "execution_manifest": {
            "mode": MODE_OFFLINE,
            "architecture": "D.1 contract + D.2 resolver + D.3 binding + D.4 calculation",
            "beams_executed": len(calcs),
            "vision_usable": vision.get("usable_beam_count"),
            "fallback_beams": sum(1 for c in calcs if c.get("provenance_kind") != "HYBRID"),
            "live_calls": 0,
        },
        "vision_coverage": vision,
        "hybrid_calculations": calcs,
        "truth": truth,
        "kpis": kpis,
        "diameter_wise": dia,
        "provenance": prov,
        "semantic_errors": sem,
        "engineering_errors": eng,
        "stirrup_errors": stir,
        "spacer_report": spacers,
        "limitations": limitations,
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
            "production_mutation_delta": 0 if fp_cmp.get("unchanged") else 1,
        },
        "output_root": str(out_root),
    }
    write_reports(out_root=out_root, result=result)
    pdf_path = write_pdf(out_root=out_root)
    result["pdf_path"] = str(pdf_path)
    slim_path = out_root / "P2.6.10-E.1_RESULTS.json"
    slim = json.loads(slim_path.read_text(encoding="utf-8"))
    slim["pdf_path"] = str(pdf_path)
    slim_path.write_text(json.dumps(slim, indent=2, default=str), encoding="utf-8")
    _log(f"  decision={decision} runtime_s={runtime_s}")
    _print_summary(result)
    return result


def _print_summary(result: Dict[str, Any]) -> None:
    k = result.get("kpis") or {}
    beam = k.get("beam_identification") or {}
    bar = k.get("bar_identification") or {}
    cor = k.get("correct_of_detected") or {}
    dia = k.get("diameter_identification") or {}
    steel = k.get("steel") or {}
    overall = k.get("overall") or {}
    print()
    print("P2.6.10-E.1 - Fifth Set Hybrid Architecture Accuracy Benchmark")
    print(f"MODEL_VERSION: {result.get('model_version')}")
    print(f"GATE: {result.get('gate_version')}")
    print(f"DECISION: {result.get('decision')}")
    print(f"MODE: {result.get('mode')}")
    print(f"GT_BEAMS: {beam.get('total_ground_truth_beams')} DETECTED: {beam.get('detected_ground_truth_beams')} ID%: {beam.get('beam_identification_percent')}")
    print(f"GT_BARS: {bar.get('total_ground_truth_bars')} IDENTIFIED: {bar.get('identified_ground_truth_bars')} ID%: {bar.get('bar_identification_percent')}")
    print(f"MATCH: {cor.get('fully_matched_detected_bars')} CORRECT%: {cor.get('correct_of_detected_percent')}")
    print(f"DIAMETER%: {dia.get('diameter_identification_percent')}")
    print(f"HYBRID_KG: {steel.get('hybrid_total_kg')} BENCH_KG: {steel.get('benchmark_total_kg')} STEEL%: {steel.get('weight_accuracy_percent')}")
    print(f"OVERALL%: {overall.get('overall_accuracy_percent')}")
    print(f"LIVE_CLAUDE_CALL: false")
    print(f"PRODUCTION_MUTATION_DELTA: {(result.get('production') or {}).get('production_mutation_delta')}")
    unit = result.get("unit_tests") or {}
    print(f"TESTS: {unit.get('passed')} / {unit.get('total')}")
    print(f"OUTPUT: {result.get('output_root')}")
    print(f"PDF: {result.get('pdf_path')}")
    print()


__all__ = ["run_phase_p2610e1"]
