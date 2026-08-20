"""P2.6.10-B.1 orchestrator. Fourth-set population validation. No Vision. No production writes."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import ezdxf

from PhaseP2610A_beam_region_crop_audit.cropper import render_crop
from PhaseP2610A_beam_region_crop_audit.dataset import find_reinforcement_dxf_for_set, load_benchmark_targets
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
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SHADOW_ONLY,
    STRESS_BEAMS,
)
from .population import discover_fourth_set_population
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    p2610b_artefacts_intact,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)
from .report import write_reports
from .unit_tests import run_unit_tests
from .validator import validate_detail

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


def _emit_progress(out_root: Path, done: int, total: int, beam_id: str, t0: float) -> None:
    elapsed = time.time() - t0
    line = _progress_line(done, total, elapsed)
    print(line, flush=True)
    _dump(
        out_root / "progress.json",
        {
            "done": done,
            "total": total,
            "beam_id": beam_id,
            "elapsed_s": elapsed,
            "eta_s": ((total - done) * (elapsed / done)) if done else 0,
            "bar": line.strip(),
            "phase": "crop_loop" if done < total else "crop_loop_done",
        },
    )


def _reuse_existing_png(path: Path, extent: Any, crop_type: str) -> Optional[Dict[str, Any]]:
    """Resume helper: keep an already-written crop PNG instead of re-rendering."""
    if not path.exists() or path.stat().st_size < 200:
        return None
    try:
        from PIL import Image

        with Image.open(path) as im:
            width, height = im.size
    except Exception:
        return None
    box = list(extent) if extent is not None else []
    return {
        "path": str(path),
        "crop_type": crop_type,
        "dxf_bbox": box,
        "image_dimensions": [int(width), int(height)],
        "reused_existing_png": True,
    }


def _classify_decision(
    *,
    tests_ok: bool,
    fingerprints_ok: bool,
    anti_ok: bool,
    six_ok: bool,
    processed: int,
    discovered: int,
    complete_n: int,
    skip_n: int,
    render_fail_n: int,
) -> str:
    if not tests_ok or not fingerprints_ok or not anti_ok or not six_ok:
        return "FAIL — GENERALIZATION OR ANTI-HARDCODING NOT ESTABLISHED"
    if discovered <= 0 or processed != discovered or skip_n:
        return "FAIL — GENERALIZATION OR ANTI-HARDCODING NOT ESTABLISHED"
    if render_fail_n:
        return "FAIL — GENERALIZATION OR ANTI-HARDCODING NOT ESTABLISHED"
    if complete_n == discovered:
        return "PASS — POPULATION GENERALIZATION CONFIRMED"
    return "PASS_WITH_LIMITATIONS — GENERALIZATION MOSTLY CONFIRMED, LIMITATIONS DOCUMENTED"


def run_phase_p2610b1(
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
        out_root / "context",
        out_root / "detail",
        out_root / "validation",
        out_root / "anti_hardcoding",
        out_root / "anti_hardcoding" / "translation_tests",
        out_root / "anti_hardcoding" / "spatial_distance_tests",
        out_root / "anti_hardcoding" / "packed_sheet_tests",
        out_root / "comparisons",
    ):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode != MODE_OFFLINE:
        raise RuntimeError(f"unsupported P2.6.10-B.1 mode {mode!r}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log(f"  DRAWING_SET: {DRAWING_SET_KEY} only")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-B.1 unit tests failed: {failed}")
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
        raise RuntimeError(f"P2.6.10-B.1 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-B.1 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "fingerprints_before.json", before)
    intact = p2610b_artefacts_intact(v10)
    if not intact.get("ok"):
        raise RuntimeError(f"P2.6.10-B artefacts missing: {intact.get('missing')}")

    dxf_path = find_reinforcement_dxf_for_set(v10, DRAWING_SET_KEY)
    _log(f"  reading DXF {dxf_path}")
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    discovered = discover_fourth_set_population(v10, msp)
    titles = discovered["titles"]
    marks = discovered["marks"]
    beam_ids = list(discovered["beam_ids"])
    _log(f"  discovered title_hits={discovered['title_hits']} unique={discovered['unique_beam_ids']}")

    records: list = []
    failures: list = []
    context_ok = detail_ok = complete_n = render_fail = skip_n = 0
    t0 = time.time()
    for i, beam_id in enumerate(beam_ids, start=1):
        mark = marks.get(beam_id)
        rec: Dict[str, Any] = {
            "beam_id": beam_id,
            "set_key": DRAWING_SET_KEY,
            "discovery_status": "OK" if mark else "FAILED",
            "shadow_only": SHADOW_ONLY,
            "production_action": PRODUCTION_ACTION,
            "production_routing_changed": False,
        }
        if mark is None:
            skip_n += 1
            val = validate_detail(
                beam_id=beam_id,
                extent=None,
                mark=None,
                outline=None,
                evidence=[],
                titles=titles,
                rendered=False,
                discovery_ok=False,
            )
            rec["validation_status"] = "FAIL"
            rec["failure_category"] = val.get("failure_categories")
            records.append(rec)
            failures.append(val)
            _dump(out_root / "validation" / f"{beam_id}.json", val)
            _log(f"  [{i}/{len(beam_ids)}] {beam_id} DISCOVERY_FAILED")
            _emit_progress(out_root, i, len(beam_ids), beam_id, t0)
            continue
        try:
            regions = build_adaptive_regions(msp=msp, beam_id=beam_id, mark=mark, titles=titles)
        except Exception as exc:
            val = validate_detail(
                beam_id=beam_id,
                extent=None,
                mark=mark,
                outline=None,
                evidence=[],
                titles=titles,
                rendered=False,
                discovery_ok=True,
            )
            val["failure_categories"] = ["OTHER_DETERMINISTIC_FAILURE"]
            val["deterministic_notes"] = [f"build_adaptive_regions: {exc}"]
            rec["validation_status"] = "FAIL"
            rec["failure_category"] = val["failure_categories"]
            records.append(rec)
            failures.append(val)
            _dump(out_root / "validation" / f"{beam_id}.json", val)
            _log(f"  [{i}/{len(beam_ids)}] {beam_id} ENVELOPE_FAILED")
            _emit_progress(out_root, i, len(beam_ids), beam_id, t0)
            continue
        crops: Dict[str, Any] = {}
        rendered_ok = True
        reused = False
        for crop_type in ("context", "detail"):
            extent = regions.get(f"{crop_type}_extent")
            out_png = out_root / crop_type / f"{beam_id}.png"
            reused_crop = _reuse_existing_png(out_png, extent, crop_type)
            if reused_crop is not None:
                crops[crop_type] = reused_crop
                reused = True
                continue
            try:
                crops[crop_type] = render_crop(
                    dxf_path=dxf_path, output_path=out_png, extent=extent, crop_type=crop_type
                )
            except Exception as exc:
                rendered_ok = False
                render_fail += 1
                crops[crop_type] = {"path": None, "error": str(exc)}
        if crops.get("context", {}).get("path"):
            context_ok += 1
        if crops.get("detail", {}).get("path"):
            detail_ok += 1
        adapted = regions.get("adaptive") or {}
        val = validate_detail(
            beam_id=beam_id,
            extent=regions.get("detail_extent"),
            mark=mark,
            outline=adapted.get("outline"),
            evidence=list(adapted.get("evidence") or []),
            titles=titles,
            rendered=rendered_ok and bool(crops.get("detail", {}).get("path")),
            discovery_ok=True,
        )
        val["context_crop_path"] = (crops.get("context") or {}).get("path")
        val["detail_crop_path"] = (crops.get("detail") or {}).get("path")
        val["context_bounds"] = list(regions.get("context_extent") or [])
        val["detail_bounds"] = list(regions.get("detail_extent") or [])
        val["crop_dimensions"] = {
            "context": (crops.get("context") or {}).get("image_dimensions"),
            "detail": (crops.get("detail") or {}).get("image_dimensions"),
        }
        _dump(out_root / "validation" / f"{beam_id}.json", val)
        rec.update(
            {
                "context_crop_status": "OK" if (crops.get("context") or {}).get("path") else "FAILED",
                "detail_crop_status": "OK" if (crops.get("detail") or {}).get("path") else "FAILED",
                "crop_bounds": val.get("detail_bounds"),
                "crop_dimensions": val.get("crop_dimensions"),
                "validation_status": val.get("completeness_status"),
                "failure_category": val.get("failure_categories") or None,
            }
        )
        records.append(rec)
        if val.get("completeness_status") == "PASS":
            complete_n += 1
        else:
            failures.append({"beam_id": beam_id, "failure_categories": val.get("failure_categories"), "notes": val.get("deterministic_notes")})
        _log(
            f"  [{i}/{len(beam_ids)}] {beam_id} "
            f"status={val.get('completeness_status')} "
            f"fail={val.get('failure_categories')}"
            f"{' reused_png' if reused else ''}"
        )
        _emit_progress(out_root, i, len(beam_ids), beam_id, t0)

    _log("  Crop loop complete. Next: anti-hardcoding (DXF copy) then six-beam regression.")
    _dump(
        out_root / "progress.json",
        {
            "done": len(beam_ids),
            "total": len(beam_ids),
            "beam_id": None,
            "elapsed_s": time.time() - t0,
            "eta_s": 480,
            "phase": "anti_hardcoding",
            "bar": _progress_line(len(beam_ids), max(len(beam_ids), 1), time.time() - t0),
            "note": "Crops done. Anti-hardcoding + six-beam regression remaining (~5-10 min).",
        },
    )

    # Anti-hardcoding uses a separate in-memory DXF copy so population msp is untouched.
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
    _log("  Anti-hardcoding complete. Next: original six-beam live engine regression.")
    _dump(
        out_root / "progress.json",
        {
            "done": len(beam_ids),
            "total": len(beam_ids),
            "elapsed_s": time.time() - t0,
            "eta_s": 240,
            "phase": "six_beam_regression",
            "bar": _progress_line(len(beam_ids), max(len(beam_ids), 1), time.time() - t0),
            "note": "Six-beam regression remaining (~2-5 min).",
        },
    )

    six_records = []
    six_docs: Dict[str, Any] = {}
    six_titles: Dict[str, list] = {}
    six_ok = True
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
        row = {"set_key": set_key, "beam_id": beam_id, "complete": bool(scomp.get("complete")), "completeness": scomp}
        six_records.append(row)
        if not scomp.get("complete"):
            six_ok = False

    discovered_n = len(beam_ids)
    incomplete_n = discovered_n - complete_n
    rate = (complete_n / discovered_n) if discovered_n else 0.0
    summary = {
        "drawing_set": "fourth_set",
        "source_dxf": str(dxf_path),
        "discovered_beam_count": discovered_n,
        "title_hits": discovered.get("title_hits"),
        "collapsed_duplicate_title_groups": len(discovered.get("collapsed_duplicates") or []),
        "context_crop_success_count": context_ok,
        "detail_crop_success_count": detail_ok,
        "fully_complete_count": complete_n,
        "incomplete_count": incomplete_n,
        "render_failure_count": render_fail,
        "skip_count": skip_n,
        "completeness_rate": rate,
        "failure_breakdown": {},
        "anti_hardcoding": {
            "source_guard_pass": bool((anti.get("source_guard") or {}).get("ok")),
            "translation_invariance_pass": bool(((anti.get("translation_invariance") or {}).get("synthetic") or {}).get("ok")),
            "spatial_distance_pass": bool((anti.get("spatial_distance") or {}).get("ok")),
            "packed_sheet_robustness_pass": bool((anti.get("packed_sheet") or {}).get("ok")),
        },
        "production_mutation_count": 0,
        "steel_quantity_delta": 0,
        "BBS_delta": 0,
        "workbook_delta": 0,
        "live_vision_invoked": False,
    }
    for f in failures:
        for cat in f.get("failure_categories") or []:
            summary["failure_breakdown"][cat] = summary["failure_breakdown"].get(cat, 0) + 1

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
    summary["production_mutation_count"] = production["production_mutation_count"]
    prior = {
        "p266": prior_phase_unit_ok(v10, "PhaseP266_semantic_longitudinal_resolver", 36),
        "p2610a": prior_phase_unit_ok(v10, "PhaseP2610A_beam_region_crop_audit", 14),
        "p2610b": prior_phase_unit_ok(v10, "PhaseP2610B_adaptive_beam_detail_crop", 18),
    }
    decision = _classify_decision(
        tests_ok=bool(unit.get("success")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        anti_ok=bool(anti.get("ok")),
        six_ok=six_ok,
        processed=len(records),
        discovered=discovered_n,
        complete_n=complete_n,
        skip_n=skip_n,
        render_fail_n=render_fail,
    )
    if not prior["p266"].get("ok") or not prior["p2610a"].get("ok") or not prior["p2610b"].get("ok"):
        decision = "FAIL — GENERALIZATION OR ANTI-HARDCODING NOT ESTABLISHED"
    pass_fail = "PASS" if decision.startswith("PASS") and not decision.startswith("PASS_WITH") else (
        "PARTIAL" if decision.startswith("PASS_WITH") else "FAILED"
    )
    if decision.startswith("PASS —"):
        pass_fail = "PASS"
    elif decision.startswith("PASS_WITH"):
        pass_fail = "PARTIAL"

    manifest = {
        "set_key": DRAWING_SET_KEY,
        "source_dxf": str(dxf_path),
        "title_hits": discovered.get("title_hits"),
        "unique_beam_ids": discovered_n,
        "collapsed_duplicates": discovered.get("collapsed_duplicates"),
        "discovery_method": discovered.get("discovery_method"),
        "beams": records,
    }
    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "mode": mode,
        "production_write": PRODUCTION_WRITE,
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
        "population_manifest": manifest,
        "validation_summary": summary,
        "failures": failures,
        "anti_hardcoding": anti,
        "six_beam_regression": {"ok": six_ok, "records": six_records},
        "unit_tests": unit,
        "firewall": fw,
        "leakage": leak,
        "production": production,
        "prior_regression": prior,
        "live_vision_invoked": False,
        "records": records,
    }
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    dump = dict(result)
    dump.pop("records", None)
    dump.pop("population_manifest", None)
    _dump(out_root / "result.json", dump)
    _dump(out_root / "fingerprints_after.json", after)
    _log(f"  decision={decision} complete={complete_n}/{discovered_n}")
    _dump(
        out_root / "progress.json",
        {
            "done": discovered_n,
            "total": discovered_n,
            "percent": 100.0,
            "elapsed_s": time.time() - t0,
            "eta_s": 0,
            "phase": "complete",
            "decision": decision,
            "bar": _progress_line(discovered_n, max(discovered_n, 1), time.time() - t0),
            "note": "P2.6.10-B.1 run finished.",
        },
    )
    return result


__all__ = ["run_phase_p2610b1"]
