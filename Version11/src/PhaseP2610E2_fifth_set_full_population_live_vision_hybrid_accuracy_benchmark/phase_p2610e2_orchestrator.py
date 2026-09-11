"""P2.6.10-E.2 orchestrator. Default OFFLINE_VALIDATION. Live Claude only in LIVE_BENCHMARK."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.benchmark_mapper import calcs_to_workbook
from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.error_analyzers import (
    engineering_errors,
    semantic_errors,
    spacer_report,
    stirrup_errors,
)
from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.provenance_analyzer import analyze as analyze_provenance

from .anti_hardcoding import run_anti_hardcoding
from .checkpoint import load_checkpoint
from .config import (
    DEFAULT_MODE,
    ENGINEERING_CHANGES,
    GATE_VERSION,
    KIND_FALLBACK,
    KIND_HYBRID,
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
from .eligibility import evaluate_population
from .pdf_report_writer import write_pdf
from .population import build_population
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
from .subset_kpis import semantic_field_breakdown, split_scores
from .unit_tests import run_unit_tests
from .vision_loop import execute_all
from .visual_sources import discover_visual_sources

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _cohort_ids(calcs, kind: str):
    return [str(c.get("beam_id")) for c in calcs if c.get("provenance_kind") == kind]


def _live_summary(calcs) -> Dict[str, Any]:
    attempted = api_ok = api_fail = schema_ok = usable = retries = reused = 0
    cost_in = cost_out = 0
    recovered = 0
    for c in calcs:
        live = c.get("live") or {}
        full = c.get("live_full") or {}
        if live.get("called"):
            attempted += 1
            retries += int(live.get("retry_count") or 0)
        if live.get("action") == "REUSE":
            reused += 1
        if live.get("api_success"):
            api_ok += 1
        if live.get("failure_category") == "API_FAILED":
            api_fail += 1
        if live.get("schema_valid"):
            schema_ok += 1
        if live.get("semantic_usable"):
            usable += 1
        if live.get("call_provenance") == "VISION_RETRIED_AFTER_HISTORICAL_FAILURE" and live.get("semantic_usable"):
            recovered += 1
        usage = full.get("usage") or (live.get("usage") if isinstance(live.get("usage"), dict) else {}) or {}
        try:
            cost_in += int(usage.get("input_tokens") or usage.get("input") or 0)
            cost_out += int(usage.get("output_tokens") or usage.get("output") or 0)
        except (TypeError, ValueError):
            pass
    return {
        "attempted": attempted,
        "api_success": api_ok,
        "api_failed": api_fail,
        "schema_valid": schema_ok,
        "semantic_usable": usable,
        "retries": retries,
        "reused": reused,
        "historical_retried_recovered": recovered,
        "input_tokens": cost_in,
        "output_tokens": cost_out,
    }


def _vision_failures(calcs) -> Dict[str, Any]:
    counts = {
        "API_FAILED": 0,
        "SCHEMA_FAILED": 0,
        "SEMANTIC_UNUSABLE": 0,
        "TARGET_NOT_IDENTIFIED": 0,
        "VISUAL_NOT_READY": 0,
        "OTHER": 0,
    }
    recovered = 0
    for c in calcs:
        live = c.get("live") or {}
        cat = str(live.get("failure_category") or "")
        if live.get("call_provenance") == "VISION_RETRIED_AFTER_HISTORICAL_FAILURE" and live.get("semantic_usable"):
            recovered += 1
            continue
        if cat in counts:
            counts[cat] += 1
        elif cat and cat not in ("OK", "LIVE_DISABLED", "None"):
            counts["OTHER"] += 1
    return {"counts": counts, "historical_api_recovered": recovered, "note": "Recovered historical API failures are not counted as current permanent failures."}


def run_phase_p2610e2(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    mode: str = DEFAULT_MODE,
    run_tests: bool = True,
    client_override: Optional[Callable] = None,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    pkg = Path(__file__).resolve().parent
    out_root.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    mode_u = str(mode or DEFAULT_MODE).upper()
    if mode_u not in (MODE_LIVE, MODE_OFFLINE):
        raise RuntimeError(f"unsupported mode {mode}")
    live_enabled = mode_u == MODE_LIVE

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  MODE: {mode_u}")
    _log(f"  LIVE_CLAUDE_CALL: {live_enabled}")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-E.2 unit tests failed: {failed}")
    else:
        existing_unit = out_root / "unit_tests.json"
        if existing_unit.exists():
            try:
                unit = json.loads(existing_unit.read_text(encoding="utf-8"))
                unit["reused_from_artefact"] = True
            except Exception:
                pass

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-E.2 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-E.2 runtime leakage: {leak.get('hits')}")

    pop = build_population(v10)
    if not pop.get("ok"):
        raise RuntimeError(f"P2.6.10-E.2 fail-closed population: {pop.get('reason')}")
    beam_ids = list(pop.get("model_beam_ids") or [])
    catalog = (pop.get("catalog") or {}).get("by_id") or {}
    visual = discover_visual_sources(v10, beam_ids=beam_ids)
    eligibility = evaluate_population(visual)
    _log(f"  model_beams={len(beam_ids)} visual_available={visual.get('available_count')} eligible={(eligibility.get('counts') or {}).get('VISION_ELIGIBLE')}")

    bundle = {}
    if pop.get("r13_path"):
        bundle["r13_models"] = Path(pop["r13_path"])
    if pop.get("estimator_path"):
        bundle["estimator_workbook"] = Path(pop["estimator_path"])
    if pop.get("run_root"):
        bundle["steel_weight_summary"] = Path(pop["run_root"]) / "data" / "output" / "Production_Output" / "steel_weight_summary.json"
        bundle["bbs_summary"] = Path(pop["run_root"]) / "data" / "output" / "Production_Output" / "bbs_summary.json"
    fp_paths = fingerprint_paths(v10, bundle)
    before = capture_fingerprints(fp_paths)
    est_before = before.get("estimator_workbook")

    anti = run_anti_hardcoding(package_dir=pkg, tmp=out_root / "_anti_tmp")
    calcs = execute_all(
        v10=v10,
        out_root=out_root,
        beam_ids=beam_ids,
        catalog=catalog,
        eligibility=eligibility,
        mode=mode_u,
        client_override=client_override if live_enabled else None,
    )
    ck = load_checkpoint(out_root)
    model_wb = calcs_to_workbook(calcs, source_path="shadow-hybrid-fifth-e2")
    truth = pop.get("truth") or {}
    splits = split_scores(
        drawing_set=str(pop.get("drawing_set") or "Fifth Set Drawings"),
        estimator=truth.get("workbook"),
        model_full=model_wb,
        hybrid_ids=_cohort_ids(calcs, KIND_HYBRID),
        fallback_ids=_cohort_ids(calcs, KIND_FALLBACK),
    )
    full_k = (splits.get("FULL_POPULATION") or {}).get("kpis") or {}
    hy_ids = _cohort_ids(calcs, KIND_HYBRID)
    fb_ids = _cohort_ids(calcs, KIND_FALLBACK)
    n = max(len(calcs), 1)
    call_counts: Dict[str, int] = {}
    for c in calcs:
        key = str((c.get("live") or {}).get("call_provenance") or "UNKNOWN")
        call_counts[key] = call_counts.get(key, 0) + 1
    execution_provenance = {
        "hybrid_count": len(hy_ids),
        "fallback_count": len(fb_ids),
        "hybrid_percent": round(100.0 * len(hy_ids) / n, 2),
        "fallback_percent": round(100.0 * len(fb_ids) / n, 2),
        **call_counts,
    }
    live_sum = _live_summary(calcs)
    vis_fail = _vision_failures(calcs)
    prov = analyze_provenance(calcs)
    sem = semantic_errors(bar_matching=full_k.get("bar_matching") or {}, beam_matching=full_k.get("beam_matching") or {}, calcs=calcs)
    eng = engineering_errors(calcs=calcs, bar_matching=full_k.get("bar_matching") or {})
    stir = stirrup_errors(calcs=calcs, bar_matching=full_k.get("bar_matching") or {})
    spacers = spacer_report(calcs=calcs)
    tax = {
        "FULL_POPULATION": (full_k.get("correct_of_detected") or {}).get("taxonomy"),
        "HYBRID_ONLY": (((splits.get("HYBRID_ONLY") or {}).get("kpis") or {}).get("correct_of_detected") or {}).get("taxonomy"),
        "FALLBACK_ONLY": (((splits.get("FALLBACK_ONLY") or {}).get("kpis") or {}).get("correct_of_detected") or {}).get("taxonomy"),
    }
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    intact = prior_artefacts_intact(v10)
    frozen_units = {
        "C.3": prior_phase_unit_ok(v10, "PhaseP2610C3_visual_completeness_claude_shadow", 1),
        "C.4": prior_phase_unit_ok(v10, "PhaseP2610C4_shadow_truth_reconciliation_benchmark_calibration", 1),
        "C.5": prior_phase_unit_ok(v10, "PhaseP2610C5_stratified_vision_semantic_benchmark", 1),
        "D.1": prior_phase_unit_ok(v10, "PhaseP2610D1_vision_semantic_contract_hybrid_foundation", 1),
        "D.2": prior_phase_unit_ok(v10, "PhaseP2610D2_shadow_hybrid_semantic_resolver", 1),
        "D.3": prior_phase_unit_ok(v10, "PhaseP2610D3_hybrid_engineering_binding_compatibility", 1),
        "D.4": prior_phase_unit_ok(v10, "PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark", 1),
        "E.1": prior_phase_unit_ok(v10, "PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark", 1),
    }
    frozen_ok = all(v.get("ok") for v in frozen_units.values())
    runtime_s = round(time.perf_counter() - t0, 3)

    limitations = []
    counts = eligibility.get("counts") or {}
    if int(counts.get("VISION_BLOCKED_NOT_READY") or 0):
        limitations.append("VISUALLY_BLOCKED_BEAMS")
    if live_sum.get("api_failed"):
        limitations.append("API_FAILURES")
    if vis_fail.get("counts", {}).get("SCHEMA_FAILED"):
        limitations.append("SCHEMA_FAILURES")
    if fb_ids:
        limitations.append("FALLBACK_POPULATION_PRESENT")
    limitations.append("ESTIMATOR_WORKBOOK_MAPPING_LIMITATION")
    if int(stir.get("engineering_unavailable_beams") or 0):
        limitations.append("STIRRUP_ENGINEERING_UNAVAILABLE")
    if not live_enabled:
        limitations.append("OFFLINE_VALIDATION_NO_LIVE_CALLS")
    if int(prov.get("withheld_groups") or 0):
        limitations.append("AMBIGUOUS_WITHHELD")

    interrupted = bool(ck.get("pending_ids")) and ck.get("status") != "COMPLETE"
    if not unit.get("success") or not fp_cmp.get("unchanged") or not anti.get("ok") or not intact.get("ok") or not frozen_ok or after.get("estimator_workbook") != est_before:
        decision = "FAILED"
        live_completion = "FAILED_LIVE_BENCHMARK" if live_enabled else "FAILED"
    elif live_enabled and interrupted:
        decision = "PARTIAL"
        live_completion = "PARTIAL_LIVE_BENCHMARK"
    elif live_enabled:
        live_completion = "COMPLETE_LIVE_BENCHMARK"
        decision = "PASS_WITH_LIMITATIONS" if limitations else "PASS"
    else:
        live_completion = "OFFLINE_VALIDATION"
        decision = "PARTIAL"

    hy_over = (((splits.get("HYBRID_ONLY") or {}).get("kpis") or {}).get("overall") or {}).get("overall_accuracy_percent")
    fb_over = (((splits.get("FALLBACK_ONLY") or {}).get("kpis") or {}).get("overall") or {}).get("overall_accuracy_percent")
    full_over = ((full_k.get("overall") or {}).get("overall_accuracy_percent"))
    if not live_enabled:
        conclusion = "OFFLINE_VALIDATION did not call Claude. HYBRID coverage reflects reusable E.2 artefacts only, if any."
    elif not hy_ids:
        conclusion = "Live Vision was attempted where eligible, but no beam produced usable Vision semantics. The measured full-population result is the FALLBACK path, not Vision-assisted hybrid accuracy."
    elif hy_over is None or fb_over is None:
        conclusion = f"HYBRID coverage is {execution_provenance['hybrid_percent']}% of executed model beams. Subset overall scores are not both applicable; full-population overall is {full_over}."
    elif float(hy_over) > float(fb_over):
        conclusion = f"HYBRID-only overall {hy_over}% is higher than FALLBACK-only {fb_over}%. Full-population overall is {full_over}%. This is subset evidence, not a historical comparison."
    elif float(hy_over) < float(fb_over):
        conclusion = f"HYBRID-only overall {hy_over}% is lower than FALLBACK-only {fb_over}%. Full-population overall is {full_over}%. Live Vision coverage did not improve the measured subset overall vs fallback."
    else:
        conclusion = f"HYBRID-only and FALLBACK-only overall are both {hy_over}%. Full-population overall is {full_over}."

    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": decision,
        "live_completion": live_completion,
        "pass_fail": "PASS" if decision != "FAILED" else "FAIL",
        "mode": mode_u,
        "live_claude_call": live_enabled,
        "runtime_s": runtime_s,
        "population": pop,
        "visual_sources": visual,
        "eligibility_counts": eligibility,
        "live_execution": {
            "mode": mode_u,
            "beams": [{"beam_id": c.get("beam_id"), **(c.get("live") or {})} for c in calcs],
            "checkpoint": ck,
        },
        "hybrid_calculations": calcs,
        "splits": splits,
        "execution_provenance": execution_provenance,
        "live_summary": live_sum,
        "vision_coverage": {
            **counts,
            "claude_attempted": live_sum.get("attempted"),
            "api_success": live_sum.get("api_success"),
            "api_failed": live_sum.get("api_failed"),
            "schema_valid": live_sum.get("schema_valid"),
            "semantic_usable": live_sum.get("semantic_usable"),
        },
        "vision_failures": vis_fail,
        "semantic_fields": semantic_field_breakdown(full_k),
        "provenance": prov,
        "semantic_errors": sem,
        "engineering_errors": eng,
        "stirrup_errors": stir,
        "spacer_report": spacers,
        "error_taxonomy": tax,
        "limitations": limitations,
        "conclusion": conclusion,
        "anti_hardcoding": anti,
        "unit_tests": unit,
        "fingerprints": fp_cmp,
        "prior_phase_unit_ok": frozen_units,
        "production": {
            "production_mutation_count": 0 if fp_cmp.get("unchanged") else 1,
            "production_write": PRODUCTION_WRITE,
            "production_action": PRODUCTION_ACTION,
            "engineering_changes": ENGINEERING_CHANGES,
            "shadow_only": SHADOW_ONLY,
            "live_claude_call": live_enabled,
            "production_mutation_delta": 0 if fp_cmp.get("unchanged") else 1,
            "estimator_unchanged": after.get("estimator_workbook") == est_before,
        },
        "output_root": str(out_root),
    }
    write_reports(out_root=out_root, result=result)
    pdf_path = write_pdf(out_root=out_root)
    result["pdf_path"] = str(pdf_path)
    slim_path = out_root / "P2.6.10-E.2_RESULTS.json"
    slim = json.loads(slim_path.read_text(encoding="utf-8"))
    slim["pdf_path"] = str(pdf_path)
    slim_path.write_text(json.dumps(slim, indent=2, default=str), encoding="utf-8")
    _log(f"  decision={decision} live_completion={live_completion} hybrid={len(hy_ids)} fallback={len(fb_ids)} runtime_s={runtime_s}")
    return result


__all__ = ["run_phase_p2610e2"]
