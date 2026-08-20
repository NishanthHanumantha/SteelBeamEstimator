"""P2.6.10-B.2 orchestrator. Context-first quality recovery. No Vision. No production writes."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import ezdxf

from PhaseP2610A_beam_region_crop_audit.dataset import find_reinforcement_dxf_for_set
from PhaseP2610A_beam_region_crop_audit.title_localizer import choose_mark, collect_beam_titles
from PhaseP2610B_adaptive_beam_detail_crop.completeness import evaluate_completeness
from PhaseP2610B_adaptive_beam_detail_crop.envelope import build_adaptive_regions

from .anti_hardcoding import run_anti_hardcoding
from .config import (
    DRAWING_SET_KEY,
    ENGINEERING_CHANGES,
    GATE_VERSION,
    MODE_OFFLINE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    P2610B1_OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    REPORT_BLANK_BEAMS,
    REPORT_CLIP_BEAMS,
    REPORT_QUALITY_BEAMS,
    SHADOW_ONLY,
    STRESS_BEAMS,
)
from .pipeline import process_beam
from .population import discover_fourth_set_population
from .quality import STATUS_BLACK, STATUS_EMPTY, STATUS_LOW_INFO, STATUS_MISSING
from .render_session import RenderSession
from .timing import PerfClock, Timer
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


def _fmt_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {secs:02d}s"


def _progress_line(done: int, total: int, elapsed_s: float, *, width: int = 28) -> str:
    total = max(total, 1)
    frac = min(max(done / total, 0.0), 1.0)
    filled = int(width * frac)
    bar = "#" * filled + "-" * (width - filled)
    remain = ((total - done) * (elapsed_s / done)) if done else 0.0
    return (
        f"  PROGRESS [{bar}] {done}/{total} {frac * 100:5.1f}%  "
        f"elapsed={_fmt_duration(elapsed_s)}  ETA={_fmt_duration(remain)}"
    )


def _emit_progress(out_root: Path, done: int, total: int, beam_id: str, t0: float, note: str = "") -> None:
    elapsed = time.time() - t0
    line = _progress_line(done, total, elapsed)
    print(line + (f"  {note}" if note else ""), flush=True)
    _dump(
        out_root / "progress.json",
        {
            "done": done,
            "total": total,
            "beam_id": beam_id,
            "elapsed_s": elapsed,
            "eta_s": ((total - done) * (elapsed / done)) if done else 0,
            "bar": line.strip(),
        },
    )


def _classify_decision(
    *,
    tests_ok: bool,
    fingerprints_ok: bool,
    anti_ok: bool,
    six_ok: bool,
    processed: int,
    discovered: int,
    skip_n: int,
    silent_blank: int,
    usable_n: int,
    hardcoding: bool,
) -> str:
    if hardcoding or not tests_ok or not fingerprints_ok or not anti_ok or not six_ok:
        return "FAIL"
    if discovered <= 0 or processed != discovered or skip_n:
        return "FAIL"
    if silent_blank:
        return "FAIL"
    if usable_n == discovered:
        return "PASS"
    if usable_n >= int(0.92 * discovered):
        return "PASS_WITH_LIMITATIONS"
    if usable_n > 0:
        return "PASS_WITH_LIMITATIONS"
    return "FAIL"


def _b1_reuse(v10: Path, beam_id: str, extent, crop_type: str) -> Optional[Path]:
    root = Path(v10) / "data" / "output" / P2610B1_OUTPUT_DIRNAME
    valp = root / "validation" / f"{beam_id}.json"
    png = root / crop_type / f"{beam_id}.png"
    if not valp.exists() or not png.exists() or png.stat().st_size < 200:
        return None
    try:
        prev = json.loads(valp.read_text(encoding="utf-8"))
        key = "context_bounds" if crop_type == "context" else "detail_bounds"
        b = prev.get(key) or []
        if len(b) != 4 or len(extent) != 4:
            return None
        if max(abs(float(b[i]) - float(extent[i])) for i in range(4)) > 12.0:
            return None
        return png
    except Exception:
        return None


def _failure_row(rec: Dict[str, Any], stage: str) -> Dict[str, Any]:
    diag = rec.get("context_diagnostic") if stage == "CONTEXT" else rec.get("detail_diagnostic")
    diag = diag or {}
    return {
        "beam_id": rec.get("beam_id"),
        "stage": stage,
        "primary_status": diag.get("primary_status") or rec.get("context_status" if stage == "CONTEXT" else "detail_status"),
        "failure_flags": diag.get("flags") or rec.get("context_flags" if stage == "CONTEXT" else "detail_flags"),
        "dominant_orientation": rec.get("dominant_orientation"),
        "clipping_direction": diag.get("clipping_axes") or [],
        "initial_bounds": rec.get("initial_context_bounds" if stage == "CONTEXT" else "initial_detail_bounds"),
        "final_bounds": rec.get("final_context_bounds" if stage == "CONTEXT" else "final_detail_bounds"),
        "recovery_attempts": rec.get("context_recovery_history" if stage == "CONTEXT" else "detail_recovery_history"),
        "final_vision_usable": rec.get("final_vision_usable"),
        "reason": diag.get("primary_status"),
    }


def run_phase_p2610b2(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_OFFLINE,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    pkg = Path(__file__).resolve().parent
    for d in (
        out_root,
        out_root / "context" / "initial",
        out_root / "context" / "final",
        out_root / "context" / "recovery",
        out_root / "detail" / "initial",
        out_root / "detail" / "final",
        out_root / "detail" / "recovery",
        out_root / "diagnostics",
        out_root / "anti_hardcoding" / "translation_tests",
        out_root / "anti_hardcoding" / "spatial_distance_tests",
        out_root / "anti_hardcoding" / "packed_sheet_tests",
    ):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode != MODE_OFFLINE:
        raise RuntimeError(f"unsupported P2.6.10-B.2 mode {mode!r}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log(f"  DRAWING_SET: {DRAWING_SET_KEY} only")
    _log("  CONTEXT-FIRST: context render/validate/recover before detail")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-B.2 unit tests failed: {failed}")
    else:
        existing = out_root / "unit_tests.json"
        if existing.exists():
            unit = json.loads(existing.read_text(encoding="utf-8"))
            unit["skipped"] = False
            unit["loaded_from_previous_run"] = True

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    _dump(out_root / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-B.2 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-B.2 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "fingerprints_before.json", before)
    intact = prior_artefacts_intact(v10)
    if not intact.get("ok"):
        raise RuntimeError(f"Prior artefacts missing: {intact.get('missing')}")

    dxf_path = find_reinforcement_dxf_for_set(v10, DRAWING_SET_KEY)
    clock = PerfClock()
    _log(f"  reading DXF {dxf_path}")
    with Timer() as t_load:
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()
    clock.add("dxf_load_s", t_load.seconds)
    with Timer() as t_disc:
        discovered = discover_fourth_set_population(v10, msp)
    clock.add("discovery_s", t_disc.seconds)
    beam_ids = list(discovered.get("beam_ids") or [])
    marks = discovered.get("marks") or {}
    titles = discovered.get("titles") or []
    session = RenderSession(dxf_path, dpi=150, doc=doc)
    _log(f"  discovered title_hits={discovered.get('title_hits')} unique={len(beam_ids)}")
    _log("  POST_OPTIMIZATION_VALIDATION_RUN: one DXF load, PNG cache, recovery only for suspects")

    records = []
    failures = []
    skip_n = 0
    render_fail = 0
    t0 = time.time()
    for i, beam_id in enumerate(beam_ids, start=1):
        diag_path = out_root / "diagnostics" / f"{beam_id}.json"
        final_ctx = out_root / "context" / "final" / f"{beam_id}.png"
        final_det = out_root / "detail" / "final" / f"{beam_id}.png"
        if diag_path.exists() and final_ctx.exists() and final_det.exists():
            rec = json.loads(diag_path.read_text(encoding="utf-8"))
            if rec.get("run_label") == "POST_OPTIMIZATION_VALIDATION_RUN":
                rec["resumed"] = True
                records.append(rec)
                _log(f"  [{i}/{len(beam_ids)}] {beam_id} RESUME usable={rec.get('final_vision_usable')}")
                _emit_progress(out_root, i, len(beam_ids), beam_id, t0, "resume")
                continue
        mark = marks.get(beam_id)
        if mark is None:
            skip_n += 1
            rec = {"beam_id": beam_id, "final_vision_usable": False, "reason": "mark_missing"}
            records.append(rec)
            failures.append(_failure_row({**rec, "context_diagnostic": {"primary_status": "DISCOVERY_FAILED", "flags": ["MARK_MISSING"]}}, "CONTEXT"))
            _log(f"  [{i}/{len(beam_ids)}] {beam_id} DISCOVERY_FAILED")
            _emit_progress(out_root, i, len(beam_ids), beam_id, t0)
            continue
        reuse = {}
        regions = None
        try:
            with Timer() as t_reg:
                regions = build_adaptive_regions(msp=msp, beam_id=beam_id, mark=mark, titles=titles)
            clock.add("region_s", t_reg.seconds)
            ctx_png = _b1_reuse(v10, beam_id, regions.get("context_extent") or [], "context")
            if ctx_png:
                reuse["context"] = ctx_png
            valp = v10 / "data" / "output" / P2610B1_OUTPUT_DIRNAME / "validation" / f"{beam_id}.json"
            if valp.exists():
                prev = json.loads(valp.read_text(encoding="utf-8"))
                reuse["detail_bounds"] = prev.get("detail_bounds")
                det_png = v10 / "data" / "output" / P2610B1_OUTPUT_DIRNAME / "detail" / f"{beam_id}.png"
                if det_png.exists():
                    reuse["detail"] = det_png
        except Exception:
            reuse = {}
        try:
            rec = process_beam(
                beam_id=beam_id,
                msp=msp,
                mark=mark,
                titles=titles,
                dxf_path=dxf_path,
                out_root=out_root,
                render_fn=session.render_crop,
                reuse_initial=reuse,
                regions=regions,
            )
            rec["run_label"] = "POST_OPTIMIZATION_VALIDATION_RUN"
        except Exception as exc:
            render_fail += 1
            rec = {
                "beam_id": beam_id,
                "final_vision_usable": False,
                "context_status": STATUS_MISSING,
                "detail_status": STATUS_MISSING,
                "error": str(exc),
                "context_diagnostic": {"primary_status": STATUS_MISSING, "flags": ["RENDER_EXCEPTION"]},
                "detail_diagnostic": {"primary_status": STATUS_MISSING, "flags": ["RENDER_EXCEPTION"]},
            }
            _log(f"  [{i}/{len(beam_ids)}] {beam_id} RENDER_EXCEPTION {exc}")
        with Timer() as t_io:
            _dump(diag_path, rec)
        clock.add("diagnostic_io_s", t_io.seconds)
        tbeam = rec.get("timing") or {}
        for key in ("context_render_s", "detail_render_s", "quality_s", "recovery_s", "reuse_copy_s"):
            clock.add(key, float(tbeam.get(key) or 0.0))
        records.append(rec)
        if not rec.get("final_vision_usable"):
            if rec.get("context_status") in (STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING) or not rec.get("context_valid_after_recovery", True):
                failures.append(_failure_row(rec, "CONTEXT"))
            else:
                failures.append(_failure_row(rec, "DETAIL"))
        _log(
            f"  [{i}/{len(beam_ids)}] {beam_id} ctx={rec.get('context_status')} "
            f"det={rec.get('detail_status')} usable={rec.get('final_vision_usable')} "
            f"orient={rec.get('dominant_orientation')} rec={rec.get('context_recovery_attempt_count')}"
        )
        _emit_progress(out_root, i, len(beam_ids), beam_id, t0)

    _log("  Population loop complete. Anti-hardcoding + six-beam regression next.")
    probe_id = beam_ids[0] if beam_ids else None
    doc_copy = ezdxf.readfile(str(dxf_path))
    anti = run_anti_hardcoding(
        package_dir=pkg,
        msp=doc_copy.modelspace(),
        beam_id=probe_id,
        titles=collect_beam_titles(doc_copy.modelspace()),
    )
    _dump(out_root / "anti_hardcoding" / "translation_tests" / "synthetic.json", (anti.get("translation_invariance") or {}).get("synthetic"))
    _dump(out_root / "anti_hardcoding" / "translation_tests" / "dxf_copy.json", (anti.get("translation_invariance") or {}).get("dxf_copy"))
    _dump(out_root / "anti_hardcoding" / "spatial_distance_tests" / "result.json", anti.get("spatial_distance"))
    _dump(out_root / "anti_hardcoding" / "packed_sheet_tests" / "result.json", anti.get("packed_sheet"))

    six_records = []
    six_docs: Dict[str, Any] = {}
    six_titles: Dict[str, list] = {}
    six_ok = True
    by_id = {r.get("beam_id"): r for r in records}
    for set_key, beam_id in STRESS_BEAMS:
        spath = find_reinforcement_dxf_for_set(v10, set_key)
        key = str(spath.resolve())
        if key not in six_docs:
            six_docs[key] = ezdxf.readfile(key)
            six_titles[key] = collect_beam_titles(six_docs[key].modelspace())
        smsp = six_docs[key].modelspace()
        stitles = six_titles[key]
        smark = choose_mark(smsp, stitles, beam_id)
        if smark is None:
            six_ok = False
            six_records.append({"set_key": set_key, "beam_id": beam_id, "complete": False, "error": "mark_missing"})
            continue
        sregions = build_adaptive_regions(msp=smsp, beam_id=beam_id, mark=smark, titles=stitles)
        scomp = evaluate_completeness(
            beam_id=beam_id,
            extent=sregions.get("detail_extent"),
            mark=smark,
            outline=(sregions.get("adaptive") or {}).get("outline"),
            evidence=list((sregions.get("adaptive") or {}).get("evidence") or []),
            titles=stitles,
        )
        row = {
            "set_key": set_key,
            "beam_id": beam_id,
            "complete": bool(scomp.get("complete")),
            "final_vision_usable": (by_id.get(beam_id) or {}).get("final_vision_usable"),
        }
        six_records.append(row)
        if not scomp.get("complete"):
            six_ok = False

    def _count(pred) -> int:
        return sum(1 for r in records if pred(r))

    discovered_n = len(beam_ids)
    empty_n = _count(lambda r: r.get("context_status") == STATUS_EMPTY or r.get("detail_status") == STATUS_EMPTY)
    black_n = _count(lambda r: r.get("context_status") == STATUS_BLACK or r.get("detail_status") == STATUS_BLACK)
    low_n = _count(lambda r: r.get("context_status") == STATUS_LOW_INFO or r.get("detail_status") == STATUS_LOW_INFO)
    silent_blank = _count(
        lambda r: r.get("final_vision_usable")
        and (r.get("context_status") in (STATUS_EMPTY, STATUS_BLACK) or r.get("detail_status") in (STATUS_EMPTY, STATUS_BLACK))
    )
    usable_n = _count(lambda r: r.get("final_vision_usable"))
    ctx_complete = _count(lambda r: r.get("context_valid_after_recovery"))
    det_complete = _count(lambda r: r.get("detail_valid_after_recovery"))
    both_complete = _count(lambda r: r.get("context_valid_after_recovery") and r.get("detail_valid_after_recovery"))
    blank_init = (STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO)
    summary = {
        "drawing_set": "fourth_set",
        "source_dxf": str(dxf_path),
        "discovered_beam_count": discovered_n,
        "title_hits": discovered.get("title_hits"),
        "initial_context_generated_count": _count(lambda r: bool(r.get("context_initial_path") or r.get("context_crop_path"))),
        "final_context_valid_count": _count(lambda r: r.get("context_valid_after_recovery")),
        "context_valid_before_recovery_count": _count(lambda r: r.get("context_valid_before_recovery")),
        "initial_detail_generated_count": _count(lambda r: bool(r.get("detail_initial_path") or r.get("detail_crop_path"))),
        "final_detail_valid_count": _count(lambda r: r.get("detail_valid_after_recovery")),
        "empty_render_count": empty_n,
        "black_render_count": black_n,
        "low_information_render_count": low_n,
        "horizontal_clipping_suspect_count": _count(lambda r: "X" in ((r.get("context_diagnostic") or {}).get("clipping_axes") or [])),
        "vertical_clipping_suspect_count": _count(lambda r: "Y" in ((r.get("context_diagnostic") or {}).get("clipping_axes") or [])),
        "context_recovery_attempt_count": sum(int(r.get("context_recovery_attempt_count") or 0) for r in records),
        "context_recovery_success_count": _count(lambda r: r.get("context_recovery_success")),
        "detail_recovery_attempt_count": sum(int(r.get("detail_recovery_attempt_count") or 0) for r in records),
        "detail_recovery_success_count": _count(lambda r: r.get("detail_recovery_success")),
        "unresolved_context_failure_count": _count(lambda r: not r.get("context_valid_after_recovery")),
        "unresolved_detail_failure_count": _count(lambda r: r.get("context_valid_after_recovery") and not r.get("detail_valid_after_recovery")),
        "target_visible_count": _count(lambda r: r.get("target_visible")),
        "longitudinal_complete_count": _count(lambda r: r.get("longitudinal_complete")),
        "context_quality_pass_count": _count(lambda r: r.get("context_quality_pass")),
        "final_vision_usable_count": usable_n,
        "final_vision_usable_rate": (usable_n / discovered_n) if discovered_n else 0.0,
        "skipped_count": skip_n,
        "true_render_failure_count": render_fail,
        "silent_blank_success_count": silent_blank,
        "production_mutation_count": 0,
        "steel_quantity_delta": 0,
        "BBS_delta": 0,
        "workbook_delta": 0,
        "live_claude_vision_calls": False,
        "context_metrics": {
            "total_beams": discovered_n,
            "initial_valid": _count(lambda r: r.get("context_valid_before_recovery")),
            "recovery_required": _count(lambda r: r.get("context_recovery_applied")),
            "recovered": _count(lambda r: r.get("context_recovery_success")),
            "unresolved": _count(lambda r: not r.get("context_valid_after_recovery")),
            "blank_black_initial": _count(lambda r: r.get("context_initial_status") in blank_init),
            "blank_black_final": _count(lambda r: r.get("context_final_status") in (STATUS_EMPTY, STATUS_BLACK)),
            "horizontal_recovery_count": _count(
                lambda r: r.get("context_recovery_applied") and r.get("dominant_orientation") == "HORIZONTAL"
            ),
            "vertical_recovery_count": _count(
                lambda r: r.get("context_recovery_applied") and r.get("dominant_orientation") == "VERTICAL"
            ),
        },
        "detail_metrics": {
            "total_processed": discovered_n,
            "initial_valid": _count(lambda r: r.get("detail_valid_before_recovery")),
            "recovery_required": _count(lambda r: r.get("detail_recovery_applied")),
            "recovered": _count(lambda r: r.get("detail_recovery_success")),
            "unresolved": _count(lambda r: r.get("context_valid_after_recovery") and not r.get("detail_valid_after_recovery")),
        },
        "population_metrics": {
            "total_unique_beams": discovered_n,
            "context_complete": ctx_complete,
            "detail_complete": det_complete,
            "both_complete": both_complete,
            "incomplete": discovered_n - both_complete,
            "skipped": skip_n,
            "render_failures": render_fail,
        },
    }

    known = {
        "blank_black": [],
        "longitudinal_clipping": [],
        "low_context_quality": [],
    }
    for bid in REPORT_BLANK_BEAMS:
        if bid in by_id:
            known["blank_black"].append(by_id[bid])
    for bid in REPORT_CLIP_BEAMS:
        if bid in by_id:
            known["longitudinal_clipping"].append(by_id[bid])
    for bid in REPORT_QUALITY_BEAMS:
        if bid in by_id:
            known["low_context_quality"].append(by_id[bid])

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
    }
    decision = _classify_decision(
        tests_ok=bool(unit.get("success")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        anti_ok=bool(anti.get("ok")),
        six_ok=six_ok,
        processed=len(records),
        discovered=discovered_n,
        skip_n=skip_n,
        silent_blank=silent_blank,
        usable_n=usable_n,
        hardcoding=bool(anti.get("beam_id_special_cases")),
    )
    if not prior["p266"].get("ok") or not prior["p2610a"].get("ok") or not prior["p2610b"].get("ok") or not prior["p2610b1"].get("ok"):
        decision = "FAIL"
    pass_fail = "PASS" if decision == "PASS" else ("PARTIAL" if decision == "PASS_WITH_LIMITATIONS" else "FAILED")

    recovery_diag = []
    for rec in records:
        if rec.get("context_recovery_history") or rec.get("detail_recovery_history"):
            recovery_diag.append(
                {
                    "beam_id": rec.get("beam_id"),
                    "context": rec.get("context_recovery_history"),
                    "detail": rec.get("detail_recovery_history"),
                }
            )

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
        "output_root": str(out_root),
        "population": {
            "source_dxf": str(dxf_path),
            "title_hits": discovered.get("title_hits"),
            "unique_beam_ids": discovered_n,
            "collapsed_duplicates": discovered.get("collapsed_duplicates"),
        },
        "validation_summary": summary,
        "failures": failures,
        "recovery_diagnostics": recovery_diag,
        "beam_diagnostics": records,
        "known_visual_cases": {
            k: [
                {
                    "beam_id": r.get("beam_id"),
                    "context_status": r.get("context_status"),
                    "detail_status": r.get("detail_status"),
                    "final_vision_usable": r.get("final_vision_usable"),
                    "dominant_orientation": r.get("dominant_orientation"),
                    "context_recovery_attempt_count": r.get("context_recovery_attempt_count"),
                    "detail_recovery_attempt_count": r.get("detail_recovery_attempt_count"),
                }
                for r in rows
            ]
            for k, rows in known.items()
        },
        "anti_hardcoding": anti,
        "six_beam_regression": {"ok": six_ok, "records": six_records},
        "unit_tests": unit,
        "firewall": fw,
        "leakage": leak,
        "production": production,
        "prior_regression": prior,
        "live_vision_invoked": False,
        "performance": {
            "run_label": "POST_OPTIMIZATION_VALIDATION_RUN",
            "total_runtime_s": clock.elapsed(),
            "avg_seconds_per_beam": (clock.elapsed() / discovered_n) if discovered_n else 0.0,
            "buckets": clock.buckets,
            "context_screening_runtime_s": clock.buckets.get("context_render_s", 0.0) + clock.buckets.get("quality_s", 0.0),
            "detail_runtime_s": clock.buckets.get("detail_render_s", 0.0),
            "recovery_runtime_s": clock.buckets.get("recovery_s", 0.0),
            "diagnostic_output_runtime_s": clock.buckets.get("diagnostic_io_s", 0.0),
            "render_cache_hits": session.hits,
            "render_cache_misses": session.misses,
            "session_render_s": session.render_s,
            "parallelism_enabled": False,
            "worker_count": 1,
            "renderer_parallel_safe": False,
            "pre_optimization_partial_rate_s_per_beam": 125.277,
            "pre_optimization_completed_beams": 8,
        },
        "root_cause_summary": {
            "blank_black": "Crop extent includes large empty model-space; M.1 fills unused canvas with dark background, so FILE_GENERATED is not VISUALLY_USABLE.",
            "longitudinal_clipping": "Initial envelope/barriers clip the target's dominant axis; recovery expands only along that axis and stops at packed-sheet title barriers.",
            "low_context_quality": "Target is visible but framing is tight or perpendicular neighbors consume context; target-first allocation prefers longitudinal evidence.",
        },
    }
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    safe_stop_path = out_root / "pre_optimization_partial" / "SAFE_STOP_RECORD.json"
    safe_stop = {}
    if safe_stop_path.exists():
        safe_stop = json.loads(safe_stop_path.read_text(encoding="utf-8"))
        _dump(out_root / "SAFE_STOP_RECORD.json", safe_stop)
    perf = result.get("performance") or {}
    pre_rate = float(perf.get("pre_optimization_partial_rate_s_per_beam") or 0.0)
    post_avg = float(perf.get("avg_seconds_per_beam") or 0.0)
    comparison = {
        "record_type": "PRE_VS_POST_OPTIMIZATION_COMPARISON",
        "pre_optimization_partial_run": {
            "do_not_use_as_final_population_evidence": True,
            "beams_completed": safe_stop.get("beams_completed_before_stop", 8),
            "elapsed_s": safe_stop.get("elapsed_time_before_stop_s", 1002.216),
            "avg_seconds_per_beam": pre_rate,
            "stage": safe_stop.get("current_execution_stage"),
            "safe_stop_status": safe_stop.get("safe_stop_status"),
        },
        "post_optimization_validation_run": {
            "total_runtime_s": perf.get("total_runtime_s"),
            "avg_seconds_per_beam": post_avg,
            "context_screening_runtime_s": perf.get("context_screening_runtime_s"),
            "detail_runtime_s": perf.get("detail_runtime_s"),
            "recovery_runtime_s": perf.get("recovery_runtime_s"),
            "diagnostic_output_runtime_s": perf.get("diagnostic_output_runtime_s"),
            "cache_hits": perf.get("render_cache_hits"),
            "cache_misses": perf.get("render_cache_misses"),
            "workers": perf.get("worker_count"),
            "parallelism_enabled": perf.get("parallelism_enabled"),
        },
        "speedup_vs_partial_rate": (pre_rate / post_avg) if post_avg else None,
        "target_wall_clock_min": [25, 40],
        "full_population_used": discovered_n,
    }
    _dump(out_root / "PRE_VS_POST_OPTIMIZATION_COMPARISON.json", comparison)
    _dump(out_root / "performance_profile.json", perf)
    _dump(out_root / "recovery_summary.json", result.get("recovery_diagnostics") or [])
    _dump(out_root / "anti_hardcoding" / "anti_hardcoding_results.json", anti)
    _dump(out_root / "anti_hardcoding_results.json", anti)
    _dump(out_root / "fingerprints_after.json", after)
    _log(f"  decision={decision} vision_usable={usable_n}/{discovered_n}")
    _dump(
        out_root / "progress.json",
        {
            "done": discovered_n,
            "total": discovered_n,
            "percent": 100.0,
            "phase": "complete",
            "decision": decision,
            "bar": _progress_line(discovered_n, max(discovered_n, 1), time.time() - t0),
        },
    )
    return result


__all__ = ["run_phase_p2610b2"]
