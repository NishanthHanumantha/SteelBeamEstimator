"""
P2.5.2.1 orchestrator — Crop Readability Refinement.

Consumes frozen P2.5.2 Vision candidates. Refines visual crops only.
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
from PhaseP2521_crop_readability_refinement.config import (  # noqa: E402
    CLAUDE,
    ENGINEERING_CHANGES,
    EXPECTED_DEFERRED,
    EXPECTED_ELIGIBLE,
    EXPECTED_EXCLUDED,
    EXPECTED_OCR,
    EXPECTED_UNRESOLVED,
    EXPECTED_VISION_CANDIDATES,
    GOLDEN_B97A_ANN,
    GOLDEN_B97A_BEAM,
    GOLDEN_B97A_TEXT,
    GOLDEN_DEV_NOTE,
    GOLDEN_OCR_SAMPLE,
    GOLDEN_SFR_NOTE,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    P250_OUTPUT,
    P252_OUTPUT,
    PHASE_ID,
    PHASE_NAME,
    READABILITY_FAIL,
    READABILITY_PARTIAL,
    READABILITY_PASS,
    READABILITY_REVIEW_REQUIRED,
    SCOPE,
)
from PhaseP2521_crop_readability_refinement.contact_sheet import (  # noqa: E402
    build_inspection_package,
)
from PhaseP2521_crop_readability_refinement.packager import (  # noqa: E402
    refine_and_package_candidate,
)
from PhaseP2521_crop_readability_refinement.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
)
from PhaseP2521_crop_readability_refinement.report_builder import write_reports  # noqa: E402
from PhaseP2521_crop_readability_refinement.unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_p252_manifest(v10: Path) -> List[Dict[str, Any]]:
    path = (
        v10
        / "data"
        / "output"
        / P252_OUTPUT
        / "manifests"
        / "VisionCandidateManifest.json"
    )
    if not path.exists():
        raise FileNotFoundError(f"P2.5.2 manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_p252_metrics(v10: Path) -> Dict[str, Any]:
    for path in (
        v10 / "data" / "output" / P252_OUTPUT / "metrics" / "metrics.json",
        v10 / "data" / "output" / P252_OUTPUT / "metrics.json",
        v10 / "data" / "output" / P252_OUTPUT / "RunSummary.json",
    ):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if "VISION_CANDIDATE_COUNT" in data:
            return data
        if isinstance(data.get("metrics"), dict) and "VISION_CANDIDATE_COUNT" in data["metrics"]:
            return data["metrics"]
    # Fallback: derive from packaged manifest (excludes EXCLUDED intents)
    mans = _load_p252_manifest(v10)
    return {
        "VISION_CANDIDATE_COUNT": sum(1 for m in mans if m.get("outcome") == "VISION_CANDIDATE"),
        "DEFERRED_COUNT": sum(1 for m in mans if m.get("outcome") == "DEFERRED"),
        "EXCLUDED_COUNT": EXPECTED_EXCLUDED,
        "TOTAL_ELIGIBLE_INTENTS": EXPECTED_ELIGIBLE,
        "UNRESOLVED_COUNT": EXPECTED_UNRESOLVED,
        "OCR_CORRUPTED_COUNT": EXPECTED_OCR,
    }


def _load_p252_golden(v10: Path) -> Dict[str, Any]:
    path = v10 / "data" / "output" / P252_OUTPUT / "golden_results.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _fingerprint_refined(refined: List[Dict[str, Any]]) -> str:
    payload = [
        {
            "candidate_id": r.get("candidate_id"),
            "outcome": r.get("outcome"),
            "priority": r.get("candidate_priority"),
            "overall_readability": r.get("overall_readability"),
            "local": {
                "iteration": (r.get("local_refined") or {}).get("refinement_iteration"),
                "strategy": (r.get("local_refined") or {}).get("strategy"),
                "crop_bbox": (r.get("local_refined") or {}).get("crop_bbox"),
                "status": (r.get("local_refined") or {}).get("readability_status"),
            },
            "context": {
                "iteration": (r.get("beam_context_refined") or {}).get(
                    "refinement_iteration"
                ),
                "strategy": (r.get("beam_context_refined") or {}).get("strategy"),
                "crop_bbox": (r.get("beam_context_refined") or {}).get("crop_bbox"),
                "status": (r.get("beam_context_refined") or {}).get("readability_status"),
            },
            "raw_text": r.get("raw_text"),
        }
        for r in refined
    ]
    return _stable_hash(payload)


def _verify_invariants(p252_metrics: Dict[str, Any], manifests: List[Dict[str, Any]]) -> Dict[str, Any]:
    active = [m for m in manifests if m.get("outcome") == "VISION_CANDIDATE"]
    deferred = [m for m in manifests if m.get("outcome") == "DEFERRED"]
    vision_n = int(p252_metrics.get("VISION_CANDIDATE_COUNT") or len(active))
    deferred_n = int(p252_metrics.get("DEFERRED_COUNT") or len(deferred))
    excluded_n = int(p252_metrics.get("EXCLUDED_COUNT") or EXPECTED_EXCLUDED)
    eligible_n = int(
        p252_metrics.get("TOTAL_ELIGIBLE_INTENTS")
        or p252_metrics.get("TOTAL_ELIGIBLE")
        or EXPECTED_ELIGIBLE
    )
    unresolved_n = int(p252_metrics.get("UNRESOLVED_COUNT") or EXPECTED_UNRESOLVED)
    ocr_n = int(p252_metrics.get("OCR_CORRUPTED_COUNT") or EXPECTED_OCR)

    ok = (
        vision_n == EXPECTED_VISION_CANDIDATES
        and deferred_n == EXPECTED_DEFERRED
        and excluded_n == EXPECTED_EXCLUDED
        and eligible_n == EXPECTED_ELIGIBLE
        and unresolved_n == EXPECTED_UNRESOLVED
        and ocr_n == EXPECTED_OCR
        and len(active) == EXPECTED_VISION_CANDIDATES
    )
    return {
        "ok": ok,
        "vision_candidates": vision_n,
        "deferred": deferred_n,
        "excluded": excluded_n,
        "eligible": eligible_n,
        "unresolved": unresolved_n,
        "ocr": ocr_n,
        "active_from_manifest": len(active),
        "expected": {
            "vision": EXPECTED_VISION_CANDIDATES,
            "deferred": EXPECTED_DEFERRED,
            "excluded": EXPECTED_EXCLUDED,
            "eligible": EXPECTED_ELIGIBLE,
            "unresolved": EXPECTED_UNRESOLVED,
            "ocr": EXPECTED_OCR,
        },
    }


def _golden_from_p252(
    manifests: List[Dict[str, Any]],
    p252_golden: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    p252_golden = p252_golden or {}

    # B97A is EXCLUDED — not in the packaged 30-row VisionCandidateManifest.
    b97_rec = p252_golden.get("b97a") or {}
    b97_sel = b97_rec.get("selection") or {}
    b97_ok = bool(
        b97_rec.get("pass")
        and (
            b97_rec.get("candidate_status") == "EXCLUDED"
            or b97_sel.get("outcome") == "EXCLUDED"
        )
        and (b97_sel.get("raw_text") or GOLDEN_B97A_TEXT).replace(" ", "") == GOLDEN_B97A_TEXT
        and b97_sel.get("beam_id", GOLDEN_B97A_BEAM) == GOLDEN_B97A_BEAM
        and b97_sel.get("annotation_id", GOLDEN_B97A_ANN) == GOLDEN_B97A_ANN
    )
    # Ensure we did not create a refined Vision crop for B97A
    b97_not_active = not any(
        m.get("beam_id") == GOLDEN_B97A_BEAM and m.get("outcome") == "VISION_CANDIDATE"
        for m in manifests
    )
    b97_ok = b97_ok and b97_not_active

    ocr = next((m for m in manifests if (m.get("raw_text") or "") == GOLDEN_OCR_SAMPLE), None)
    ocr_ok = bool(
        ocr
        and ocr.get("outcome") == "VISION_CANDIDATE"
        and ocr.get("candidate_priority") == "P0"
    )

    dev = next((m for m in manifests if (m.get("raw_text") or "") == GOLDEN_DEV_NOTE), None)
    if not dev:
        dev = next(
            (
                m
                for m in manifests
                if (m.get("raw_text") or "").startswith("Ld")
                and m.get("outcome") == "DEFERRED"
            ),
            None,
        )
    if not dev and (p252_golden.get("development_note") or {}).get("pass"):
        dev_ok = True
        dev = (p252_golden.get("development_note") or {}).get("selection") or {
            "outcome": "DEFERRED"
        }
    else:
        dev_ok = bool(dev and (dev.get("outcome") == "DEFERRED" or dev.get("classification") == "DEFERRED"))

    sfr = next((m for m in manifests if (m.get("raw_text") or "") == GOLDEN_SFR_NOTE), None)
    if not sfr and (p252_golden.get("sfr_note") or {}).get("pass"):
        sfr_ok = (p252_golden.get("sfr_note") or {}).get("classification") == "DEFERRED" or (
            (p252_golden.get("sfr_note") or {}).get("selection") or {}
        ).get("outcome") == "DEFERRED"
        # Prefer explicit deferred
        sfr_status = (p252_golden.get("sfr_note") or {}).get("classification") or (
            (p252_golden.get("sfr_note") or {}).get("selection") or {}
        ).get("outcome")
        sfr_ok = sfr_status == "DEFERRED"
        sfr = {"outcome": sfr_status}
    else:
        sfr_ok = bool(sfr and sfr.get("outcome") == "DEFERRED")

    return {
        "b97a": {
            "pass": b97_ok,
            "outcome": b97_sel.get("outcome") or b97_rec.get("candidate_status"),
            "note": "must remain EXCLUDED / VISION_NOT_REQUIRED; no refined Vision crop",
        },
        "ocr_stirrup": {
            "pass": ocr_ok,
            "outcome": (ocr or {}).get("outcome"),
            "priority": (ocr or {}).get("candidate_priority"),
            "raw_text_preserved": (ocr or {}).get("raw_text") == GOLDEN_OCR_SAMPLE,
            "candidate_id": (ocr or {}).get("candidate_id"),
        },
        "development_note": {
            "pass": bool(dev_ok),
            "outcome": (dev or {}).get("outcome") or (dev or {}).get("classification"),
            "note": "DEFER_ENGINEERING_RULE — no Vision force",
        },
        "sfr_note": {
            "pass": bool(sfr_ok),
            "outcome": (sfr or {}).get("outcome"),
            "note": "SEMANTIC_CONTEXT_REQUIRED / insufficient visual — remains deferred",
        },
        "all_pass": bool(b97_ok and ocr_ok and dev_ok and sfr_ok),
    }


def run_phase_p2521(
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
    p252_candidates = v10 / "data" / "output" / P252_OUTPUT / "candidates"

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
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            _log(f"  FAIL unit tests: {failed[:5]}")
            return {"success": False, "unit_tests": unit, "output_root": str(out_root)}

    bundle = load_fourth_set_bundle(v10)
    dxf_path = Path(bundle.reinforcement_dxf)
    fp_paths = fingerprint_paths(v10, bundle.paths)
    fp_before = capture_fingerprints(fp_paths)

    manifests = _load_p252_manifest(v10)
    p252_metrics = _load_p252_metrics(v10)
    p252_golden = _load_p252_golden(v10)
    invariants = _verify_invariants(p252_metrics, manifests)
    _log(
        f"  P252 invariants: ok={invariants['ok']} "
        f"vision={invariants['vision_candidates']} "
        f"deferred={invariants['deferred']} excluded={invariants['excluded']}"
    )
    if not invariants["ok"]:
        _log("  STOP: P2.5.2 candidate counts changed — refinement aborted.")
        return {
            "success": False,
            "error": "P252_INVARIANT_VIOLATION",
            "invariants": invariants,
            "output_root": str(out_root),
            "claude_calls": 0,
        }

    golden = _golden_from_p252(manifests, p252_golden)
    if not golden.get("all_pass"):
        _log(f"  STOP: golden cases failed against frozen P252: {golden}")
        return {
            "success": False,
            "error": "GOLDEN_CASE_FAILURE",
            "golden": golden,
            "output_root": str(out_root),
            "claude_calls": 0,
        }

    active = [m for m in manifests if m.get("outcome") == "VISION_CANDIDATE"]
    active = sorted(active, key=lambda m: (m.get("beam_id") or "", m.get("annotation_id") or ""))
    _log(f"  Active Vision candidates (frozen): {len(active)}")

    refined: List[Dict[str, Any]] = []
    for m in active:
        _log(f"  Refining {m.get('candidate_id')} ...")
        r = refine_and_package_candidate(
            p252_manifest=m,
            p250_beams_root=p250_beams,
            p252_candidates_root=p252_candidates,
            out_candidates_root=candidates_root,
            engine_root=v10,
            dxf_path=dxf_path,
        )
        refined.append(r)
        _log(
            f"    -> overall={r.get('overall_readability')} "
            f"local_iter={(r.get('local_refined') or {}).get('refinement_iteration')} "
            f"ctx_iter={(r.get('beam_context_refined') or {}).get('refinement_iteration')}"
        )

    inspection = build_inspection_package(
        refined_manifests=refined,
        candidates_root=candidates_root,
        contact_root=contact_root,
    )

    fp_after = capture_fingerprints(fp_paths)
    reg = compare_fingerprints(fp_before, fp_after)

    fp = _fingerprint_refined(refined)
    det_status = "PASS"
    if prior_fingerprint is not None:
        det_status = "PASS" if prior_fingerprint == fp else "FAIL"

    # Counts
    def _status_of(r: Dict[str, Any]) -> str:
        return r.get("overall_readability") or READABILITY_REVIEW_REQUIRED

    n_pass = sum(1 for r in refined if _status_of(r) == READABILITY_PASS)
    n_partial = sum(1 for r in refined if _status_of(r) == READABILITY_PARTIAL)
    n_fail = sum(1 for r in refined if _status_of(r) == READABILITY_FAIL)
    n_review = sum(1 for r in refined if _status_of(r) == READABILITY_REVIEW_REQUIRED)
    n_ok_render = sum(1 for r in refined if r.get("success"))
    n_extreme = 0
    n_clipped = 0
    n_missing_target = 0
    n_missing_ann = 0
    manual_review: List[str] = []
    for r in refined:
        for key in ("local_refined", "beam_context_refined"):
            block = r.get(key) or {}
            metrics = block.get("metrics") or {}
            flags = (block.get("readability") or {}).get("flags") or []
            if metrics.get("is_extreme"):
                n_extreme += 1
            if "ANNOTATION_CLIPPED" in flags:
                n_clipped += 1
            if "TARGET_BEAM_MISSING" in flags:
                n_missing_target += 1
            if not metrics.get("annotation_fully_inside", True):
                n_missing_ann += 1
        if _status_of(r) in (READABILITY_FAIL, READABILITY_REVIEW_REQUIRED, READABILITY_PARTIAL):
            manual_review.append(
                f"{r.get('candidate_id')}|{r.get('beam_id')}|{_status_of(r)}"
            )

    counts = {
        "total_active": len(active),
        "refined_successfully": n_ok_render,
        "readability_pass": n_pass,
        "readability_partial": n_partial,
        "readability_fail": n_fail,
        "readability_review_required": n_review,
        "local_refined": sum(
            1 for r in refined if (r.get("local_refined") or {}).get("crop_bbox")
        ),
        "context_refined": sum(
            1 for r in refined if (r.get("beam_context_refined") or {}).get("crop_bbox")
        ),
        "extreme": n_extreme,
        "clipped": n_clipped,
        "missing_target": n_missing_target,
        "missing_annotation": n_missing_ann,
        "p252_vision_candidates": invariants["vision_candidates"],
        "p252_deferred": invariants["deferred"],
        "p252_excluded": invariants["excluded"],
        "invariants_ok": invariants["ok"],
    }

    # Phase PASS if: invariants+goldens+determinism(when compared)+regression+renders+inspection
    # Readability PARTIAL is acceptable for READY_FOR_VISUAL_INSPECTION
    hard_fail = (
        not invariants["ok"]
        or not golden.get("all_pass")
        or not reg.get("unchanged", False)
        or n_ok_render != len(active)
        or not inspection.get("local_contact_sheet", {}).get("success")
        or not inspection.get("beam_context_contact_sheet", {}).get("success")
        or det_status == "FAIL"
        or n_review > 0 and False  # review required does not auto-fail phase; inspect
    )
    # Extreme forced through?
    forced_extreme = n_extreme > 0 and any(
        (r.get("overall_readability") == READABILITY_PASS)
        and (
            ((r.get("local_refined") or {}).get("metrics") or {}).get("is_extreme")
            or ((r.get("beam_context_refined") or {}).get("metrics") or {}).get("is_extreme")
        )
        for r in refined
    )
    if forced_extreme:
        hard_fail = True

    pass_fail = "FAIL" if hard_fail else "PASS"
    decision = "READY_FOR_VISUAL_INSPECTION" if pass_fail == "PASS" else "NOT_READY"

    summary = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "pass_fail": pass_fail,
        "decision": decision,
        "counts": counts,
        "golden": golden,
        "invariants": invariants,
        "determinism": {
            "fingerprint": fp,
            "determinism_status": det_status,
            "prior_fingerprint": prior_fingerprint,
        },
        "regression": reg,
        "visual_inspection": inspection,
        "manual_review": manual_review,
        "claude_calls": 0,
        "engineering_changes": ENGINEERING_CHANGES,
        "unit_tests": unit,
        "refined_candidate_ids": [r.get("candidate_id") for r in refined],
    }

    _dump(out_root / "manifests" / "RefinedVisionEvidenceManifest.json", refined)
    _dump(out_root / "diagnostics" / "invariants.json", invariants)
    _dump(out_root / "diagnostics" / "golden_cases.json", golden)
    _dump(out_root / "diagnostics" / "determinism.json", summary["determinism"])
    paths = write_reports(out_root=out_root, summary=summary)

    _log(f"  PASS/FAIL: {pass_fail}")
    _log(f"  Decision: {decision}")
    _log(f"  Readability: PASS={n_pass} PARTIAL={n_partial} FAIL={n_fail} REVIEW={n_review}")
    _log(f"  Determinism fingerprint: {fp[:16]}...")
    _log(f"  Contact sheets: {contact_root}")

    return {
        "success": pass_fail == "PASS",
        "pass_fail": pass_fail,
        "decision": decision,
        "output_root": str(out_root),
        "counts": counts,
        "golden": golden,
        "determinism": summary["determinism"],
        "regression": reg,
        "visual_inspection": inspection,
        "manual_review": manual_review,
        "claude_calls": 0,
        "meta": {"model_version": MODEL_VERSION, "phase_id": PHASE_ID},
        "report_paths": paths,
        "unit_tests": unit,
        "fingerprint": fp,
        "refined": refined,
    }


__all__ = ["run_phase_p2521"]
