"""P2.6.10-C.3 orchestrator. Shadow completeness gate + optional live Vision. No production writes."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .anti_hardcoding import run_anti_hardcoding
from .comparison import compare_beam
from .config import (
    ENGINEERING_CHANGES,
    GATE_VERSION,
    MODE_LIVE,
    MODE_OFFLINE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    REPORT_BENCHMARK_BEAMS,
    REPORT_BLANK_BEAMS,
    REPORT_CLIP_BEAMS,
    REPORT_QUALITY_BEAMS,
    SHADOW_ONLY,
    SIX_BEAM_UNUSABLE_STOP_RATE,
    STATUS_LIMITED,
    STATUS_NOT_READY,
    STATUS_READY,
    STATUS_REVIEW,
)
from .diagnostics import call_quality_counts, gate_population_counts
from .manifest_loader import load_beam_evidence
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
from .vision_benchmark import run_one_beam
from .visual_completeness_gate import evaluate_completeness

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _classify_decision(
    *,
    tests_ok: bool,
    fingerprints_ok: bool,
    anti_ok: bool,
    hardcoding: bool,
    production_mutations: int,
    live_failed: bool,
    unresolved_limitations: bool,
) -> str:
    if production_mutations or hardcoding:
        return "UNSAFE_FOR_PRODUCTION"
    if not tests_ok or not fingerprints_ok or not anti_ok:
        return "UNSAFE_FOR_PRODUCTION"
    if live_failed:
        return "LIVE_BENCHMARK_FAILED"
    if unresolved_limitations:
        return "PASS_WITH_LIMITATIONS"
    return "SAFE_SHADOW_BENCHMARK"


def run_phase_p2610c3(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_OFFLINE,
    include_limitations: bool = False,
    client_override=None,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    pkg = Path(__file__).resolve().parent
    out_root.mkdir(parents=True, exist_ok=True)
    live = mode == MODE_LIVE

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode not in (MODE_OFFLINE, MODE_LIVE):
        raise RuntimeError(f"unsupported P2.6.10-C.3 mode {mode!r}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log(f"  mode={mode} live={live}")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-C.3 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-C.3 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-C.3 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    intact = prior_artefacts_intact(v10)
    if not intact.get("ok"):
        raise RuntimeError(f"Prior artefacts missing: {intact.get('missing')}")

    anti = run_anti_hardcoding(package_dir=pkg)
    if not anti.get("ok"):
        raise RuntimeError(f"P2.6.10-C.3 anti-hardcoding failed: {anti}")

    t0 = time.perf_counter()
    beams = load_beam_evidence(v10)
    _log(f"  loaded C.1+C.2 manifest unique={len(beams)}")

    gate_rows: List[Dict[str, Any]] = []
    by_id = {}
    for beam in beams:
        gate = evaluate_completeness(beam.context, beam.detail)
        rec = {
            "beam_id": beam.beam_id,
            "status": gate["status"],
            "reason_codes": gate["reason_codes"],
            "context_source_phase": beam.context.source_phase,
            "detail_source_phase": beam.detail.source_phase,
            "mixed_source": beam.context.source_phase != beam.detail.source_phase,
            "gate": gate,
            "evidence": beam.to_dict(),
        }
        gate_rows.append(rec)
        by_id[beam.beam_id] = (beam, rec)
        _dump(
            out_root / "beams" / beam.beam_id / "gate_decision.json",
            rec,
        )

    gate_counts = gate_population_counts(gate_rows)
    _log(
        f"  gate READY={gate_counts.get(STATUS_READY)} LIMITED={gate_counts.get(STATUS_LIMITED)} "
        f"REVIEW={gate_counts.get(STATUS_REVIEW)} NOT_READY={gate_counts.get(STATUS_NOT_READY)}"
    )

    six_ids = [bid for _sk, bid in REPORT_BENCHMARK_BEAMS]
    set_of = {bid: sk for sk, bid in REPORT_BENCHMARK_BEAMS}
    six_rows: List[Dict[str, Any]] = []
    six_claude: List[Dict[str, Any]] = []
    live_failed = False
    stop_population = False

    for beam_id in six_ids:
        pair = by_id.get(beam_id)
        if pair is None:
            six_rows.append({"beam_id": beam_id, "error": "not_in_manifest", "set_key": set_of.get(beam_id)})
            continue
        beam, grec = pair
        claude = run_one_beam(
            v10=v10,
            beam=beam,
            gate=grec["gate"],
            six_beam_control=True,
            include_limitations=True,
            client_override=client_override,
            live=live,
        )
        six_claude.append(claude)
        cmp = compare_beam(
            v10=v10,
            set_key=set_of[beam_id],
            beam_id=beam_id,
            parsed=claude.get("parsed") or {},
        )
        row = {
            "beam_id": beam_id,
            "set_key": set_of[beam_id],
            "context_source": beam.context.source_phase,
            "detail_source": beam.detail.source_phase,
            "gate": grec["gate"],
            "claude": {k: v for k, v in claude.items() if k != "raw_text"},
            "comparison": cmp,
        }
        six_rows.append(row)
        _dump(out_root / "beams" / beam_id / "claude_result.json", claude)
        _dump(out_root / "beams" / beam_id / "comparison.json", cmp)
        _log(f"  six-beam {beam_id} gate={grec['status']} called={claude.get('called')} usable={(claude.get('parsed') or {}).get('usable')}")

    attempted = [c for c in six_claude if c.get("called")]
    unusable_n = sum(1 for c in attempted if not (c.get("parsed") or {}).get("usable"))
    api_fail = sum(1 for c in attempted if not (c.get("audit") or {}).get("success"))
    technically_valid = True
    if live:
        if attempted and (unusable_n / max(len(attempted), 1)) > SIX_BEAM_UNUSABLE_STOP_RATE:
            technically_valid = False
            live_failed = True
            stop_population = True
        if attempted and api_fail == len(attempted):
            technically_valid = False
            live_failed = True
            stop_population = True
        if not attempted and live:
            technically_valid = True

    pop_claude: List[Dict[str, Any]] = list(six_claude)
    if live and not stop_population and technically_valid:
        for beam in beams:
            if beam.beam_id in six_ids:
                continue
            grec = by_id[beam.beam_id][1]
            st = grec["status"]
            if st not in (STATUS_READY, STATUS_LIMITED):
                claude = run_one_beam(
                    v10=v10,
                    beam=beam,
                    gate=grec["gate"],
                    six_beam_control=False,
                    include_limitations=False,
                    live=False,
                )
                pop_claude.append(claude)
                _dump(out_root / "beams" / beam.beam_id / "claude_result.json", claude)
                continue
            claude = run_one_beam(
                v10=v10,
                beam=beam,
                gate=grec["gate"],
                six_beam_control=False,
                include_limitations=include_limitations and st == STATUS_LIMITED,
                client_override=client_override,
                live=live,
            )
            pop_claude.append(claude)
            _dump(out_root / "beams" / beam.beam_id / "claude_result.json", claude)
            if claude.get("called"):
                _log(f"  pop {beam.beam_id} {st} usable={(claude.get('parsed') or {}).get('usable')}")
    else:
        for beam in beams:
            if beam.beam_id in six_ids:
                continue
            grec = by_id[beam.beam_id][1]
            claude = run_one_beam(
                v10=v10,
                beam=beam,
                gate=grec["gate"],
                six_beam_control=False,
                include_limitations=False,
                live=False,
            )
            pop_claude.append(claude)
            _dump(out_root / "beams" / beam.beam_id / "claude_result.json", claude)

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
    }

    claude_q = call_quality_counts(pop_claude)
    known = {
        "blank_crushed": [by_id[i][1] for i in REPORT_BLANK_BEAMS if i in by_id],
        "long_horizontal": [by_id[i][1] for i in REPORT_CLIP_BEAMS if i in by_id],
        "less_accurate": [by_id[i][1] for i in REPORT_QUALITY_BEAMS if i in by_id],
    }
    unresolved = gate_counts.get(STATUS_NOT_READY, 0) > 0 or gate_counts.get(STATUS_REVIEW, 0) > 0
    decision = _classify_decision(
        tests_ok=bool(unit.get("success")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        anti_ok=bool(anti.get("ok")),
        hardcoding=bool(anti.get("beam_id_special_cases")),
        production_mutations=0,
        live_failed=live_failed,
        unresolved_limitations=unresolved or (not live),
    )
    six_ident = [
        r for r in six_rows if ((r.get("claude") or {}).get("parsed") or {}).get("target_beam_identified")
    ]
    neighbor_hits = [
        r for r in six_rows if ((r.get("claude") or {}).get("parsed") or {}).get("neighbor_evidence_detected")
    ]
    collapse = []
    for r in six_rows:
        vs = ((r.get("comparison") or {}).get("vs_p269") or {})
        if vs.get("merged_distinct_groups"):
            collapse.append(r.get("beam_id"))

    control_answers = {
        "1_visually_eligible_ready": gate_counts.get(STATUS_READY),
        "1b_ready_with_limitations": gate_counts.get(STATUS_LIMITED),
        "2_blocked_before_claude": gate_counts.get(STATUS_NOT_READY),
        "3_six_beam_target_identified": len(six_ident),
        "4_same_spec_distinct_groups_collapsed": collapse,
        "5_six_beam_taxonomy": [r.get("comparison", {}).get("taxonomy") for r in six_rows],
        "6_neighbor_evidence_flags": [r.get("beam_id") for r in neighbor_hits],
        "7_b55_taxonomy": next((r.get("comparison", {}).get("taxonomy") for r in six_rows if r.get("beam_id") == "B55"), None),
        "8_accuracy_improvement": "diagnostic_only_see_six_beam_report",
        "9_production_generalization": "SHADOW_DIAGNOSTICS_ONLY",
    }

    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": decision,
        "pass_fail": "PASS" if decision in ("SAFE_SHADOW_BENCHMARK", "PASS_WITH_LIMITATIONS") else "FAIL",
        "live_claude_vision": "CALLED" if live and any(c.get("called") for c in pop_claude) else "NOT_CALLED",
        "visual_completeness_manifest": gate_rows,
        "six_beam": {
            "technically_valid": technically_valid,
            "stop_population": stop_population,
            "rows": six_rows,
        },
        "population_summary": {
            "total_unique_beams": len(beams),
            "gate": gate_counts,
            "claude": claude_q,
            "mixed_source": sum(1 for g in gate_rows if g.get("mixed_source")),
            "prior_phase_units": {k: bool(v.get("ok")) for k, v in prior_ok.items()},
        },
        "claude_call_audit": [
            {"beam_id": c.get("beam_id"), "called": c.get("called"), "audit": c.get("audit"), "skip_reason": c.get("skip_reason"), "call_reason": c.get("call_reason")}
            for c in pop_claude
        ],
        "claude_normalized_results": [
            {"beam_id": c.get("beam_id"), "parsed": c.get("parsed"), "gate_status": c.get("gate_status")}
            for c in pop_claude
        ],
        "comparison_results": six_rows,
        "diagnostics": {"known_reporting_cohorts": {k: [{"beam_id": r["beam_id"], "status": r["status"]} for r in v] for k, v in known.items()}},
        "performance": {"total_runtime_s": round(time.perf_counter() - t0, 3)},
        "anti_hardcoding": anti,
        "unit_tests": unit,
        "fingerprints": fp_cmp,
        "production": {
            "production_mutation_count": 0,
            "steel_quantity_delta": 0,
            "BBS_delta": 0,
            "workbook_delta": 0,
            "production_write": PRODUCTION_WRITE,
            "production_action": PRODUCTION_ACTION,
            "engineering_changes": ENGINEERING_CHANGES,
            "shadow_only": SHADOW_ONLY,
        },
        "control_answers": control_answers,
        "handoff": {"consumed_manifest": "PhaseP2610C1C2_evidence_inventory_candidate_selection/selection_manifest.json"},
        "output_root": str(out_root),
    }
    write_reports(out_root=out_root, result=result)
    _log(f"  decision={decision} live={result['live_claude_vision']}")
    return result


__all__ = ["run_phase_p2610c3"]
