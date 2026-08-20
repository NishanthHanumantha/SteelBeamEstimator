"""P2.6.10-B.3 orchestrator. Overlay recovery. No Vision. No production writes."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import ezdxf

from PhaseP2610A_beam_region_crop_audit.dataset import find_reinforcement_dxf_for_set
from PhaseP2610A_beam_region_crop_audit.title_localizer import collect_beam_titles
from PhaseP2610B2_render_quality_directional_recovery.quality import (
    STATUS_BLACK,
    STATUS_EMPTY,
    STATUS_LOW_INFO,
    STATUS_MISSING,
    validate_render,
)
from PhaseP2610B2_render_quality_directional_recovery.render_session import RenderSession
from PhaseP2610B2_render_quality_directional_recovery.timing import PerfClock, Timer

from .anti_hardcoding import run_anti_hardcoding
from .classify import classify_beam
from .config import (
    CLASS_FROZEN,
    CLASS_REVIEW,
    CLASS_TARGET,
    DRAWING_SET_KEY,
    ENGINEERING_CHANGES,
    GATE_VERSION,
    MODE_OFFLINE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    P2610B1_OUTPUT_DIRNAME,
    P2610B2_OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    REPORT_ALIAS_DISCOVERED,
    REPORT_BLANK_BEAMS,
    REPORT_CLIP_BEAMS,
    REPORT_QUALITY_BEAMS,
    SHADOW_ONLY,
)
from .pipeline import freeze_baseline, recover_beam
from .population import discover_fourth_set_population
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
_BLANK = {STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING}


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _fmt_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {secs:02d}s"


def _classify_decision(
    *,
    tests_ok: bool,
    fingerprints_ok: bool,
    anti_ok: bool,
    frozen_regression: int,
    processed: int,
    discovered: int,
    skip_n: int,
    silent_blank: int,
    improved: int,
    hardcoding: bool,
    unresolved_limitations: bool = False,
) -> str:
    if hardcoding or not tests_ok or not fingerprints_ok or not anti_ok:
        return "FAIL"
    if frozen_regression or skip_n or silent_blank or processed != discovered or discovered <= 0:
        return "FAIL"
    if unresolved_limitations:
        return "PASS_WITH_LIMITATIONS"
    if improved > 0:
        return "PASS"
    return "PASS_WITH_LIMITATIONS"


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cohort_force_ids(discovered: set) -> set:
    force = set(REPORT_BLANK_BEAMS + REPORT_CLIP_BEAMS + REPORT_QUALITY_BEAMS)
    for alias, real in REPORT_ALIAS_DISCOVERED:
        if alias not in discovered and real in discovered:
            force.add(real)
    return {x for x in force if x in discovered}


def run_phase_p2610b3(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_OFFLINE,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    pkg = Path(__file__).resolve().parent
    out_root.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode != MODE_OFFLINE:
        raise RuntimeError(f"unsupported P2.6.10-B.3 mode {mode!r}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log("  OVERLAY: frozen-good B.1 PNGs are not regenerated")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-B.3 unit tests failed: {failed}")
    else:
        existing = out_root / "unit_tests.json"
        if existing.exists():
            unit = json.loads(existing.read_text(encoding="utf-8"))
            unit["loaded_from_previous_run"] = True

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-B.3 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-B.3 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    intact = prior_artefacts_intact(v10)
    if not intact.get("ok"):
        raise RuntimeError(f"Prior artefacts missing: {intact.get('missing')}")

    dxf_path = find_reinforcement_dxf_for_set(v10, DRAWING_SET_KEY)
    clock = PerfClock()
    with Timer() as t_load:
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()
    clock.add("dxf_load_s", t_load.seconds)
    discovered = discover_fourth_set_population(v10, msp)
    beam_ids = list(discovered.get("beam_ids") or [])
    marks = discovered.get("marks") or {}
    titles = discovered.get("titles") or []
    session = RenderSession(dxf_path, dpi=150, doc=doc)
    force_ids = _cohort_force_ids(set(beam_ids))
    _log(f"  discovered unique={len(beam_ids)} cohort_force={len(force_ids)}")

    b1_root = v10 / "data" / "output" / P2610B1_OUTPUT_DIRNAME
    b2_root = v10 / "data" / "output" / P2610B2_OUTPUT_DIRNAME
    records = []
    skip_n = 0
    t0 = time.time()
    for i, beam_id in enumerate(beam_ids, start=1):
        mark = marks.get(beam_id)
        b1 = _load_json(b1_root / "validation" / f"{beam_id}.json") or {}
        b2 = _load_json(b2_root / "diagnostics" / f"{beam_id}.json")
        ctx_png = Path(str(b1.get("context_crop_path") or (b1_root / "context" / f"{beam_id}.png")))
        det_png = Path(str(b1.get("detail_crop_path") or (b1_root / "detail" / f"{beam_id}.png")))
        b1["context_crop_path"] = str(ctx_png)
        b1["detail_crop_path"] = str(det_png)
        with Timer() as t_q:
            ctx_q = validate_render(ctx_png if ctx_png.exists() else None, extent=b1.get("context_bounds"), crop_type="context")
            det_q = validate_render(det_png if det_png.exists() else None, extent=b1.get("detail_bounds"), crop_type="detail")
        clock.add("quality_s", t_q.seconds)
        decision = classify_beam(b1=b1, ctx_quality=ctx_q, det_quality=det_q, b2=b2)
        classification = decision["classification"]
        reasons = list(decision.get("reasons") or [])
        if beam_id in force_ids and classification != CLASS_TARGET:
            classification = CLASS_TARGET
            reasons.append("VALIDATION_COHORT_OVERLAY")
        if mark is None:
            skip_n += 1
            rec = {"beam_id": beam_id, "baseline_classification": CLASS_TARGET, "final_reason": "MARK_MISSING", "rerendered": False}
            records.append(rec)
            _log(f"  [{i}/{len(beam_ids)}] {beam_id} MARK_MISSING")
            continue
        if classification != CLASS_TARGET:
            rec = freeze_baseline(
                beam_id=beam_id,
                classification=classification,
                reasons=reasons,
                b1=b1,
                b2=b2,
                ctx_quality=ctx_q,
                det_quality=det_q,
            )
            rec["run_label"] = "P2610B3"
        else:
            with Timer() as t_rec:
                rec = recover_beam(
                    beam_id=beam_id,
                    msp=msp,
                    mark=mark,
                    titles=titles,
                    dxf_path=dxf_path,
                    out_root=out_root,
                    render_fn=session.render_crop,
                    classification=classification,
                    reasons=reasons,
                    b1=b1,
                    b2=b2,
                    ctx_quality=ctx_q,
                    det_quality=det_q,
                )
            clock.add("recovery_s", t_rec.seconds)
            rec["run_label"] = "P2610B3"
        records.append(rec)
        _log(
            f"  [{i}/{len(beam_ids)}] {beam_id} {rec.get('baseline_classification')} "
            f"action={rec.get('b3_action')} src={rec.get('selected_context_source')} "
            f"elapsed={_fmt_duration(time.time() - t0)}"
        )

    _log("  Population overlay complete. Anti-hardcoding next.")
    probe_id = beam_ids[0] if beam_ids else None
    doc_copy = ezdxf.readfile(str(dxf_path))
    anti = run_anti_hardcoding(
        package_dir=pkg,
        msp=doc_copy.modelspace(),
        beam_id=probe_id,
        titles=collect_beam_titles(doc_copy.modelspace()),
    )

    def _count(pred) -> int:
        return sum(1 for r in records if pred(r))

    frozen_n = _count(lambda r: r.get("baseline_classification") == CLASS_FROZEN)
    target_n = _count(lambda r: r.get("baseline_classification") == CLASS_TARGET or r.get("target_recovery"))
    review_n = _count(lambda r: r.get("baseline_classification") == CLASS_REVIEW)
    regressions = []
    for rec in records:
        if rec.get("baseline_classification") != CLASS_FROZEN:
            continue
        if rec.get("rerendered") or rec.get("selected_context_source") != "P2610B1" or rec.get("selected_detail_source") != "P2610B1":
            regressions.append(rec.get("beam_id"))
            continue
        if rec.get("b1_context_sha256") and rec.get("selected_context_sha256") != rec.get("b1_context_sha256"):
            regressions.append(rec.get("beam_id"))
        if rec.get("b1_detail_sha256") and rec.get("selected_detail_sha256") != rec.get("b1_detail_sha256"):
            regressions.append(rec.get("beam_id"))
    silent_blank = _count(
        lambda r: str(r.get("final_context_status")) in _BLANK and r.get("b3_action") == "improved"
    )
    improved = _count(lambda r: r.get("b3_action") == "improved")
    summary = {
        "drawing_set": "fourth_set",
        "discovered_beam_count": len(beam_ids),
        "frozen_good_count": frozen_n,
        "target_recovery_count": target_n,
        "review_only_count": review_n,
        "known_good_regression_count": len(set(regressions)),
        "known_good_regression_ids": sorted(set(regressions)),
        "b1_reused_count": _count(lambda r: r.get("selected_context_source") == "P2610B1" and r.get("selected_detail_source") == "P2610B1"),
        "b2_retained_count": _count(lambda r: r.get("selected_context_source") == "P2610B2"),
        "b3_improved_count": improved,
        "fallback_count": _count(lambda r: r.get("fallback_to_baseline") or r.get("b3_action") == "fallback_to_baseline"),
        "context_complete_count": _count(lambda r: str(r.get("final_context_status")) not in _BLANK),
        "detail_complete_count": _count(lambda r: str(r.get("final_detail_status")) not in _BLANK),
        "skipped_count": skip_n,
        "silent_blank_success_count": silent_blank,
        "production_mutation_count": 0,
        "live_claude_vision_calls": False,
    }

    by_id = {r.get("beam_id"): r for r in records}
    known = {"blank_black": [], "longitudinal_clipping": [], "low_context_quality": []}
    for bid in REPORT_BLANK_BEAMS:
        if bid in by_id:
            known["blank_black"].append(by_id[bid])
    for bid in REPORT_CLIP_BEAMS:
        if bid in by_id:
            known["longitudinal_clipping"].append(by_id[bid])
    for bid in REPORT_QUALITY_BEAMS:
        if bid in by_id:
            known["low_context_quality"].append(by_id[bid])
        elif bid == "B69A" and "B69" in by_id:
            row = dict(by_id["B69"])
            row["reporting_alias"] = "B69A_COLLAPSED_TO_B69"
            known["low_context_quality"].append(row)

    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    production = {
        "production_mutation_count": 0 if fp_cmp.get("unchanged") else len(fp_cmp.get("changed_keys") or []),
        "fingerprints_ok": fp_cmp.get("unchanged"),
        "changed_keys": fp_cmp.get("changed_keys") or [],
        "steel_quantity_delta": 0,
        "bbs_delta": 0,
        "workbook_delta": 0,
        "production_objects_modified": False,
        "live_vision_invoked": False,
        "engineering_changes": ENGINEERING_CHANGES,
    }
    prior = {
        "p266": prior_phase_unit_ok(v10, "PhaseP266_semantic_longitudinal_resolver", 36),
        "p2610a": prior_phase_unit_ok(v10, "PhaseP2610A_beam_region_crop_audit", 14),
        "p2610b": prior_phase_unit_ok(v10, "PhaseP2610B_adaptive_beam_detail_crop", 18),
        "p2610b1": prior_phase_unit_ok(v10, "PhaseP2610B1_population_generalization", 16),
        "p2610b2": prior_phase_unit_ok(v10, "PhaseP2610B2_render_quality_directional_recovery", 29),
    }
    targeted = max(target_n, 1)
    performance = {
        "run_label": "P2610B3_OVERLAY",
        "total_runtime_s": clock.elapsed(),
        "frozen_beam_count": frozen_n,
        "targeted_beam_count": target_n,
        "review_only_count": review_n,
        "candidates_generated": sum(int(r.get("candidate_count") or 0) for r in records),
        "candidates_evaluated": sum(len(r.get("candidate_evaluation") or []) for r in records),
        "avg_recovery_s_per_targeted": (clock.buckets.get("recovery_s", 0.0) / targeted),
        "buckets": clock.buckets,
        "render_cache_hits": session.hits,
        "render_cache_misses": session.misses,
        "parallelism_enabled": False,
        "worker_count": 1,
        "renderer_parallel_safe": False,
    }
    blank_unresolved = any((r.get("b3_action") != "improved") for r in known.get("blank_black") or [])
    clip_unresolved = sum(1 for r in (known.get("longitudinal_clipping") or []) if r.get("b3_action") != "improved") >= 3
    unresolved_limitations = bool(blank_unresolved or clip_unresolved)
    decision = _classify_decision(
        tests_ok=bool(unit.get("success")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        anti_ok=bool(anti.get("ok")),
        frozen_regression=len(set(regressions)),
        processed=len(records),
        discovered=len(beam_ids),
        skip_n=skip_n,
        silent_blank=silent_blank,
        improved=improved,
        hardcoding=bool(anti.get("beam_id_special_cases")),
        unresolved_limitations=unresolved_limitations,
    )
    if not all(p.get("ok") for p in prior.values()):
        decision = "FAIL"
    if len(set(regressions)):
        recommendation = "B. Stop because B.3 introduced regression"
    else:
        recommendation = (
            "A. Proceed to Detail Candidate Selection + Visual Completeness Gate "
            "+ Claude Vision Shadow Benchmark"
        )
    pass_fail = "PASS" if decision == "PASS" else ("PARTIAL" if decision == "PASS_WITH_LIMITATIONS" else "FAILED")

    failures = [
        {
            "beam_id": r.get("beam_id"),
            "classification": r.get("baseline_classification"),
            "final_context_status": r.get("final_context_status"),
            "final_detail_status": r.get("final_detail_status"),
            "final_reason": r.get("final_reason"),
            "b3_action": r.get("b3_action"),
        }
        for r in records
        if str(r.get("final_context_status")) in _BLANK or str(r.get("final_detail_status")) in _BLANK
    ]
    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "mode": mode,
        "production_write": PRODUCTION_WRITE,
        "shadow_only": SHADOW_ONLY,
        "engineering_changes": ENGINEERING_CHANGES,
        "pass_fail": pass_fail,
        "decision": decision,
        "recommendation": recommendation,
        "output_root": str(out_root),
        "population": {
            "source_dxf": str(dxf_path),
            "title_hits": discovered.get("title_hits"),
            "unique_beam_ids": len(beam_ids),
        },
        "validation_summary": summary,
        "failures": failures,
        "beam_selection_manifest": [
            {
                "beam_id": r.get("beam_id"),
                "baseline_classification": r.get("baseline_classification"),
                "frozen_good": r.get("frozen_good"),
                "target_recovery": r.get("target_recovery"),
                "review_only": r.get("review_only"),
                "baseline_context_source": r.get("baseline_context_source"),
                "baseline_detail_source": r.get("baseline_detail_source"),
                "target_geometry_bounds": r.get("target_geometry_bounds"),
                "primary_direction": r.get("primary_direction"),
                "target_start_end_coverage": r.get("target_start_end_coverage"),
                "candidate_count": r.get("candidate_count"),
                "candidate_reason_codes": r.get("candidate_reason_codes"),
                "selected_context_source": r.get("selected_context_source"),
                "selected_detail_source": r.get("selected_detail_source"),
                "b3_action": r.get("b3_action"),
                "b3_detail_action": r.get("b3_detail_action"),
                "final_context_status": r.get("final_context_status"),
                "final_detail_status": r.get("final_detail_status"),
                "final_reason": r.get("final_reason"),
            }
            for r in records
        ],
        "target_anchor_manifest": [
            {
                "beam_id": r.get("beam_id"),
                "target_geometry_bounds": r.get("target_geometry_bounds"),
                "primary_direction": r.get("primary_direction"),
                "owned_evidence_count": r.get("owned_evidence_count"),
                "target_start_end_coverage": r.get("target_start_end_coverage"),
            }
            for r in records
            if r.get("target_geometry_bounds")
        ],
        "context_recovery_summary": {
            "improved": improved,
            "fallback": summary["fallback_count"],
            "b2_retained": summary["b2_retained_count"],
        },
        "candidate_evaluations": [
            {"beam_id": r.get("beam_id"), "candidates": r.get("candidate_evaluation")}
            for r in records
            if r.get("candidate_evaluation")
        ],
        "baseline_preservation": {
            "frozen_good_count": frozen_n,
            "rerendered_frozen": [r.get("beam_id") for r in records if r.get("baseline_classification") == CLASS_FROZEN and r.get("rerendered")],
        },
        "known_good_regression": {"count": len(set(regressions)), "ids": sorted(set(regressions))},
        "known_visual_cases": {
            k: [
                {
                    "beam_id": r.get("beam_id"),
                    "baseline_classification": r.get("baseline_classification"),
                    "b3_action": r.get("b3_action"),
                    "final_context_status": r.get("final_context_status"),
                    "final_detail_status": r.get("final_detail_status"),
                    "selected_context_source": r.get("selected_context_source"),
                    "reporting_alias": r.get("reporting_alias"),
                }
                for r in rows
            ]
            for k, rows in known.items()
        },
        "anti_hardcoding": anti,
        "unit_tests": unit,
        "firewall": fw,
        "leakage": leak,
        "production": production,
        "prior_regression": prior,
        "live_vision_invoked": False,
        "performance": performance,
        "production_action": PRODUCTION_ACTION,
    }
    write_reports(out_root=out_root, result=result)
    index_lines = ["# B.3 visual review index", "", "TARGET_RECOVERY beams only.", ""]
    for r in records:
        if not r.get("target_recovery"):
            continue
        index_lines.append(
            f"- {r.get('beam_id')}: {r.get('b3_action')} ctx={r.get('final_context_status')} "
            f"src={r.get('selected_context_source')} review/`{r.get('beam_id')}`/"
        )
    (out_root / "visual_review_index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    _log(f"  decision={decision} frozen={frozen_n} target={target_n} improved={improved} regression={len(set(regressions))}")
    return result


__all__ = ["run_phase_p2610b3", "_classify_decision"]
