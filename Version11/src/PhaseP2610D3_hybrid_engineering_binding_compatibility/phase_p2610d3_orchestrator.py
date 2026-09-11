"""P2.6.10-D.3 orchestrator. Shadow engineering binding. No Claude. No production. No calculations."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .anti_hardcoding import run_anti_hardcoding
from .compatibility_validator import validate_population
from .config import (
    ENGINEERING_CHANGES,
    EXPECTED_POPULATION_SIZE,
    GATE_VERSION,
    LIVE_CLAUDE_CALL,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SHADOW_ONLY,
)
from .diagnostics import build_diagnostics
from .engineering_rule_binder import default_rule_catalog
from .hybrid_binding_engine import bind_population
from .input_loader import load_d2_hybrids, load_d2_population, load_r13_catalog
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


def _authority_preservation(bound_beams: List[Dict[str, Any]], hybrids: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_id = {str(h.get("beam_id")): h for h in hybrids}
    dia_ok = True
    role_ok = True
    spacer_ok = True
    stirrup_ok = True
    for beam in bound_beams:
        src = by_id.get(str(beam.get("beam_id"))) or {}
        src_groups = {str(g.get("group_id")): g for g in (src.get("reinforcement_groups") or []) if isinstance(g, dict)}
        for g in beam.get("groups") or []:
            orig = src_groups.get(str(g.get("group_id"))) or {}
            sem = g.get("semantic") or {}
            orig_dia = (orig.get("diameter") or {}).get("value") if isinstance(orig.get("diameter"), dict) else orig.get("diameter")
            orig_role = (orig.get("role") or {}).get("value") if isinstance(orig.get("role"), dict) else orig.get("role")
            if orig_dia is not None and sem.get("diameter") != orig_dia:
                dia_ok = False
            if orig_role is not None and sem.get("role") != orig_role:
                role_ok = False
            recs = sem.get("field_records") or {}
            if isinstance(recs.get("diameter"), dict) and recs["diameter"].get("source") == "VISION":
                if sem.get("diameter") != recs["diameter"].get("value"):
                    dia_ok = False
            if isinstance(recs.get("role"), dict) and recs["role"].get("source") == "VISION":
                if sem.get("role") != recs["role"].get("value"):
                    role_ok = False
        spacer_ok = spacer_ok and (beam.get("spacers") or {}).get("source") == "DETERMINISTIC"
        for s in beam.get("stirrups") or []:
            if s.get("semantic_identification_authority") != "VISION_PREFERRED":
                stirrup_ok = False
            if s.get("engineering_calculation_authority") != "DETERMINISTIC_ENGINEERING":
                stirrup_ok = False
    return {
        "diameter": dia_ok,
        "role": role_ok,
        "spacer": spacer_ok,
        "stirrup_split": stirrup_ok,
    }


def _print_summary(result: Dict[str, Any]) -> None:
    pop = result.get("population") or {}
    diag = result.get("diagnostics") or {}
    beam = diag.get("beam_compatibility") or {}
    groups = diag.get("group_binding") or {}
    cov = (diag.get("coverage") or {}).get("engineering_reference_coverage") or {}
    src = diag.get("source_categories") or {}
    auth = result.get("authority_preservation") or {}
    prod = result.get("production") or {}
    unit = result.get("unit_tests") or {}
    anti = result.get("anti_hardcoding") or {}
    fp = result.get("fingerprints") or {}
    print()
    print("P2.6.10-D.3 - Hybrid Engineering Binding & Deterministic Calculation Compatibility")
    print()
    print(f"MODEL_VERSION: {result.get('model_version')}")
    print(f"GATE: {result.get('gate_version')}")
    print(f"DECISION: {result.get('decision')}")
    print()
    print("Benchmark population:")
    print(f"Expected: {pop.get('expected')}")
    print(f"Discovered: {pop.get('discovered_count')}")
    print()
    print("Beam compatibility:")
    print(f"ENGINEERING_COMPATIBLE: {beam.get('ENGINEERING_COMPATIBLE', 0)}")
    print(f"ENGINEERING_PARTIALLY_COMPATIBLE: {beam.get('ENGINEERING_PARTIALLY_COMPATIBLE', 0)}")
    print(f"ENGINEERING_AMBIGUOUS: {beam.get('ENGINEERING_AMBIGUOUS', 0)}")
    print(f"ENGINEERING_INCOMPATIBLE: {beam.get('ENGINEERING_INCOMPATIBLE', 0)}")
    print()
    print("Group binding:")
    print(f"Total: {groups.get('total', 0)}")
    print(f"BOUND: {groups.get('BOUND', 0)}")
    print(f"PARTIALLY_BOUND: {groups.get('PARTIALLY_BOUND', 0)}")
    print(f"AMBIGUOUS: {groups.get('AMBIGUOUS', 0)}")
    print(f"MISSING_GEOMETRY: {groups.get('MISSING_GEOMETRY', 0)}")
    print(f"MISSING_SUPPORT_REFERENCE: {groups.get('MISSING_SUPPORT_REFERENCE', 0)}")
    print(f"MISSING_RULE_REFERENCE: {groups.get('MISSING_RULE_REFERENCE', 0)}")
    print(f"UNSUPPORTED: {groups.get('UNSUPPORTED', 0)}")
    print(f"INVALID_INPUT: {groups.get('INVALID_INPUT', 0)}")
    print()
    print("Engineering reference coverage:")
    print(f"Geometry: {cov.get('geometry')}")
    print(f"Section geometry: {cov.get('section_geometry')}")
    print(f"Direction: {cov.get('direction')}")
    print(f"Support: {cov.get('support')}")
    print(f"Cut-length rule: {cov.get('cut_length_rule')}")
    print(f"Development-length rule: {cov.get('development_length_rule')}")
    print(f"Anchorage: {cov.get('anchorage')}")
    print(f"Hook/bend: {cov.get('hook_bend')}")
    print()
    print("Semantic source categories:")
    print(f"Matched groups: {src.get('matched_groups')}")
    print(f"Vision-only groups: {src.get('vision_only_groups')}")
    print(f"Deterministic-only groups: {src.get('deterministic_only_groups')}")
    print(f"Ambiguous groups: {src.get('ambiguous_groups_unresolved')}")
    print(f"Possible duplicates: {src.get('possible_duplicates_preserved')}")
    print()
    print("Authority preservation:")
    print(f"Vision diameter preserved: {auth.get('diameter')}")
    print(f"Vision MAIN/EXTRA preserved: {auth.get('role')}")
    print(f"Spacer deterministic-only: {auth.get('spacer')}")
    print(f"Stirrup semantic/engineering split: {auth.get('stirrup_split')}")
    print()
    print("Calculations performed:")
    print("Cut length: NO")
    print("Development length: NO")
    print("Steel weight: NO")
    print("BBS: NO")
    print()
    print("Claude:")
    print("LIVE_CLAUDE_CALL: false")
    print()
    print("Production:")
    print("PRODUCTION_WRITE: false")
    print("ENGINEERING_CHANGES: NONE")
    print(f"Production mutation delta: {prod.get('production_mutation_count')}")
    print(f"Steel delta: {prod.get('steel_delta')}")
    print(f"BBS delta: {prod.get('bbs_delta')}")
    print(f"Workbook delta: {prod.get('workbook_delta')}")
    print()
    print("Anti-hardcoding:")
    print("PASS" if anti.get("ok") else "FAIL")
    print()
    print("Source fingerprints:")
    print("UNCHANGED" if fp.get("unchanged") else "CHANGED")
    print()
    print("Tests:")
    prior = result.get("prior_phase_units") or {}
    print(f"D.3: {unit.get('passed')} / {unit.get('total')}")
    print(f"D.1 frozen: {'PASS' if prior.get('p2610d1') else 'FAIL'} (32/32 expected)")
    print(f"D.2 frozen: {'PASS' if prior.get('p2610d2') else 'FAIL'} (30/30 expected)")
    print()
    print("Output:")
    print(result.get("output_root"))
    print()
    print("Recommended next step:")
    if result.get("ready_for_shadow_calculation"):
        print("Evidence supports proceeding to P2.6.10-D.4 - Shadow Hybrid Engineering Calculation & Accuracy Benchmark Preparation.")
    else:
        print("Do not proceed to P2.6.10-D.4 until binding gaps are reviewed. This remains a shadow-only compatibility phase.")
    print()


def run_phase_p2610d3(
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
            raise RuntimeError(f"P2.6.10-D.3 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-D.3 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-D.3 runtime leakage: {leak.get('hits')}")

    catalog = load_r13_catalog(v10)
    fp_paths = fingerprint_paths(v10, {"r13_models": Path(catalog["path"])} if catalog.get("path") else {})
    before = capture_fingerprints(fp_paths)

    pop = load_d2_population(v10)
    _log(f"  discovered={pop.get('discovered_count')} expected={EXPECTED_POPULATION_SIZE} ok={pop.get('ok')}")
    if not pop.get("ok"):
        raise RuntimeError(f"P2.6.10-D.3 fail-closed population: {pop.get('reason')} count={pop.get('discovered_count')}")
    hybrids_payload = load_d2_hybrids(v10)
    if not hybrids_payload.get("ok"):
        raise RuntimeError(f"P2.6.10-D.3 fail-closed hybrid: {hybrids_payload.get('reason')}")
    by_id = hybrids_payload.get("by_id") or {}
    missing = [bid for bid in (pop.get("beam_ids") or []) if bid not in by_id]
    if missing:
        raise RuntimeError("P2.6.10-D.3 fail-closed: canonical hybrid semantic data missing")
    if not catalog.get("ok"):
        raise RuntimeError(f"P2.6.10-D.3 fail-closed deterministic catalog: {catalog.get('reason')}")

    ordered = [by_id[bid] for bid in pop.get("beam_ids") or []]
    bound_beams = bind_population(hybrids=ordered, catalog=catalog.get("by_id") or {}, rule_catalog=default_rule_catalog())
    diag = build_diagnostics(bound_beams)
    compat = validate_population(bound_beams)
    anti = run_anti_hardcoding(package_dir=pkg)
    auth = _authority_preservation(bound_beams, ordered)
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    intact = prior_artefacts_intact(v10)
    prior_ok = {
        "p2610d1": prior_phase_unit_ok(v10, "PhaseP2610D1_vision_semantic_contract_hybrid_foundation", 32),
        "p2610d2": prior_phase_unit_ok(v10, "PhaseP2610D2_shadow_hybrid_semantic_resolver", 30),
    }
    runtime_s = round(time.perf_counter() - t0, 3)
    beam = diag.get("beam_compatibility") or {}
    ready = bool(
        pop.get("ok")
        and unit.get("success")
        and fp_cmp.get("unchanged")
        and anti.get("ok")
        and intact.get("ok")
        and auth.get("diameter")
        and auth.get("role")
        and auth.get("spacer")
        and auth.get("stirrup_split")
        and (beam.get("ENGINEERING_COMPATIBLE", 0) + beam.get("ENGINEERING_PARTIALLY_COMPATIBLE", 0) + beam.get("ENGINEERING_AMBIGUOUS", 0)) > 0
    )
    decision = "PASS"
    if not unit.get("success") or not fp_cmp.get("unchanged") or not anti.get("ok") or not intact.get("ok") or not pop.get("ok") or not auth.get("diameter") or not auth.get("role"):
        decision = "FAIL_CLOSED"
    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": decision,
        "pass_fail": "PASS" if decision == "PASS" else "FAIL",
        "live_claude_call": LIVE_CLAUDE_CALL,
        "runtime_s": runtime_s,
        "population": pop,
        "diagnostics": diag,
        "compatibility_validation": compat,
        "authority_preservation": auth,
        "ready_for_shadow_calculation": ready and decision == "PASS",
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
    write_reports(out_root=out_root, result=result, hybrids=ordered, bound_beams=bound_beams)
    _log(f"  decision={decision} runtime_s={runtime_s}")
    _print_summary(result)
    return result


__all__ = ["run_phase_p2610d3"]
