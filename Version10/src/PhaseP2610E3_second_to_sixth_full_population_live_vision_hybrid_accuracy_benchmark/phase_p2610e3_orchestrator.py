"""P2.6.10-E.3 orchestrator. Default OFFLINE_VALIDATION. Live Claude only in LIVE_BENCHMARK."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.benchmark_mapper import calcs_to_workbook
from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.error_analyzers import (
    engineering_errors,
    semantic_errors,
    spacer_report,
    stirrup_errors,
)
from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.provenance_analyzer import analyze as analyze_provenance
from PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.eligibility import evaluate_population

from .anti_hardcoding import run_anti_hardcoding
from .config import (
    DEFAULT_MODE,
    ENGINEERING_CHANGES,
    FIFTH_SET_KEY,
    GATE_VERSION,
    INCLUDED_SET_KEYS,
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
    PROV_NEW,
    PROV_NOT_AVAILABLE,
    PROV_RETRIED,
    PROV_REUSED,
    SHADOW_ONLY,
)
from .metrics import kpi_block, score_set
from .population import discover_all_sets, slim_set_population
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
from .vision_loop import execute_set, fifth_reuse_gate
from .visual_sources import discover_visual_sources

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _cohort_ids(calcs, kind: str) -> List[str]:
    return [str(c.get("beam_id")) for c in calcs if c.get("provenance_kind") == kind]


def _live_summary(calcs) -> Dict[str, Any]:
    attempted = api_ok = api_fail = schema_ok = usable = retries = 0
    new_live = reused = retried = not_available = 0
    cost_in = cost_out = 0
    for c in calcs:
        live = c.get("live") or {}
        full = c.get("live_full") or {}
        prov = str(live.get("call_provenance") or "")
        if live.get("called"):
            attempted += 1
            retries += int(live.get("retry_count") or 0)
            if live.get("api_success"):
                api_ok += 1
            if live.get("failure_category") == "API_FAILED":
                api_fail += 1
            usage = full.get("usage") or (live.get("usage") if isinstance(live.get("usage"), dict) else {}) or {}
            try:
                cost_in += int(usage.get("input_tokens") or usage.get("input") or 0)
                cost_out += int(usage.get("output_tokens") or usage.get("output") or 0)
            except (TypeError, ValueError):
                pass
        if live.get("schema_valid"):
            schema_ok += 1
        if live.get("semantic_usable"):
            usable += 1
        if prov == PROV_REUSED:
            reused += 1
        elif prov == PROV_RETRIED:
            retried += 1
        elif prov == PROV_NEW:
            new_live += 1
        elif prov == PROV_NOT_AVAILABLE:
            not_available += 1
    return {
        "attempted": attempted,
        "api_success": api_ok,
        "api_failed": api_fail,
        "schema_valid": schema_ok,
        "semantic_usable": usable,
        "retries": retries,
        "new_live": new_live,
        "reused": reused,
        "retried": retried,
        "not_available": not_available,
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
        "LIVE_DISABLED": 0,
        "OTHER": 0,
    }
    for c in calcs:
        live = c.get("live") or {}
        cat = str(live.get("failure_category") or "")
        if live.get("semantic_usable"):
            continue
        if cat in counts:
            counts[cat] += 1
        elif cat and cat not in ("OK", "None"):
            counts["OTHER"] += 1
    return {"counts": counts}


def _merge_live(parts: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = {
        "attempted": 0,
        "api_success": 0,
        "api_failed": 0,
        "schema_valid": 0,
        "semantic_usable": 0,
        "retries": 0,
        "new_live": 0,
        "reused": 0,
        "retried": 0,
        "not_available": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }
    for p in parts:
        for k in out:
            out[k] += int(p.get(k) or 0)
    return out


def run_phase_p2610e3(
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
            raise RuntimeError(f"P2.6.10-E.3 unit tests failed: {failed}")
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
        raise RuntimeError(f"P2.6.10-E.3 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-E.3 runtime leakage: {leak.get('hits')}")

    pop_all = discover_all_sets(v10)
    if not pop_all.get("ok"):
        reasons = {k: (v.get("reason") or "FAIL") for k, v in (pop_all.get("by_set") or {}).items() if not v.get("ok")}
        raise RuntimeError(f"P2.6.10-E.3 fail-closed population: {reasons}")

    bundle: Dict[str, Path] = {}
    for key, pop in (pop_all.get("by_set") or {}).items():
        if pop.get("r13_path"):
            bundle[f"r13_{key}"] = Path(pop["r13_path"])
        if pop.get("estimator_path"):
            bundle[f"estimator_{key}"] = Path(pop["estimator_path"])
        if pop.get("run_root"):
            bundle[f"steel_{key}"] = Path(pop["run_root"]) / "data" / "output" / "Production_Output" / "steel_weight_summary.json"
            bundle[f"bbs_{key}"] = Path(pop["run_root"]) / "data" / "output" / "Production_Output" / "bbs_summary.json"
    fp_paths = fingerprint_paths(v10, bundle)
    before = capture_fingerprints(fp_paths)

    anti = run_anti_hardcoding(package_dir=pkg, tmp=out_root / "_anti_tmp")
    fifth_pop = (pop_all.get("by_set") or {}).get(FIFTH_SET_KEY) or {}
    fifth_reuse = fifth_reuse_gate(v10=v10, current_ids=fifth_pop.get("model_beam_ids") or [])
    _log(f"  fifth_reuse={fifth_reuse.get('decision')} allowed={fifth_reuse.get('allowed')}")

    by_set: Dict[str, Any] = {}
    live_parts: List[Dict[str, Any]] = []
    for set_key in INCLUDED_SET_KEYS:
        pop = (pop_all.get("by_set") or {})[set_key]
        beam_ids = list(pop.get("model_beam_ids") or [])
        catalog = (pop.get("catalog") or {}).get("by_id") or {}
        visual = discover_visual_sources(v10, set_key=set_key, beam_ids=beam_ids, run_root=pop.get("run_root"))
        eligibility = evaluate_population(visual)
        _log(
            f"  {set_key}: model={len(beam_ids)} visual={visual.get('available_count')} "
            f"eligible={(eligibility.get('counts') or {}).get('VISION_ELIGIBLE')}"
        )
        calcs = execute_set(
            v10=v10,
            out_root=out_root,
            set_key=set_key,
            beam_ids=beam_ids,
            catalog=catalog,
            eligibility=eligibility,
            mode=mode_u,
            client_override=client_override if live_enabled else None,
            e2_reuse_allowed=bool(set_key == FIFTH_SET_KEY and fifth_reuse.get("allowed")),
        )
        model_wb = calcs_to_workbook(calcs, source_path=f"shadow-hybrid-{set_key.lower()}-e3")
        truth = pop.get("truth") or {}
        hy_ids = _cohort_ids(calcs, KIND_HYBRID)
        fb_ids = _cohort_ids(calcs, KIND_FALLBACK)
        scores = score_set(
            drawing_set=str(pop.get("drawing_set") or f"{set_key} Set Drawings"),
            estimator=truth.get("workbook"),
            model_wb=model_wb,
            hybrid_ids=hy_ids,
            fallback_ids=fb_ids,
        )
        full_k = ((scores.get("raw_splits") or {}).get("FULL_POPULATION") or {}).get("kpis") or {}
        live_sum = _live_summary(calcs)
        live_parts.append(live_sum)
        vis_fail = _vision_failures(calcs)
        prov = analyze_provenance(calcs)
        sem = semantic_errors(
            bar_matching=full_k.get("bar_matching") or {},
            beam_matching=full_k.get("beam_matching") or {},
            calcs=calcs,
        )
        eng = engineering_errors(calcs=calcs, bar_matching=full_k.get("bar_matching") or {})
        stir = stirrup_errors(calcs=calcs, bar_matching=full_k.get("bar_matching") or {})
        spacers = spacer_report(calcs=calcs)
        by_set[set_key] = {
            "population": pop,
            "visual": visual,
            "eligibility": eligibility,
            "calcs": calcs,
            "scores": scores,
            "live_summary": live_sum,
            "vision_failures": vis_fail,
            "provenance": prov,
            "semantic_errors": sem,
            "engineering_errors": eng,
            "stirrup_errors": stir,
            "spacer_report": spacers,
            "hybrid_ids": hy_ids,
            "fallback_ids": fb_ids,
        }

    live_all = _merge_live(live_parts)
    live_all["runtime_s"] = round(time.perf_counter() - t0, 3)
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
        "E.2": prior_phase_unit_ok(v10, "PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark", 1),
    }
    frozen_ok = all(v.get("ok") for v in frozen_units.values())
    runtime_s = round(time.perf_counter() - t0, 3)
    live_all["runtime_s"] = runtime_s

    hy_n = sum(len(by_set[k]["hybrid_ids"]) for k in INCLUDED_SET_KEYS)
    fb_n = sum(len(by_set[k]["fallback_ids"]) for k in INCLUDED_SET_KEYS)
    limitations = ["ESTIMATOR_WORKBOOK_MAPPING_LIMITATION", "FIRST_SET_EXCLUDED", "SHADOW_ONLY_NOT_PRODUCTION"]
    if not live_enabled:
        limitations.append("OFFLINE_VALIDATION_NO_LIVE_CALLS")
    if fb_n:
        limitations.append("FALLBACK_POPULATION_PRESENT")
    if live_all.get("api_failed"):
        limitations.append("API_FAILURES")
    if not fifth_reuse.get("allowed"):
        limitations.append("FIFTH_E2_REUSE_NOT_PROVEN")

    if not unit.get("success") or not fp_cmp.get("unchanged") or not anti.get("ok") or not intact.get("ok") or not frozen_ok:
        decision = "FAILED"
    elif live_enabled:
        decision = "PASS_WITH_LIMITATIONS" if limitations else "PASS"
    else:
        decision = "PARTIAL"

    conclusion = (
        "This benchmark reports current hybrid architecture performance on Second through Sixth sets. "
        "It is not a historical improvement comparison and not a production-readiness claim. "
        f"HYBRID beams={hy_n}, FALLBACK beams={fb_n}. Vision API success is not engineering accuracy."
    )

    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": decision,
        "pass_fail": "PASS" if decision != "FAILED" else "FAIL",
        "mode": mode_u,
        "live_claude_call": live_enabled,
        "runtime_s": runtime_s,
        "population_all": pop_all,
        "by_set": by_set,
        "fifth_reuse": fifth_reuse,
        "live_summary": live_all,
        "hybrid_execution_manifest": {
            "hybrid_count": hy_n,
            "fallback_count": fb_n,
            "by_set": {k: {"hybrid": len(by_set[k]["hybrid_ids"]), "fallback": len(by_set[k]["fallback_ids"])} for k in INCLUDED_SET_KEYS},
        },
        "vision_execution_manifest": {k: by_set[k]["live_summary"] for k in INCLUDED_SET_KEYS},
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
        },
        "output_root": str(out_root),
    }
    write_reports(out_root=out_root, result=result)
    _log(f"  decision={decision} hybrid={hy_n} fallback={fb_n} runtime_s={runtime_s}")
    _log(f"  docx={result.get('docx_path')}")
    _log(f"  pdf={result.get('pdf_path')}")
    return result


__all__ = ["run_phase_p2610e3"]
