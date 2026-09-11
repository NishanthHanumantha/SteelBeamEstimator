"""P2.6.10-D.2 orchestrator. Shadow hybrid application of the D.1 contract."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.vision_normalizer import (
    extract_deterministic_groups,
    extract_vision_payload,
)

from .anti_hardcoding import run_anti_hardcoding
from .audit import collect_conflicts, collect_fallbacks, collect_matching
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
from .discovery import load_authority_contract, load_d1_population
from .metrics import build_metrics
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_artefacts_intact,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)
from .report import write_beam_review, write_reports
from .resolver import resolve_hybrid_beam
from .unit_tests import run_unit_tests

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run_phase_p2610d2(
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
            raise RuntimeError(f"P2.6.10-D.2 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-D.2 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-D.2 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)

    contract = load_authority_contract(v10)
    if not contract.get("ok"):
        raise RuntimeError(f"P2.6.10-D.2 fail-closed: {contract.get('reason')}")
    pop = load_d1_population(v10)
    _log(f"  discovered={pop.get('discovered_count')} expected={EXPECTED_POPULATION_SIZE} ok={pop.get('ok')}")
    if not pop.get("ok"):
        raise RuntimeError(f"P2.6.10-D.2 fail-closed population: {pop.get('reason')} count={pop.get('discovered_count')}")

    hybrid_results = []
    conflicts: List[Dict[str, Any]] = []
    fallbacks: List[Dict[str, Any]] = []
    matching_audits = []
    resolution_audits = []
    for rec in pop.get("records") or []:
        vis = extract_vision_payload(rec.get("parsed") or {})
        det = extract_deterministic_groups(rec.get("detected_groups") or rec.get("expected_groups") or [])
        hybrid = resolve_hybrid_beam(
            beam_id=str(rec.get("beam_id")),
            vision=vis,
            deterministic=det,
            source_provenance={
                "source_phase": rec.get("source_phase"),
                "source_path": rec.get("source_path"),
                "schema_version": rec.get("schema_version"),
            },
        )
        beam_conflicts = collect_conflicts(hybrid)
        beam_fallbacks = collect_fallbacks(hybrid)
        beam_match = collect_matching(hybrid)
        audit = {
            "beam_id": rec.get("beam_id"),
            "conflicts": beam_conflicts,
            "fallbacks": beam_fallbacks,
            "matching": beam_match,
            "target": hybrid.get("target_identity"),
        }
        hybrid_results.append(hybrid)
        conflicts.extend(beam_conflicts)
        fallbacks.extend(beam_fallbacks)
        matching_audits.append(beam_match)
        resolution_audits.append(audit)
        write_beam_review(out_root=out_root, rec=rec, hybrid=hybrid, audit=audit)
        gm = hybrid.get("group_matching") or {}
        _log(f"  {rec.get('beam_id')} matched={gm.get('matched')} vo={gm.get('vision_only')} do={gm.get('deterministic_only')} amb={gm.get('ambiguous')}")

    metrics = build_metrics(hybrid_results)
    anti = run_anti_hardcoding(package_dir=pkg)
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    intact = prior_artefacts_intact(v10)
    prior_ok = {
        "p2610c5": prior_phase_unit_ok(v10, "PhaseP2610C5_stratified_vision_semantic_benchmark", 21),
        "p2610d1": prior_phase_unit_ok(v10, "PhaseP2610D1_vision_semantic_contract_hybrid_foundation", 32),
    }
    runtime_s = round(time.perf_counter() - t0, 3)
    decision = "PASS"
    if not unit.get("success") or not fp_cmp.get("unchanged") or not anti.get("ok") or not intact.get("ok") or not pop.get("ok"):
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
        "authority_contract": contract.get("contract"),
        "population": pop,
        "hybrid_results": hybrid_results,
        "conflicts": conflicts,
        "fallbacks": fallbacks,
        "matching_audits": matching_audits,
        "resolution_audits": resolution_audits,
        "metrics": metrics,
        "manifest": {
            "expected_population": EXPECTED_POPULATION_SIZE,
            "discovered": pop.get("discovered_count"),
            "contract_version": (contract.get("contract") or {}).get("contract_version"),
            "live_claude_call": LIVE_CLAUDE_CALL,
            "production_write": PRODUCTION_WRITE,
        },
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
        },
        "output_root": str(out_root),
    }
    write_reports(out_root=out_root, result=result)
    _log(f"  decision={decision} runtime_s={runtime_s}")
    return result


__all__ = ["run_phase_p2610d2"]
