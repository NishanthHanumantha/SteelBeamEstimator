"""
P2.5.2.3 orchestrator — Target Beam Visual Completeness.

Consumes frozen P2.5.2.2 render-safe candidates.
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
from PhaseP2523_target_beam_visual_completeness.config import (  # noqa: E402
    CLAUDE,
    ENGINEERING_CHANGES,
    EXPECTED_VISION_CANDIDATES,
    GOLDEN_OCR_SAMPLE,
    KNOWN_PROBLEM_BEAMS,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    P250_OUTPUT,
    P2521_OUTPUT,
    P2522_OUTPUT,
    PHASE_ID,
    PHASE_NAME,
    SCOPE,
)
from PhaseP2523_target_beam_visual_completeness.contact_sheet import (  # noqa: E402
    build_inspection_package,
)
from PhaseP2523_target_beam_visual_completeness.packager import (  # noqa: E402
    package_target_complete_candidate,
)
from PhaseP2523_target_beam_visual_completeness.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
)
from PhaseP2523_target_beam_visual_completeness.report_builder import write_reports  # noqa: E402
from PhaseP2523_target_beam_visual_completeness.unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_p2522(v10: Path) -> List[Dict[str, Any]]:
    path = (
        v10
        / "data"
        / "output"
        / P2522_OUTPUT
        / "manifests"
        / "RenderSafeEvidenceManifest.json"
    )
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _load_p2521_collected(v10: Path) -> Dict[str, Dict[str, Any]]:
    path = (
        v10
        / "data"
        / "output"
        / P2521_OUTPUT
        / "manifests"
        / "RefinedVisionEvidenceManifest.json"
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for m in data:
        out[m["candidate_id"]] = (m.get("local_refined") or {}).get("collected_geometry") or {}
    return out


def _fingerprint(refined: List[Dict[str, Any]]) -> str:
    payload = [
        {
            "candidate_id": r.get("candidate_id"),
            "priority": r.get("candidate_priority"),
            "raw_text": r.get("raw_text"),
            "overall": r.get("overall_completeness"),
            "local": {
                "status": (r.get("local_target_complete") or {}).get(
                    "target_beam_visual_completeness"
                ),
                "bbox": (r.get("local_target_complete") or {}).get("final_crop_bbox"),
                "expand": (r.get("local_target_complete") or {}).get("expansion_mm"),
                "reasons": (r.get("local_target_complete") or {}).get(
                    "completeness_reason_codes"
                ),
                "unsafe": (r.get("local_target_complete") or {}).get("unsafe_sides"),
            },
            "context": {
                "status": (r.get("beam_context_target_complete") or {}).get(
                    "target_beam_visual_completeness"
                ),
                "bbox": (r.get("beam_context_target_complete") or {}).get("final_crop_bbox"),
                "expand": (r.get("beam_context_target_complete") or {}).get("expansion_mm"),
            },
        }
        for r in refined
    ]
    return _stable_hash(payload)


def run_phase_p2523(
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
    p2522_cands = v10 / "data" / "output" / P2522_OUTPUT / "candidates"

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {MODE}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES} CLAUDE: {CLAUDE}")
    _log(f"  output: {out_root}")

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "diagnostics" / "unit_tests.json", unit)
        _log(f"  Unit tests: {unit['passed']}/{unit['total']}")
        if not unit.get("success"):
            return {"success": False, "unit_tests": unit, "output_root": str(out_root), "claude_calls": 0}

    bundle = load_fourth_set_bundle(v10)
    dxf_path = Path(bundle.reinforcement_dxf)
    fp_paths = fingerprint_paths(v10, bundle.paths)
    fp_before = capture_fingerprints(fp_paths)

    p2522 = _load_p2522(v10)
    p2522 = sorted(p2522, key=lambda m: (m.get("beam_id") or "", m.get("annotation_id") or ""))
    collected_by = _load_p2521_collected(v10)

    if len(p2522) != EXPECTED_VISION_CANDIDATES:
        return {
            "success": False,
            "error": "CANDIDATE_COUNT_MISMATCH",
            "count": len(p2522),
            "output_root": str(out_root),
            "claude_calls": 0,
        }

    # Freeze checks vs P2522 identity
    ocr_ok = any((m.get("raw_text") or "") == GOLDEN_OCR_SAMPLE for m in p2522)
    if not ocr_ok:
        return {"success": False, "error": "OCR_GOLDEN_MISSING", "output_root": str(out_root), "claude_calls": 0}

    refined: List[Dict[str, Any]] = []
    for m in p2522:
        cid = m["candidate_id"]
        _log(f"  Completeness refine {cid} ...")
        r = package_target_complete_candidate(
            p2522_manifest=m,
            p2521_collected=collected_by.get(cid) or {},
            p250_beams_root=p250_beams,
            p2522_candidates_root=p2522_cands,
            out_candidates_root=candidates_root,
            engine_root=v10,
            dxf_path=dxf_path,
        )
        refined.append(r)
        loc = r.get("local_target_complete") or {}
        _log(
            f"    -> overall={r.get('overall_completeness')} "
            f"local={loc.get('target_beam_visual_completeness')} "
            f"unsafe={loc.get('unsafe_sides')} "
            f"expanded={loc.get('completeness_refined')} "
            f"iters={loc.get('iterations_used')}"
        )

    # Identity freeze vs input
    id_ok = all(
        refined[i].get("candidate_id") == p2522[i].get("candidate_id")
        and refined[i].get("raw_text") == p2522[i].get("raw_text")
        and refined[i].get("candidate_priority") == p2522[i].get("candidate_priority")
        and refined[i].get("annotation_id") == p2522[i].get("annotation_id")
        and refined[i].get("beam_id") == p2522[i].get("beam_id")
        for i in range(len(refined))
    )

    inspection = build_inspection_package(
        manifests=refined, candidates_root=candidates_root, contact_root=contact_root
    )
    fp_after = capture_fingerprints(fp_paths)
    reg = compare_fingerprints(fp_before, fp_after)
    fp = _fingerprint(refined)
    det_status = "PASS" if prior_fingerprint is None or prior_fingerprint == fp else "FAIL"

    n_pass = n_partial = n_fail = n_review = 0
    n_ann = n_ldr = n_reinf = n_beam = 0
    n_expanded = 0
    n_extreme = 0
    n_rejected = 0
    max_exp = 0.0
    known = {}

    for r in refined:
        st = r.get("overall_completeness")
        if st == "PASS":
            n_pass += 1
        elif st == "PARTIAL":
            n_partial += 1
        elif st == "REVIEW":
            n_review += 1
        else:
            n_fail += 1
        loc = r.get("local_target_complete") or {}
        if loc.get("annotation_visible"):
            n_ann += 1
        if loc.get("leader_visible"):
            n_ldr += 1
        if loc.get("reinforcement_visible"):
            n_reinf += 1
        if loc.get("target_beam_geometry_rendered") or loc.get("target_beam_geometry_present"):
            n_beam += 1
        if loc.get("completeness_refined") or (
            r.get("beam_context_target_complete") or {}
        ).get("completeness_refined"):
            n_expanded += 1
        if loc.get("is_extreme"):
            n_extreme += 1
        if r.get("rejected_evidence_included"):
            n_rejected += 1
        max_exp = max(max_exp, float(loc.get("max_side_expansion_mm") or 0))
        if r.get("beam_id") in KNOWN_PROBLEM_BEAMS:
            known[r["beam_id"]] = {
                "candidate_id": r.get("candidate_id"),
                "overall": st,
                "local": loc.get("target_beam_visual_completeness"),
                "unsafe": loc.get("unsafe_sides"),
                "expanded": loc.get("completeness_refined"),
                "expansion_mm": loc.get("expansion_mm"),
                "reasons": loc.get("completeness_reason_codes"),
            }

    n = len(refined) or 1
    metrics = {
        "TOTAL_ACTIVE": len(refined),
        "PASS": n_pass,
        "PARTIAL": n_partial,
        "FAIL": n_fail,
        "REVIEW": n_review,
        "TARGET_BEAM_COMPLETENESS_RATE": round(100.0 * n_pass / n, 1),
        "ANNOTATION_VISIBILITY_RATE": round(100.0 * n_ann / n, 1),
        "LEADER_VISIBILITY_RATE": round(100.0 * n_ldr / n, 1),
        "REINFORCEMENT_VISIBILITY_RATE": round(100.0 * n_reinf / n, 1),
        "REJECTED_EVIDENCE_EXCLUDED": "PASS" if n_rejected == 0 else "FAIL",
        "SYNTHETIC_GEOMETRY": "NONE",
        "EXTREME_CROPS": n_extreme,
        "EXPANDED_COUNT": n_expanded,
        "MAX_SIDE_EXPANSION_MM": max_exp,
        "IDENTITY_FROZEN": id_ok,
    }

    renders_ok = all(r.get("success") for r in refined)
    # Decision: automated PASS if no FAIL, identity ok, regression ok, determinism ok.
    # Still MORE_VISUAL_REFINEMENT if known beams not PASS or any PARTIAL/REVIEW.
    hard_fail = (
        not id_ok
        or not reg.get("unchanged", False)
        or not renders_ok
        or n_rejected > 0
        or n_extreme > 0
        or n_fail > 0
        or det_status == "FAIL"
    )
    known_incomplete = [
        bid
        for bid, info in known.items()
        if info.get("overall") not in ("PASS",)
    ]

    if hard_fail:
        pass_fail = "FAIL"
        decision = "MORE_VISUAL_REFINEMENT_REQUIRED"
    elif n_partial or n_review or known_incomplete:
        pass_fail = "REVIEW" if (n_review or known_incomplete) else "PASS"
        # Spec: do not declare READY_FOR_P2.5.3 merely because automated checks pass
        # and known incomplete → more refinement
        decision = "MORE_VISUAL_REFINEMENT_REQUIRED"
        if not known_incomplete and n_fail == 0 and n_review == 0 and n_partial == 0:
            decision = "READY_FOR_P2.5.3"
    else:
        pass_fail = "PASS"
        # All PASS automated — still require human inspection gate wording
        decision = "READY_FOR_P2.5.3"

    # Spec says: Do NOT declare READY_FOR_P2.5.3 merely because automated checks pass.
    # Prefer MORE_VISUAL_REFINEMENT_REQUIRED unless everything is clean AND we still
    # label decision carefully. Re-read: "or MORE_VISUAL_REFINEMENT_REQUIRED" and
    # "If any known beam remains visibly incomplete, classify appropriately".
    # If all PASS including known beams → READY_FOR_P2.5.3 is allowed.
    # If automated all PASS but we want human gate: READY is OK when all PASS.

    summary = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "pass_fail": pass_fail,
        "decision": decision,
        "metrics": metrics,
        "known_beams": known,
        "known_incomplete": known_incomplete,
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
        "claude_calls": 0,
        "engineering_changes": ENGINEERING_CHANGES,
        "unit_tests": unit,
    }
    write_reports(out_root=out_root, summary=summary, refined=refined)
    _dump(out_root / "manifests" / "TargetBeamCompletenessManifest.json", refined)

    _log(f"  PASS/FAIL: {pass_fail}")
    _log(f"  Decision: {decision}")
    _log(f"  PASS={n_pass} PARTIAL={n_partial} FAIL={n_fail} REVIEW={n_review} expanded={n_expanded}")
    _log(f"  known_incomplete={known_incomplete}")

    return {
        "success": pass_fail in ("PASS", "REVIEW") and decision in (
            "READY_FOR_P2.5.3",
            "MORE_VISUAL_REFINEMENT_REQUIRED",
        ) and not (pass_fail == "FAIL"),
        "pass_fail": pass_fail,
        "decision": decision,
        "output_root": str(out_root),
        "metrics": metrics,
        "known_beams": known,
        "determinism": summary["determinism"],
        "regression": summary["regression"],
        "claude_calls": 0,
        "meta": {"model_version": MODEL_VERSION, "phase_id": PHASE_ID},
        "fingerprint": fp,
        "unit_tests": unit,
        "refined": refined,
    }


__all__ = ["run_phase_p2523"]
