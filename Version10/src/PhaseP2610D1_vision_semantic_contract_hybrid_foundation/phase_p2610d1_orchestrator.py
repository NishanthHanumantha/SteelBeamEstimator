"""P2.6.10-D.1 orchestrator. Shadow hybrid contract over existing C.3/C.5 artefacts."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .anti_hardcoding import run_anti_hardcoding
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
)
from .discovery import discover_benchmark_population
from .hybrid_authority_contract import authority_contract
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_artefacts_intact,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)
from .report import collect_validations, field_counts, validation_failures, write_reports
from .resolver import resolve_beam
from .unit_tests import run_unit_tests
from .vision_normalizer import extract_deterministic_groups, extract_vision_payload

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run_phase_p2610d1(
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
            raise RuntimeError(f"P2.6.10-D.1 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-D.1 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-D.1 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)

    contract = authority_contract()
    pop = discover_benchmark_population(v10)
    _log(f"  discovered={pop.get('deduplicated_count')} ids={pop.get('beam_ids')}")

    hybrid_results = []
    comparisons = []
    for rec in pop.get("records") or []:
        vis = extract_vision_payload(rec.get("parsed") or {})
        det = extract_deterministic_groups(rec.get("detected_groups") or rec.get("expected_groups") or [])
        resolved = resolve_beam(
            beam_id=str(rec.get("beam_id")),
            vision=vis,
            deterministic=det,
            source_provenance={
                "source_phase": rec.get("source_phase"),
                "source_path": rec.get("source_path"),
                "schema_version": rec.get("schema_version"),
                "dedupe": rec.get("dedupe"),
            },
        )
        hybrid_results.append(resolved)
        comparisons.append(
            {
                "beam_id": rec.get("beam_id"),
                "source_phase": rec.get("source_phase"),
                "vision_group_count": len(vis.get("groups") or []),
                "deterministic_group_count": len(det.get("groups") or []),
                "resolution_summary": resolved.get("resolution_summary"),
            }
        )
        _log(f"  {rec.get('beam_id')} vis={len(vis.get('groups') or [])} det={len(det.get('groups') or [])} vo={resolved['resolution_summary']['vision_only_groups']} do={resolved['resolution_summary']['deterministic_only_groups']}")

    validations = collect_validations(hybrid_results)
    metrics = {
        "field_counts": field_counts(hybrid_results),
        "validation_failures": validation_failures(validations),
        "vision_only_groups": sum(r["resolution_summary"]["vision_only_groups"] for r in hybrid_results),
        "deterministic_only_groups": sum(r["resolution_summary"]["deterministic_only_groups"] for r in hybrid_results),
        "possible_duplicates": sum(r["resolution_summary"]["possible_duplicates"] for r in hybrid_results),
        "matched_groups": sum(r["resolution_summary"]["matched_groups"] for r in hybrid_results),
    }
    anti = run_anti_hardcoding(package_dir=pkg)
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    intact = prior_artefacts_intact(v10)
    prior_ok = {
        "p266": prior_phase_unit_ok(v10, "PhaseP266_semantic_longitudinal_resolver", 36),
        "p2610a": prior_phase_unit_ok(v10, "PhaseP2610A_beam_region_crop_audit", 14),
        "p2610b": prior_phase_unit_ok(v10, "PhaseP2610B_adaptive_beam_detail_crop", 18),
        "p2610b1": prior_phase_unit_ok(v10, "PhaseP2610B1_population_generalization", 16),
        "p2610c1c2": prior_phase_unit_ok(v10, "PhaseP2610C1C2_evidence_inventory_candidate_selection", 21),
        "p2610c3": prior_phase_unit_ok(v10, "PhaseP2610C3_visual_completeness_claude_shadow", 19),
        "p2610c4": prior_phase_unit_ok(v10, "PhaseP2610C4_shadow_truth_reconciliation_benchmark_calibration", 22),
        "p2610c5": prior_phase_unit_ok(v10, "PhaseP2610C5_stratified_vision_semantic_benchmark", 21),
    }
    decision = "PASS_WITH_LIMITATIONS"
    if not unit.get("success") or not fp_cmp.get("unchanged") or not anti.get("ok") or not intact.get("ok"):
        decision = "FAIL"

    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": decision,
        "pass_fail": "PASS" if decision == "PASS_WITH_LIMITATIONS" else "FAIL",
        "live_claude_call": LIVE_CLAUDE_CALL,
        "authority_contract": contract,
        "population": pop,
        "hybrid_results": hybrid_results,
        "comparisons": comparisons,
        "validations": validations,
        "audit": {
            "beams": [
                {
                    "beam_id": r.get("beam_id"),
                    "source": (r.get("source_provenance") or {}).get("source_phase"),
                    "target": r.get("target_identity"),
                    "summary": r.get("resolution_summary"),
                }
                for r in hybrid_results
            ]
        },
        "metrics": metrics,
        "anti_hardcoding": anti,
        "unit_tests": unit,
        "fingerprints": fp_cmp,
        "prior_phase_units": {k: bool(v.get("ok")) for k, v in prior_ok.items()},
        "performance": {"total_runtime_s": round(time.perf_counter() - t0, 3)},
        "production": {
            "production_mutation_count": 0 if fp_cmp.get("unchanged") else 1,
            "production_write": PRODUCTION_WRITE,
            "production_action": PRODUCTION_ACTION,
            "engineering_changes": ENGINEERING_CHANGES,
            "shadow_only": SHADOW_ONLY,
            "live_claude_call": LIVE_CLAUDE_CALL,
        },
        "output_root": str(out_root),
    }
    write_reports(out_root=out_root, result=result)
    _log(f"  decision={decision}")
    return result


__all__ = ["run_phase_p2610d1"]
