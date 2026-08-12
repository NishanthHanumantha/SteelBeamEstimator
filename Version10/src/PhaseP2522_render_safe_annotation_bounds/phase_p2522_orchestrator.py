"""
P2.5.2.2 orchestrator — Render-Safe Annotation Bounds.

Consumes frozen P2.5.2.1 refined active candidates.
No Claude. No engineering mutations. No candidate reselection.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_SRC = Path(__file__).resolve().parents[1]
_V10 = Path(__file__).resolve().parents[2]
for p in (str(_SRC), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)

from PhaseP24_fourth_set_bar_failure_audit.artefacts import (  # noqa: E402
    load_fourth_set_bundle,
)
from PhaseP2522_render_safe_annotation_bounds.config import (  # noqa: E402
    CLAUDE,
    ENGINEERING_CHANGES,
    EXPECTED_VISION_CANDIDATES,
    FLAG_ANNOTATION_RENDER_CLIPPED,
    FLAG_ANNOTATION_RENDER_EDGE_RISK,
    FLAG_BOTTOM_ANNOTATION_EDGE_RISK,
    FLAG_LEADER_RENDER_EDGE_RISK,
    FLAG_TOP_ANNOTATION_EDGE_RISK,
    GOLDEN_B97A_BEAM,
    GOLDEN_OCR_SAMPLE,
    MAX_RENDER_SAFETY_ITERATIONS,
    MIN_RENDER_SAFE_MARGIN_PX,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    P250_OUTPUT,
    P2521_OUTPUT,
    P252_OUTPUT,
    PHASE_ID,
    PHASE_NAME,
    READABILITY_FAIL,
    READABILITY_PARTIAL,
    READABILITY_PASS,
    READABILITY_REVIEW,
    SCOPE,
)
from PhaseP2522_render_safe_annotation_bounds.contact_sheet import (  # noqa: E402
    build_inspection_package,
)
from PhaseP2522_render_safe_annotation_bounds.packager import (  # noqa: E402
    package_render_safe_candidate,
)
from PhaseP2522_render_safe_annotation_bounds.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
)
from PhaseP2522_render_safe_annotation_bounds.report_builder import write_reports  # noqa: E402
from PhaseP2522_render_safe_annotation_bounds.unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_p2521(v10: Path) -> List[Dict[str, Any]]:
    path = (
        v10
        / "data"
        / "output"
        / P2521_OUTPUT
        / "manifests"
        / "RefinedVisionEvidenceManifest.json"
    )
    if not path.exists():
        raise FileNotFoundError(f"P2.5.2.1 manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_p252_metrics(v10: Path) -> Dict[str, Any]:
    path = v10 / "data" / "output" / P252_OUTPUT / "metrics" / "metrics.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _fingerprint(refined: List[Dict[str, Any]]) -> str:
    payload = [
        {
            "candidate_id": r.get("candidate_id"),
            "overall": r.get("overall_readability"),
            "local": {
                "bbox": (r.get("local_render_safe") or {}).get("crop_bbox"),
                "status": (r.get("local_render_safe") or {}).get("readability_status"),
                "iters": (r.get("local_render_safe") or {}).get("iterations_used"),
                "flags": (r.get("local_render_safe") or {}).get("flags"),
                "margins": (r.get("local_render_safe") or {}).get("margins_px"),
                "safe": (r.get("local_render_safe") or {}).get("render_safe"),
            },
            "context": {
                "bbox": (r.get("beam_context_render_safe") or {}).get("crop_bbox"),
                "status": (r.get("beam_context_render_safe") or {}).get("readability_status"),
                "iters": (r.get("beam_context_render_safe") or {}).get("iterations_used"),
                "flags": (r.get("beam_context_render_safe") or {}).get("flags"),
                "margins": (r.get("beam_context_render_safe") or {}).get("margins_px"),
                "safe": (r.get("beam_context_render_safe") or {}).get("render_safe"),
            },
            "raw_text": r.get("raw_text"),
        }
        for r in refined
    ]
    return _stable_hash(payload)


def run_phase_p2522(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    prior_fingerprint: Optional[str] = None,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    candidates_root = out_root / "candidates"
    candidates_root.mkdir(parents=True, exist_ok=True)
    contact_root = out_root / "contact_sheets"
    p250_beams = v10 / "data" / "output" / P250_OUTPUT / "beams"
    p2521_cands = v10 / "data" / "output" / P2521_OUTPUT / "candidates"

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {MODE}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES} CLAUDE: {CLAUDE}")
    _log(f"  MIN_RENDER_SAFE_MARGIN_PX={MIN_RENDER_SAFE_MARGIN_PX} MAX_ITERS={MAX_RENDER_SAFETY_ITERATIONS}")
    _log(f"  output: {out_root}")

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "diagnostics" / "unit_tests.json", unit)
        _log(f"  Unit tests: {unit['passed']}/{unit['total']}")
        if not unit.get("success"):
            failed = [r for r in (unit.get("results") or []) if not r.get("pass")]
            _log(f"  FAIL unit tests: {failed[:5]}")
            return {"success": False, "unit_tests": unit, "output_root": str(out_root), "claude_calls": 0}

    bundle = load_fourth_set_bundle(v10)
    dxf_path = Path(bundle.reinforcement_dxf)
    fp_paths = fingerprint_paths(v10, bundle.paths)
    fp_before = capture_fingerprints(fp_paths)

    p2521 = _load_p2521(v10)
    p2521 = sorted(p2521, key=lambda m: (m.get("beam_id") or "", m.get("annotation_id") or ""))
    p252_metrics = _load_p252_metrics(v10)
    vision_n = int(p252_metrics.get("VISION_CANDIDATE_COUNT") or EXPECTED_VISION_CANDIDATES)
    invariants_ok = len(p2521) == EXPECTED_VISION_CANDIDATES and vision_n == EXPECTED_VISION_CANDIDATES
    _log(f"  Active from P2521: {len(p2521)} (expected {EXPECTED_VISION_CANDIDATES}) invariants_ok={invariants_ok}")
    if not invariants_ok:
        return {
            "success": False,
            "error": "CANDIDATE_INVARIANT_VIOLATION",
            "output_root": str(out_root),
            "claude_calls": 0,
        }

    # Golden: OCR still present; B97A not in active set
    ocr = next((m for m in p2521 if (m.get("raw_text") or "") == GOLDEN_OCR_SAMPLE), None)
    b97_absent = not any(m.get("beam_id") == GOLDEN_B97A_BEAM for m in p2521)
    golden = {
        "ocr_stirrup": {
            "pass": bool(ocr and ocr.get("outcome") == "VISION_CANDIDATE"),
            "candidate_id": (ocr or {}).get("candidate_id"),
        },
        "b97a_not_active": {"pass": b97_absent},
        "all_pass": bool(ocr and b97_absent),
    }
    if not golden["all_pass"]:
        return {
            "success": False,
            "error": "GOLDEN_CASE_FAILURE",
            "golden": golden,
            "output_root": str(out_root),
            "claude_calls": 0,
        }

    refined: List[Dict[str, Any]] = []
    for m in p2521:
        _log(f"  Render-safe refine {m.get('candidate_id')} ...")
        r = package_render_safe_candidate(
            p2521_manifest=m,
            p250_beams_root=p250_beams,
            p2521_candidates_root=p2521_cands,
            out_candidates_root=candidates_root,
            engine_root=v10,
            dxf_path=dxf_path,
        )
        refined.append(r)
        loc = r.get("local_render_safe") or {}
        _log(
            f"    -> overall={r.get('overall_readability')} "
            f"local_safe={loc.get('render_safe')} "
            f"iters={loc.get('iterations_used')} "
            f"refined={loc.get('render_safety_refined')} "
            f"margins={loc.get('margins_px')}"
        )

    inspection = build_inspection_package(
        manifests=refined, candidates_root=candidates_root, contact_root=contact_root
    )

    fp_after = capture_fingerprints(fp_paths)
    reg = compare_fingerprints(fp_before, fp_after)
    fp = _fingerprint(refined)
    det_status = "PASS"
    if prior_fingerprint is not None:
        det_status = "PASS" if prior_fingerprint == fp else "FAIL"

    # Aggregate metrics
    def _flags(r: Dict[str, Any]) -> List[str]:
        out = []
        for key in ("local_render_safe", "beam_context_render_safe"):
            out.extend((r.get(key) or {}).get("flags") or [])
        return out

    n_geom = 0
    n_safe = 0
    n_clip = 0
    n_edge = 0
    n_leader = 0
    n_top = 0
    n_bot = 0
    n_refined = 0
    n_max = 0
    n_pass = n_partial = n_review = n_fail = 0
    n_extreme = 0
    n_missing_beam = 0
    n_missing_ann = 0
    n_rejected = 0
    max_exp = 0.0
    review_list: List[str] = []

    for r in refined:
        flags = _flags(r)
        loc = r.get("local_render_safe") or {}
        ctx = r.get("beam_context_render_safe") or {}
        if loc.get("geometric_containment") and ctx.get("geometric_containment"):
            n_geom += 1
        if loc.get("render_safe") and ctx.get("render_safe"):
            n_safe += 1
        if FLAG_ANNOTATION_RENDER_CLIPPED in flags:
            n_clip += 1
        if FLAG_ANNOTATION_RENDER_EDGE_RISK in flags:
            n_edge += 1
        if FLAG_LEADER_RENDER_EDGE_RISK in flags:
            n_leader += 1
        if FLAG_TOP_ANNOTATION_EDGE_RISK in flags:
            n_top += 1
        if FLAG_BOTTOM_ANNOTATION_EDGE_RISK in flags:
            n_bot += 1
        if loc.get("render_safety_refined") or ctx.get("render_safety_refined"):
            n_refined += 1
        if loc.get("hit_max_iterations") or ctx.get("hit_max_iterations"):
            n_max += 1
        st = r.get("overall_readability")
        if st == READABILITY_PASS:
            n_pass += 1
        elif st == READABILITY_PARTIAL:
            n_partial += 1
        elif st == READABILITY_REVIEW:
            n_review += 1
            review_list.append(f"{r.get('candidate_id')}|{st}")
        else:
            n_fail += 1
            review_list.append(f"{r.get('candidate_id')}|{st}")
        if loc.get("is_extreme") or ctx.get("is_extreme"):
            n_extreme += 1
        if r.get("rejected_evidence_included"):
            n_rejected += 1
        for block in (loc, ctx):
            max_exp = max(max_exp, float(block.get("max_side_expansion_mm") or 0.0))
            if block.get("annotation_pixel_bbox") is None and "CRITICAL_PIXELS_NOT_FOUND" in (
                block.get("flags") or []
            ):
                n_missing_ann += 1

    metrics = {
        "TOTAL_ACTIVE_CANDIDATES": len(refined),
        "GEOMETRIC_CONTAINMENT_PASS": n_geom,
        "RENDER_SAFE_PASS": n_safe,
        "ANNOTATION_CLIPPING_COUNT": n_clip,
        "ANNOTATION_EDGE_RISK_COUNT": n_edge,
        "LEADER_EDGE_RISK_COUNT": n_leader,
        "TOP_ANNOTATION_EDGE_RISK_COUNT": n_top,
        "BOTTOM_ANNOTATION_EDGE_RISK_COUNT": n_bot,
        "RENDER_SAFETY_REFINEMENT_COUNT": n_refined,
        "MAX_ITERATION_HITS": n_max,
        "READABILITY_PASS": n_pass,
        "READABILITY_PARTIAL": n_partial,
        "READABILITY_REVIEW": n_review,
        "READABILITY_FAIL": n_fail,
        "EXTREME_CROP_COUNT": n_extreme,
        "MISSING_TARGET_BEAM_COUNT": n_missing_beam,
        "MISSING_ANNOTATION_COUNT": n_missing_ann,
        "REJECTED_EVIDENCE_INCLUDED_COUNT": n_rejected,
        "DETERMINISM_PASS": det_status == "PASS",
        "CLAUDE_CALLS": 0,
        "ENGINEERING_CHANGES": ENGINEERING_CHANGES,
        "MAX_SIDE_EXPANSION_MM": max_exp,
    }

    renders_ok = all(r.get("success") for r in refined)
    hard_fail = (
        not invariants_ok
        or not golden.get("all_pass")
        or not reg.get("unchanged", False)
        or not renders_ok
        or n_extreme > 0
        or n_rejected > 0
        or n_fail > 0
        or det_status == "FAIL"
        or n_safe < len(refined)
        or n_geom < len(refined)
        or not inspection.get("local_contact_sheet", {}).get("success")
    )
    # If review required but no hard engineering fail → MORE_DIAGNOSTICS or still READY_FOR_VISUAL if only partial
    if hard_fail:
        pass_fail = "FAIL"
        decision = "FAIL" if (n_fail or n_extreme or n_rejected or not renders_ok) else "MORE_DIAGNOSTICS_REQUIRED"
        if det_status == "FAIL" or not reg.get("unchanged", False) or not invariants_ok:
            decision = "FAIL"
        elif n_safe < len(refined) or n_review > 0:
            decision = "MORE_DIAGNOSTICS_REQUIRED"
    else:
        pass_fail = "PASS"
        decision = "READY_FOR_VISUAL_INSPECTION"

    summary = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "pass_fail": pass_fail,
        "decision": decision,
        "metrics": metrics,
        "golden": golden,
        "invariants_ok": invariants_ok,
        "determinism": {
            "fingerprint": fp,
            "determinism_status": det_status,
            "prior_fingerprint": prior_fingerprint,
        },
        "regression": {
            "unchanged": reg.get("unchanged"),
            "changed_keys": reg.get("changed_keys"),
        },
        "visual_inspection": inspection,
        "manual_review": review_list,
        "claude_calls": 0,
        "engineering_changes": ENGINEERING_CHANGES,
        "unit_tests": unit,
    }

    _dump(out_root / "manifests" / "RenderSafeEvidenceManifest.json", refined)
    paths = write_reports(out_root=out_root, summary=summary, refined=refined)

    _log(f"  PASS/FAIL: {pass_fail}")
    _log(f"  Decision: {decision}")
    _log(
        f"  Render-safe: {n_safe}/{len(refined)} refined={n_refined} "
        f"PASS={n_pass} PARTIAL={n_partial} REVIEW={n_review} FAIL={n_fail}"
    )
    _log(f"  max_side_expansion_mm={max_exp:.1f}")

    return {
        "success": pass_fail == "PASS",
        "pass_fail": pass_fail,
        "decision": decision,
        "output_root": str(out_root),
        "metrics": metrics,
        "golden": golden,
        "determinism": summary["determinism"],
        "regression": summary["regression"],
        "visual_inspection": inspection,
        "manual_review": review_list,
        "claude_calls": 0,
        "meta": {"model_version": MODEL_VERSION, "phase_id": PHASE_ID},
        "report_paths": paths,
        "unit_tests": unit,
        "fingerprint": fp,
        "refined": refined,
    }


__all__ = ["run_phase_p2522"]
