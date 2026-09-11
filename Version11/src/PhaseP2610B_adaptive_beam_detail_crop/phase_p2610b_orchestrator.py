"""P2.6.10-B orchestrator. Shadow adaptive-crop benchmark. No Vision. No production writes."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import ezdxf

from PhaseP2610A_beam_region_crop_audit.config import OUTPUT_DIRNAME as P2610A_DIR
from PhaseP2610A_beam_region_crop_audit.cropper import render_crop
from PhaseP2610A_beam_region_crop_audit.dataset import load_benchmark_targets
from PhaseP2610A_beam_region_crop_audit.title_localizer import choose_mark, collect_beam_titles

from .completeness import evaluate_completeness
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
from .envelope import build_adaptive_regions
from .evaluator import classify_phase, classify_readiness, production_invariants
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)
from .report import write_reports
from .unit_tests import run_unit_tests

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run_phase_p2610b(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_OFFLINE,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (
        out_root,
        out_root / "reports",
        out_root / "context",
        out_root / "detail",
        out_root / "comparison",
        out_root / "metadata",
        out_root / "completeness",
    ):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode != MODE_OFFLINE:
        raise RuntimeError(f"unsupported P2.6.10-B mode {mode!r}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-B unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)
    _dump(out_root / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-B firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-B runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "fingerprints_before.json", before)

    p2610a = v10 / "data" / "output" / P2610A_DIR
    targets = load_benchmark_targets(v10)
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
        if mark is None:
            raise RuntimeError(f"title not located for {set_key}/{beam_id}")
        regions = build_adaptive_regions(msp=msp, beam_id=beam_id, mark=mark, titles=titles)
        crops: Dict[str, Any] = {}
        for crop_type in ("context", "detail"):
            extent = regions.get(f"{crop_type}_extent")
            out_png = out_root / crop_type / f"{beam_id}.png"
            rendered = render_crop(dxf_path=dxf_path, output_path=out_png, extent=extent, crop_type=crop_type)
            crops[crop_type] = rendered
            meta = {
                "beam_id": beam_id,
                "drawing_set": set_key,
                "source_dxf": str(dxf_path),
                "crop_type": crop_type,
                "dxf_bbox": rendered.get("dxf_bbox"),
                "image_dimensions": rendered.get("image_dimensions"),
                "localization_method": regions.get("localization_method"),
                "annotation_association_dependency": False,
                "p2610a_detail_extent": list(regions.get("p2610a_detail_extent") or []),
            }
            _dump(out_root / "metadata" / f"{beam_id}_{crop_type}.json", meta)
        adapted = regions.get("adaptive") or {}
        completeness = evaluate_completeness(
            beam_id=beam_id,
            extent=regions.get("detail_extent"),
            mark=mark,
            outline=adapted.get("outline"),
            evidence=list(adapted.get("evidence") or []),
            titles=titles,
        )
        _dump(out_root / "completeness" / f"{beam_id}.json", completeness)
        a_detail = p2610a / "detail" / f"{beam_id}.png"
        cmp = {"a_detail": None, "b_detail": crops["detail"]["path"]}
        if a_detail.exists():
            dest_a = out_root / "comparison" / f"{beam_id}_A.png"
            dest_b = out_root / "comparison" / f"{beam_id}_B.png"
            shutil.copy2(a_detail, dest_a)
            shutil.copy2(crops["detail"]["path"], dest_b)
            cmp = {"a_detail": str(dest_a), "b_detail": str(dest_b)}
        rec = {
            "phase": PHASE_ID,
            "set_key": set_key,
            "beam_id": beam_id,
            "source_dxf": str(dxf_path),
            "mark": {"x": mark.get("x"), "y": mark.get("y"), "text": mark.get("text")},
            "crops": crops,
            "adaptive": {
                "detail_extent": adapted.get("detail_extent"),
                "p2610a_detail_extent": regions.get("p2610a_detail_extent"),
                "evidence_counts": adapted.get("evidence_counts"),
                "y_cap": adapted.get("y_cap"),
            },
            "completeness": completeness,
            "comparison": cmp,
            "production_action": PRODUCTION_ACTION,
            "shadow_only": SHADOW_ONLY,
            "production_routing_changed": False,
        }
        records.append(rec)
        _log(
            f"  [{i}/{len(targets)}] {set_key}/{beam_id} "
            f"top={completeness.get('top_reinforcement_visible')} "
            f"complete={completeness.get('complete')}"
        )

    inv = production_invariants(records)
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    crops_complete = all(
        (r.get("crops") or {}).get("context", {}).get("path") and (r.get("crops") or {}).get("detail", {}).get("path")
        for r in records
    )
    readiness = classify_readiness(records)
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
        "p2610a": prior_phase_unit_ok(v10, "PhaseP2610A_beam_region_crop_audit", 14),
    }
    recommendation = classify_phase(
        tests_ok=bool(unit.get("success")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        six_beams=len(records) == TARGET_BEAMS,
        crops_complete=crops_complete,
        readiness=readiness,
    )
    status = "PASS" if recommendation.get("decision") == "SAFE_SHADOW_BENCHMARK" and readiness in ("READY", "PARTIAL") else (
        "PARTIAL" if readiness == "PARTIAL" else "FAILED"
    )
    if recommendation.get("decision") == "SAFE_SHADOW_BENCHMARK" and readiness == "READY":
        status = "PASS"
    elif recommendation.get("decision") == "SAFE_SHADOW_BENCHMARK" and readiness in ("PARTIAL", "INCOMPLETE"):
        status = "PARTIAL"
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
        "output_root": str(out_root),
        "metrics": {
            "target_beams": len(records),
            "crops_complete": crops_complete,
            "readiness": readiness,
            "complete_count": sum(1 for r in records if (r.get("completeness") or {}).get("complete")),
            "LIVE_VISION_CALLS": 0,
        },
        "recommendation": recommendation,
        "decision": recommendation.get("decision"),
        "records": records,
        "unit_tests": unit,
        "firewall": fw,
        "leakage": leak,
        "production": production,
        "prior_regression": prior,
        "live_vision_invoked": False,
    }
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    dump = dict(result)
    dump.pop("records", None)
    _dump(out_root / "result.json", dump)
    _dump(out_root / "fingerprints_after.json", after)
    (out_root / "P2.6.10-B_SAFETY.md").write_text(
        "\n".join(
            [
                "# P2.6.10-B production safety",
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
    _log(f"  decision={result.get('decision')} readiness={readiness} status={status}")
    return result


__all__ = ["run_phase_p2610b"]
