"""P2.6.10-A orchestrator. Shadow crop audit. Does not change production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import ezdxf

from .config import (
    ENGINEERING_CHANGES,
    GATE_VERSION,
    MODE_OFFLINE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SCOPE,
    SHADOW_ONLY,
    TARGET_BEAMS,
)
from .cropper import render_crop
from .dataset import load_benchmark_targets
from .evaluator import (
    assert_allowed_final,
    b55_diagnostics,
    classify_final_decision,
    classify_phase_status,
    classify_reusability,
    production_invariants,
)
from .inventory import DISCOVERED_COMPONENTS
from .quality import assess_crop
from .region_builder import build_target_regions
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)
from .report import write_reports
from .title_localizer import choose_mark, collect_beam_titles
from .unit_tests import run_unit_tests

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _next_step(decision: str) -> str:
    if decision == "RENDERING_READY_FOR_P2_6_10":
        return "P2.6.10 can proceed with Claude Vision using this crop pipeline."
    if decision == "RENDERING_READY_WITH_ADAPTER":
        return (
            "P2.6.10 can proceed with Claude Vision using the P2.6.10-A adapter "
            "(title localization + outline envelope + M.1 region renderer). "
            "Do not use R.1 association extents."
        )
    if decision == "LOCALIZATION_GAP_REQUIRES_IMPLEMENTATION":
        return (
            "P2.6.10 must not start Claude Vision yet. Implement the minimum remaining "
            "association-free localization (reliable title disambiguation and/or outline envelope) first."
        )
    if decision == "EXISTING_RENDERER_NOT_SUITABLE":
        return "P2.6.10 cannot reuse the existing renderer without a new localization/render path."
    return "Investigation failed; do not start P2.6.10 Claude Vision."


def run_phase_p2610a(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_OFFLINE,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (out_root, out_root / "reports", out_root / "context", out_root / "detail", out_root / "metadata"):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode != MODE_OFFLINE:
        raise RuntimeError(f"unsupported P2.6.10-A mode {mode!r}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-A unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)
    _dump(out_root / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-A firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-A runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "fingerprints_before.json", before)

    targets = load_benchmark_targets(v10)
    _log(f"  loaded benchmark beams: {len(targets)} (expected {TARGET_BEAMS})")

    docs: Dict[str, Any] = {}
    titles_by_dxf: Dict[str, list] = {}
    records: list = []
    for i, target in enumerate(targets, start=1):
        set_key = str(target.get("set_key") or "")
        beam_id = str(target.get("beam_id") or "")
        dxf_path = Path(str(target.get("source_dxf")))
        key = str(dxf_path.resolve())
        if key not in docs:
            _log(f"  reading DXF {dxf_path.name}")
            docs[key] = ezdxf.readfile(key)
            titles_by_dxf[key] = collect_beam_titles(docs[key].modelspace())
        msp = docs[key].modelspace()
        titles = titles_by_dxf[key]
        mark = choose_mark(msp, titles, beam_id)
        notes = []
        if mark is None:
            notes.append("title_not_located")
            mark = {"x": None, "y": None, "text": None, "score": 0, "candidate_count": 0}
            regions = {
                "localization_method": "failed",
                "localization_source": "reinforcement_dxf_text",
                "annotation_association_dependency": False,
                "geometry_included": False,
                "title_included": False,
                "detail_extent": None,
                "context_extent": None,
                "envelope": {},
            }
        else:
            regions = build_target_regions(msp=msp, beam_id=beam_id, mark=mark, titles=titles)
        crops: Dict[str, Any] = {}
        for crop_type in ("context", "detail"):
            extent = regions.get(f"{crop_type}_extent")
            out_png = out_root / crop_type / f"{beam_id}.png"
            if not extent or mark.get("x") is None:
                crops[crop_type] = {"path": None, "quality": {"vision_readiness": "NOT_READY", "ocr_validation": "NOT_EVALUABLE"}}
                continue
            rendered = render_crop(dxf_path=dxf_path, output_path=out_png, extent=extent, crop_type=crop_type)
            quality = assess_crop(
                beam_id=beam_id,
                crop_type=crop_type,
                path=out_png,
                extent=extent,
                mark=mark,
                geometry_included=bool(regions.get("geometry_included")),
                titles=titles,
                scale_px_per_mm=rendered.get("scale_px_per_mm") or (0, 0),
                msp=msp,
            )
            meta = {
                "beam_id": beam_id,
                "drawing_set": set_key,
                "source_dxf": str(dxf_path),
                "renderer": rendered.get("renderer"),
                "renderer_version": rendered.get("renderer_version"),
                "crop_type": crop_type,
                "dxf_bbox": rendered.get("dxf_bbox"),
                "image_dimensions": rendered.get("image_dimensions"),
                "scale": rendered.get("scale_px_per_mm"),
                "localization_method": regions.get("localization_method"),
                "localization_source": regions.get("localization_source"),
                "annotation_association_dependency": False,
                "beam_title_included": quality.get("beam_title_included"),
                "beam_geometry_included": quality.get("beam_geometry_included"),
                "context_included": quality.get("context_included"),
                "clipping_detected": quality.get("clipping_detected"),
                "readability_status": quality.get("readability_status"),
                "confidence": quality.get("confidence"),
                "ocr_validation": "NOT_EVALUABLE",
                "notes": notes + list((regions.get("envelope") or {}).get("notes") or []),
            }
            _dump(out_root / "metadata" / f"{beam_id}_{crop_type}.json", meta)
            crops[crop_type] = {**rendered, "quality": quality, "metadata_path": str(out_root / "metadata" / f"{beam_id}_{crop_type}.json")}
        rec = {
            "phase": PHASE_ID,
            "set_key": set_key,
            "beam_id": beam_id,
            "source_dxf": str(dxf_path),
            "mark": mark,
            "localization_method": regions.get("localization_method"),
            "localization_source": regions.get("localization_source"),
            "annotation_association_dependency": False,
            "envelope": regions.get("envelope"),
            "crops": crops,
            "notes": notes,
            "production_action": PRODUCTION_ACTION,
            "shadow_only": SHADOW_ONLY,
            "production_routing_changed": False,
        }
        records.append(rec)
        dq = ((crops.get("detail") or {}).get("quality") or {})
        _log(
            f"  [{i}/{len(targets)}] {set_key}/{beam_id} "
            f"title={'Y' if mark.get('x') is not None else 'N'} "
            f"geom={'Y' if dq.get('beam_geometry_included') else 'N'} "
            f"ready={dq.get('vision_readiness')}"
        )

    inv = production_invariants(records)
    b55_rec = next((r for r in records if r.get("set_key") == "Fifth" and r.get("beam_id") == "B55"), {})
    b55 = b55_diagnostics(b55_rec)
    reusability = classify_reusability(records)
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    crops_complete = all(
        (r.get("crops") or {}).get("context", {}).get("path") and (r.get("crops") or {}).get("detail", {}).get("path")
        for r in records
    )
    production = {
        "production_mutation_count": 0 if fp_cmp.get("unchanged") else len(fp_cmp.get("changed_keys") or []),
        "fingerprints_ok": fp_cmp.get("unchanged"),
        "changed_keys": fp_cmp.get("changed_keys") or [],
        "all_shadow_only": inv.get("all_shadow_only"),
        "all_no_change": inv.get("all_no_change"),
        "engineering_changes": ENGINEERING_CHANGES,
        "steel_quantity_delta": 0,
        "bbs_delta": 0,
        "workbook_delta": 0,
        "production_objects_modified": False,
        "live_vision_invoked": False,
    }
    prior = {
        "p266": prior_phase_unit_ok(v10, "PhaseP266_semantic_longitudinal_resolver", 36),
        "p267": prior_phase_unit_ok(v10, "PhaseP267_live_semantic_arbitration", 31),
        "p268": prior_phase_unit_ok(v10, "PhaseP268_evidence_conflict_arbitration", 27),
        "p269": prior_phase_unit_ok(v10, "PhaseP269_reinforcement_group_interpretation", 20),
    }
    decision = assert_allowed_final(
        classify_final_decision(
            reusability=reusability,
            records=records,
            b55=b55,
            tests_ok=bool(unit.get("success")),
            fingerprints_ok=bool(fp_cmp.get("unchanged")),
        )
    )
    status = classify_phase_status(
        tests_ok=bool(unit.get("success")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        six_beams=len(records) == TARGET_BEAMS,
        crops_complete=crops_complete,
        reusability=reusability,
        final_decision=decision,
    )
    rendering_found = any(
        "render_dxf_region_to_png" in str((((r.get("crops") or {}).get("detail") or {}).get("renderer") or ""))
        for r in records
    )
    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "scope": SCOPE,
        "mode": mode,
        "production_write": PRODUCTION_WRITE,
        "engineering_changes": ENGINEERING_CHANGES,
        "pass_fail": status,
        "existing_rendering_capability": "FOUND" if rendering_found else "NOT_FOUND",
        "reusability_class": reusability,
        "output_root": str(out_root),
        "metrics": {
            "target_beams": len(records),
            "crops_complete": crops_complete,
            "production_invariants": inv,
            "LIVE_VISION_CALLS": 0,
        },
        "recommendation": {"decision": decision, "strength": "DIAGNOSTIC"},
        "decision": decision,
        "records": records,
        "b55_diagnostics": b55,
        "discovered_components": DISCOVERED_COMPONENTS,
        "unit_tests": unit,
        "firewall": fw,
        "leakage": leak,
        "production": production,
        "prior_regression": prior,
        "next_step": _next_step(decision),
        "live_vision_invoked": False,
    }
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    dump = dict(result)
    dump.pop("records", None)
    _dump(out_root / "result.json", dump)
    _dump(out_root / "fingerprints_after.json", after)
    (out_root / "P2.6.10-A_SAFETY.md").write_text(
        "\n".join(
            [
                "# P2.6.10-A production safety",
                "",
                f"- production_mutation_count: {production.get('production_mutation_count')}",
                f"- steel_quantity_delta: {production.get('steel_quantity_delta')}",
                f"- BBS_delta: {production.get('bbs_delta')}",
                f"- workbook_delta: {production.get('workbook_delta')}",
                "- live_vision_invoked: false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _log(f"  decision={decision} status={status} reusability={reusability}")
    return result


__all__ = ["run_phase_p2610a"]
