"""P2.6.9 orchestrator. Shadow benchmark. Does not change production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .comparator import apply_overlay, associate_annotations, compare_inventories
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
from .dataset import load_benchmark_targets, load_control_overlay
from .drawing_groups import extract_drawing_groups
from .evaluator import classify_capability, classify_phase, evaluate_controls, production_invariants
from .extractor import extract_detected_groups
from .metrics import aggregate_metrics, beam_metrics
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .report import write_reports
from .unit_tests import run_unit_tests

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run_phase_p269(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_OFFLINE,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (out_root, out_root / "reports", out_root / "inventories"):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode != MODE_OFFLINE:
        raise RuntimeError(f"unsupported P2.6.9 mode {mode!r}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {mode}")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.9 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)
    _dump(out_root / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.9 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.9 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "fingerprints_before.json", before)

    targets = load_benchmark_targets(v10)
    overlays = load_control_overlay()
    _log(f"  loaded benchmark beams: {len(targets)} (expected {TARGET_BEAMS})")

    records: list = []
    for i, target in enumerate(targets, start=1):
        set_key = str(target.get("set_key") or "")
        beam_id = str(target.get("beam_id") or "")
        detected = extract_detected_groups(target.get("r13_model") or {})
        drawing = extract_drawing_groups(target.get("r1_annotations") or [], beam_id=beam_id)
        overlay = overlays.get((set_key, beam_id)) or {}
        expected = apply_overlay(drawing, overlay)
        comparison = compare_inventories(expected=expected, detected=detected)
        associations = associate_annotations(
            annotations=target.get("r1_annotations") or [],
            detected=detected,
            expected=expected,
        )
        metrics = beam_metrics(comparison, associations)
        rec = {
            "phase": PHASE_ID,
            "set_key": set_key,
            "beam_id": beam_id,
            "expected_groups": expected,
            "detected_groups": detected,
            "comparison": comparison,
            "associations": associations,
            "metrics": metrics,
            "discrepancy_notes": list(overlay.get("discrepancy_notes") or []),
            "overlay_provenance": overlay.get("provenance"),
            "production_action": PRODUCTION_ACTION,
            "shadow_only": SHADOW_ONLY,
            "production_routing_changed": False,
            "annotation_count": target.get("annotation_count"),
            "model_found": target.get("model_found"),
        }
        records.append(rec)
        _log(
            f"  [{i}/{len(targets)}] {set_key}/{beam_id} "
            f"exp={comparison.get('expected_group_count')} det={comparison.get('detected_group_count')} "
            f"miss={len(comparison.get('missing_groups') or [])} err={comparison.get('errors')}"
        )

    inv = production_invariants(records)
    controls = evaluate_controls(records)
    aggregate = aggregate_metrics(records)
    capability = classify_capability(aggregate, controls)
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    inventories_complete = all(
        r.get("expected_groups") is not None and r.get("detected_groups") is not None for r in records
    ) and all(r.get("model_found") for r in records)
    production = {
        "production_mutation_count": 0 if fp_cmp.get("unchanged") else len(fp_cmp.get("changed_keys") or []),
        "fingerprints_ok": fp_cmp.get("unchanged"),
        "changed_keys": fp_cmp.get("changed_keys") or [],
        "p266_artefacts_unchanged": fp_cmp.get("unchanged"),
        "p267_artefacts_unchanged": fp_cmp.get("unchanged"),
        "p268_artefacts_unchanged": fp_cmp.get("unchanged"),
        "all_shadow_only": inv.get("all_shadow_only"),
        "all_no_change": inv.get("all_no_change"),
        "engineering_changes": ENGINEERING_CHANGES,
        "steel_quantity_delta": 0,
        "bbs_delta": 0,
        "workbook_delta": 0,
        "production_objects_modified": False,
        "live_vision_invoked": False,
    }
    recommendation = classify_phase(
        tests_ok=bool(unit.get("success")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        production_mutation=int(production["production_mutation_count"]),
        all_shadow=bool(inv.get("all_shadow_only")),
        all_no_change=bool(inv.get("all_no_change")),
        six_beams=len(records) == TARGET_BEAMS,
        inventories_complete=inventories_complete,
    )
    metrics = {
        "target_beams": len(records),
        "aggregate": aggregate,
        "controls": controls,
        "production_invariants": inv,
        "capability": capability,
        "LIVE_VISION_CALLS": 0,
    }
    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "scope": SCOPE,
        "mode": mode,
        "production_write": PRODUCTION_WRITE,
        "engineering_changes": ENGINEERING_CHANGES,
        "pass_fail": (
            "PASS"
            if unit.get("success")
            and fw.get("ok")
            and leak.get("ok")
            and fp_cmp.get("unchanged")
            and inv.get("all_shadow_only")
            and inv.get("all_no_change")
            and len(records) == TARGET_BEAMS
            and inventories_complete
            else "FAIL"
        ),
        "output_root": str(out_root),
        "metrics": metrics,
        "recommendation": recommendation,
        "capability": capability,
        "records": records,
        "unit_tests": unit,
        "firewall": fw,
        "leakage": leak,
        "production": production,
        "decision": recommendation.get("decision"),
        "strength": recommendation.get("strength"),
        "live_vision_invoked": False,
    }
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    dump = dict(result)
    dump.pop("records", None)
    _dump(out_root / "result.json", dump)
    _dump(out_root / "fingerprints_after.json", after)
    _log(f"  decision={result.get('decision')} capability={capability}")
    return result


__all__ = ["run_phase_p269"]
