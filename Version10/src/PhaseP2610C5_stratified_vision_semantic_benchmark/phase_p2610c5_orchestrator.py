"""P2.6.10-C.5 orchestrator. Stratified Fourth Set Vision sample. Shadow only."""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from .anti_hardcoding import run_anti_hardcoding
from .candidate import build_candidate
from .claude_call import call_selected_beam, smoke_api
from .comparison import compare_beam
from .config import (
    ENGINEERING_CHANGES,
    GATE_VERSION,
    MAX_SAMPLE_SIZE,
    MODE_LIVE,
    MODE_OFFLINE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SHADOW_ONLY,
    TARGET_SAMPLE_SIZE,
)
from .discovery import (
    discover_fourth_set,
    load_c3_gate_by_id,
    load_prior_control_ids,
    load_r13_detected_by_beam,
    load_selection_manifest,
)
from .length_evidence import attach_length_evidence, summarize_length_vs_role
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
from .sampler import select_sample
from .strata import classify_strata
from .unit_tests import run_unit_tests
from .vision_contract import unusable

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _metrics(records: List[Dict[str, Any]], live: bool) -> Dict[str, Any]:
    gates = Counter(r.get("c3_visual_gate_status") for r in records)
    attempted = api_ok = schema_ok = unusable_n = api_fail = schema_inv = skipped = 0
    target_m = target_d = target_u = 0
    role_mm = collapse = neighbour = 0
    vis_n = det_n = 0
    count_labels: Counter = Counter()
    stir_ag = stir_dis = 0
    length_groups: List[Dict[str, Any]] = []
    for rec in records:
        vis = rec.get("vision") or {}
        parsed = vis.get("parsed") or {}
        if vis.get("called"):
            attempted += 1
            if (vis.get("audit") or {}).get("success"):
                api_ok += 1
            else:
                api_fail += 1
            if parsed.get("usable"):
                schema_ok += 1
            else:
                unusable_n += 1
                if parsed.get("call_status") == "SCHEMA_INVALID":
                    schema_inv += 1
        else:
            skipped += 1
        cmp = rec.get("comparison") or {}
        ta = cmp.get("target_association")
        if ta == "MATCH":
            target_m += 1
        elif ta == "DISAGREE":
            target_d += 1
        else:
            target_u += 1
        vis_n += int((cmp.get("physical_group_count") or {}).get("vision") or 0)
        det_n += int((cmp.get("physical_group_count") or {}).get("deterministic") or 0)
        role_mm += int(cmp.get("role_mismatch_count") or 0)
        collapse += int(cmp.get("merged_distinct_groups") or 0)
        if parsed.get("neighbour_evidence_detected"):
            neighbour += 1
        for p in cmp.get("pairs") or []:
            count_labels[p.get("count_comparison")] += 1
        st = cmp.get("stirrup") or {}
        if st.get("agreement"):
            stir_ag += 1
        elif st.get("vision_count") or st.get("deterministic_count"):
            stir_dis += 1
        length_groups.extend(parsed.get("groups") or [])
    return {
        "gate_distribution": dict(gates),
        "attempted": attempted if live else 0,
        "skipped": skipped if live else len(records),
        "api_success": api_ok,
        "api_failed": api_fail,
        "schema_valid": schema_ok,
        "schema_invalid": schema_inv,
        "unusable": unusable_n,
        "target_match": target_m,
        "target_disagree": target_d,
        "target_unknown": target_u,
        "physical_groups": {"vision_total": vis_n, "deterministic_total": det_n},
        "layers": "see per-beam comparison",
        "specs": "see per-beam comparison",
        "counts": dict(count_labels),
        "role_mismatches": role_mm,
        "same_spec_collapse": collapse,
        "stirrups": {"agreement_beams": stir_ag, "disagreement_beams": stir_dis},
        "neighbour_flags": neighbour,
        "length_evidence": summarize_length_vs_role(length_groups),
    }


def run_phase_p2610c5(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_OFFLINE,
    client_override=None,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    pkg = Path(__file__).resolve().parent
    out_root.mkdir(parents=True, exist_ok=True)
    live = mode == MODE_LIVE
    t0 = time.perf_counter()

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode not in (MODE_OFFLINE, MODE_LIVE):
        raise RuntimeError(f"unsupported C.5 mode {mode!r}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  mode={mode} live={live} max_sample={MAX_SAMPLE_SIZE}")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        _dump(out_root / "tests" / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-C.5 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-C.5 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-C.5 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)

    fourth = discover_fourth_set(v10)
    if not fourth.get("ok"):
        raise RuntimeError(fourth.get("reason") or "FOURTH_SET_PROVENANCE_UNAVAILABLE")
    set_key = str(fourth.get("set_key"))
    fourth_ids = set(fourth.get("beam_ids") or [])
    sel_rows = load_selection_manifest(v10)
    gates = load_c3_gate_by_id(v10)
    prior_ids = load_prior_control_ids(v10)
    r13 = load_r13_detected_by_beam(v10, set_key)
    r13_by = r13.get("by_beam") or {}
    _log(f"  fourth_set n={len(fourth_ids)} prior_control={prior_ids} r13_ok={r13.get('ok')} r13_n={len(r13_by)}")

    candidates: List[Dict[str, Any]] = []
    for row in sel_rows:
        bid = str(row.get("beam_id") or "")
        if bid not in fourth_ids:
            continue
        rec = build_candidate(
            v10=v10,
            set_key=set_key,
            sel_row=row,
            gate_row=gates.get(bid),
            r13_groups=r13_by.get(bid),
        )
        rec["strata"] = classify_strata(rec)
        candidates.append(rec)

    sample = select_sample(candidates, exclude_ids=prior_ids, target_size=TARGET_SAMPLE_SIZE)
    if not sample.get("ok"):
        raise RuntimeError(sample.get("reason") or "sample_failed")
    selected = list(sample.get("selected") or [])
    if len(selected) > MAX_SAMPLE_SIZE:
        raise RuntimeError("FAIL_CLOSED_SAMPLE_CAP")
    _log(f"  selected={sample.get('selected_ids')} coverage={sample.get('strata_coverage')}")

    smoke = {"ok": True, "skipped": True}
    if live:
        smoke = smoke_api(v10)
        _log(f"  api_smoke ok={smoke.get('ok')} error={smoke.get('error')}")
        if not smoke.get("ok"):
            raise RuntimeError(f"API smoke failed: {smoke.get('error')}")

    records: List[Dict[str, Any]] = []
    for rec in selected:
        bid = rec.get("beam_id")
        if rec.get("set_key") != set_key:
            raise RuntimeError("selected beam not Fourth Set")
        ctx_ok = (rec.get("context_integrity") or {}).get("integrity_ok")
        det_ok = (rec.get("detail_integrity") or {}).get("integrity_ok")
        vision: Dict[str, Any]
        if live:
            if not ctx_ok or not det_ok:
                vision = {
                    "called": False,
                    "skip_reason": "INVALID_EVIDENCE",
                    "parsed": unusable("invalid_selected_png"),
                    "audit": None,
                }
            else:
                vision = call_selected_beam(
                    version10_root=v10,
                    beam_id=str(bid),
                    context_path=Path(rec.get("context_selected_path")),
                    detail_path=Path(rec.get("detail_selected_path")),
                    context_source=str(rec.get("context_selected_source")),
                    detail_source=str(rec.get("detail_selected_source")),
                    client_override=client_override,
                )
                parsed = vision.get("parsed") or {}
                if parsed.get("usable"):
                    parsed["groups"] = attach_length_evidence(parsed.get("groups") or [])
                    vision["parsed"] = parsed
                _log(f"  live {bid} success={(vision.get('audit') or {}).get('success')} usable={parsed.get('usable')}")
        else:
            vision = {
                "called": False,
                "skip_reason": "LIVE_DISABLED",
                "parsed": unusable("LIVE_DISABLED"),
                "audit": None,
            }
        parsed = vision.get("parsed") or {}
        cmp = compare_beam(
            parsed=parsed if parsed.get("usable") else parsed,
            detected=rec.get("detected_groups") or [],
            expected=rec.get("expected_groups") or [],
            requested_id=str(bid),
        )
        row = dict(rec)
        row["vision"] = {k: vision.get(k) for k in ("called", "skip_reason", "audit", "parsed")}
        row["comparison"] = cmp
        records.append(row)
        _dump(out_root / "review" / str(bid) / "vision_result.json", row["vision"])

    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    anti = run_anti_hardcoding(package_dir=pkg)
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
        "p2610c4": prior_phase_unit_ok(v10, "PhaseP2610C4_shadow_truth_reconciliation_benchmark_calibration", 22),
    }
    intact = prior_artefacts_intact(v10)
    metrics = _metrics(records, live=live)
    decision = "PASS_WITH_LIMITATIONS"
    if not unit.get("success") or not fp_cmp.get("unchanged") or not anti.get("ok") or not intact.get("ok"):
        decision = "FAIL"
    if live and metrics.get("api_failed") == metrics.get("attempted") and metrics.get("attempted"):
        decision = "FAIL"

    handoff = {
        "selected_ids": sample.get("selected_ids"),
        "sample_size": sample.get("size"),
        "fourth_set_count": len(fourth_ids),
        "next_step": "MANUAL VERIFICATION OF THE 10-BEAM FINAL VISION BENCHMARK",
    }
    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": decision,
        "pass_fail": "PASS" if decision == "PASS_WITH_LIMITATIONS" else "FAIL",
        "live_claude_call": live,
        "fourth_set": {k: fourth.get(k) for k in ("ok", "set_key", "path", "discovery_method", "unique_beam_ids")},
        "candidate_count": len(candidates),
        "population_records": [
            {k: c.get(k) for k in (
                "beam_id", "set_key", "c3_visual_gate_status", "strata", "evidence_valid",
                "excluded_reason", "mixed_source", "deterministic_group_count", "group_stats",
            )}
            for c in candidates
        ],
        "sample": {k: sample.get(k) for k in (
            "ok", "selected_ids", "size", "notes", "strata_coverage", "uncovered_strata",
            "why", "excluded_prior_control", "eligible_pool_size",
        )},
        "records": records,
        "metrics": metrics,
        "api_smoke": smoke,
        "anti_hardcoding": anti,
        "unit_tests": unit,
        "fingerprints": fp_cmp,
        "prior_phase_units": {k: bool(v.get("ok")) for k, v in prior_ok.items()},
        "handoff": handoff,
        "run_metadata": {
            "mode": mode,
            "runtime_s": round(time.perf_counter() - t0, 3),
            "max_sample": MAX_SAMPLE_SIZE,
            "live": live,
        },
        "production": {
            "production_mutation_count": 0 if fp_cmp.get("unchanged") else 1,
            "production_write": PRODUCTION_WRITE,
            "production_action": PRODUCTION_ACTION,
            "engineering_changes": ENGINEERING_CHANGES,
            "shadow_only": SHADOW_ONLY,
        },
        "output_root": str(out_root),
    }
    write_reports(out_root=out_root, result=result)
    _log(f"  decision={decision} selected={sample.get('selected_ids')}")
    return result


__all__ = ["run_phase_p2610c5"]
