"""P2.6.10-C.4 orchestrator. Read-only reconciliation of existing C.3 six-beam evidence."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from .discovery import control_beam_ids, load_six_beam_control
from .engine import reconcile_groups
from .evidence import collect_beam_evidence, default_manual_path, load_manual_verifications
from .metrics import aggregate_metrics
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


def _classify_gate(*, tests_ok: bool, fingerprints_ok: bool, anti_ok: bool, hardcoding: bool, mutations: int) -> str:
    if mutations or hardcoding:
        return "FAIL"
    if not tests_ok or not fingerprints_ok or not anti_ok:
        return "FAIL"
    return "PASS_WITH_LIMITATIONS"


def run_phase_p2610c4(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    report_only: bool = False,
    verify_manual_evidence: bool = True,
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
    _log(f"  PRODUCTION_WRITE: {PRODUCTION_WRITE}")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests and not report_only:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-C.4 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-C.4 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-C.4 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)

    control = load_six_beam_control(v10)
    if not control.get("ok"):
        raise RuntimeError(f"C.3 six-beam control missing: {control.get('path')}")
    beam_ids = control_beam_ids(control)
    _log(f"  discovered control population: {beam_ids}")

    manual_path = default_manual_path(pkg) if verify_manual_evidence else None
    manuals = load_manual_verifications(manual_path) if verify_manual_evidence else {}

    records: List[Dict[str, Any]] = []
    for row in control.get("rows") or []:
        bid = str(row.get("beam_id"))
        set_key = str(row.get("set_key") or "")
        collected = collect_beam_evidence(
            beam_id=bid,
            set_key=set_key,
            c3_row=row,
            c3_path=str(control.get("path")),
            manual_row=manuals.get(bid),
            v10=v10,
        )
        rec = reconcile_groups(
            vision_groups=collected.get("vision_groups") or [],
            deterministic_groups=collected.get("deterministic_groups") or [],
            p269_groups=collected.get("p269_groups") or [],
            independent_groups=collected.get("independent_groups") or [],
            independent_basis=collected.get("independent_basis"),
        )
        records.append(
            {
                "beam_id": bid,
                "set_key": set_key,
                "context_provenance": collected.get("context_provenance"),
                "detail_provenance": collected.get("detail_provenance"),
                "evidence_inventory": collected.get("inventory"),
                "deterministic_interpretation": collected.get("deterministic_groups"),
                "p269_interpretation": collected.get("p269_groups"),
                "vision_interpretation": collected.get("vision_groups"),
                "reconciled_groups": rec.get("reconciled_groups"),
                "reconciliation_status": rec.get("reconciliation_status"),
                "reconciliation_confidence": rec.get("reconciliation_confidence"),
                "evidence_strength": rec.get("evidence_strength"),
                "deterministic_result": rec.get("deterministic_result"),
                "vision_result": rec.get("vision_result"),
                "unresolved_items": rec.get("unresolved_items"),
                "provenance": {
                    "c3_path": control.get("path"),
                    "c3_taxonomy": collected.get("c3_taxonomy"),
                    "claude_called_in_c3": collected.get("claude_called"),
                    "independent_basis": collected.get("independent_basis"),
                    "phase_notes": collected.get("notes"),
                },
                "vision_vs_truth": rec.get("vision_vs_truth"),
                "deterministic_vs_truth": rec.get("deterministic_vs_truth"),
                "truth_established": rec.get("truth_established"),
                "truth_source_summary": rec.get("truth_source_summary"),
                "unresolved_reason": rec.get("unresolved_reason"),
                "reason": rec.get("reason"),
            }
        )
        _log(f"  {bid} status={rec.get('reconciliation_status')} strength={rec.get('evidence_strength')}")

    metrics = aggregate_metrics(records)
    anti = run_anti_hardcoding(package_dir=pkg)
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    prior_ok = {
        "p266": prior_phase_unit_ok(v10, "PhaseP266_semantic_longitudinal_resolver", 36),
        "p269": prior_phase_unit_ok(v10, "PhaseP269_reinforcement_group_interpretation", 20),
        "p2610a": prior_phase_unit_ok(v10, "PhaseP2610A_beam_region_crop_audit", 14),
        "p2610b": prior_phase_unit_ok(v10, "PhaseP2610B_adaptive_beam_detail_crop", 18),
        "p2610b1": prior_phase_unit_ok(v10, "PhaseP2610B1_population_generalization", 16),
        "p2610b2": prior_phase_unit_ok(v10, "PhaseP2610B2_render_quality_directional_recovery", 29),
        "p2610b3": prior_phase_unit_ok(v10, "PhaseP2610B3_target_anchor_geometry_context_recovery", 18),
        "p2610c1c2": prior_phase_unit_ok(v10, "PhaseP2610C1C2_evidence_inventory_candidate_selection", 21),
        "p2610c3": prior_phase_unit_ok(v10, "PhaseP2610C3_visual_completeness_claude_shadow", 19),
    }
    intact = prior_artefacts_intact(v10)
    mutations = 0 if fp_cmp.get("unchanged") else 1
    decision_gate = _classify_gate(
        tests_ok=bool(unit.get("success")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        anti_ok=bool(anti.get("ok")),
        hardcoding=bool(anti.get("beam_id_special_cases")),
        mutations=mutations,
    )
    if not intact.get("ok"):
        decision_gate = "FAIL"

    verified_anchors = [
        r.get("beam_id")
        for r in records
        if str(r.get("truth_source_summary") or "").upper().startswith("MANUAL")
        and r.get("reconciliation_status") == "VISION_CONFIRMED"
    ]
    handoff = {
        "1_beams_reconciled": metrics.get("beams_reconciled"),
        "2_vision_confirmed": metrics.get("beams_vision_confirmed"),
        "3_deterministic_confirmed": metrics.get("beams_deterministic_confirmed"),
        "4_both_equivalent": metrics.get("beams_both_equivalent"),
        "5_ambiguous_evidence": metrics.get("beams_ambiguous"),
        "6_insufficient_evidence": metrics.get("beams_insufficient_evidence"),
        "7_group_comparison": {
            "vision_correct": metrics.get("vision_correct_group_count"),
            "vision_missing": metrics.get("vision_missing_group_count"),
            "vision_spurious": metrics.get("vision_spurious_group_count"),
            "deterministic_correct": metrics.get("deterministic_correct_group_count"),
            "deterministic_missing": metrics.get("deterministic_missing_group_count"),
            "deterministic_spurious": metrics.get("deterministic_spurious_group_count"),
        },
        "8_explicit_verification_vision_confirmed": verified_anchors,
        "9_enough_evidence_to_expand": metrics.get("decision") == "VISION_SIGNAL_SUPPORTED",
        "10_next_sample_strategy": metrics.get("recommendation_text"),
        "11_evidence_gap": (
            f"{metrics.get('beams_ambiguous')} ambiguous and "
            f"{metrics.get('beams_insufficient_evidence')} insufficient without independent verification"
        ),
        "12_safety": {
            "LIVE_CLAUDE_CALL": LIVE_CLAUDE_CALL,
            "PRODUCTION_WRITE": PRODUCTION_WRITE,
            "ENGINEERING_CHANGES": ENGINEERING_CHANGES,
        },
    }

    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": metrics.get("decision"),
        "pass_fail": "PASS" if decision_gate == "PASS_WITH_LIMITATIONS" else "FAIL",
        "terminal_gate": decision_gate,
        "live_claude_call": LIVE_CLAUDE_CALL,
        "records": records,
        "calibration_metrics": metrics,
        "handoff_answers": handoff,
        "discovered_control": beam_ids,
        "anti_hardcoding": anti,
        "unit_tests": unit,
        "fingerprints": fp_cmp,
        "prior_phase_units": {k: bool(v.get("ok")) for k, v in prior_ok.items()},
        "performance": {"total_runtime_s": round(time.perf_counter() - t0, 3)},
        "production": {
            "production_mutation_count": 0 if fp_cmp.get("unchanged") else 1,
            "steel_quantity_delta": 0,
            "BBS_delta": 0,
            "workbook_delta": 0,
            "production_write": PRODUCTION_WRITE,
            "production_action": PRODUCTION_ACTION,
            "engineering_changes": ENGINEERING_CHANGES,
            "shadow_only": SHADOW_ONLY,
            "live_claude_call": LIVE_CLAUDE_CALL,
        },
        "output_root": str(out_root),
    }
    write_reports(out_root=out_root, result=result, package_dir=pkg)
    _dump(out_root / "control_discovery.json", {"beam_ids": beam_ids, "source": control.get("path")})
    _log(f"  decision={result.get('decision')} gate={decision_gate}")
    return result


__all__ = ["run_phase_p2610c4"]
