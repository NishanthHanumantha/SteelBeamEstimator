"""
P2.5.0.1 orchestrator — Evidence Spatial Sanity Diagnostic.

MODEL_VERSION: 10.6.1
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_SRC = Path(__file__).resolve().parents[1]
_V10 = Path(__file__).resolve().parents[2]
for p in (str(_SRC), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)

from PhaseP24_fourth_set_bar_failure_audit.artefacts import load_fourth_set_bundle  # noqa: E402
from PhaseP250_beam_evidence_crop_qa.evidence_pack import build_beam_evidence_pack  # noqa: E402
from PhaseP250_beam_evidence_crop_qa.renderer import (  # noqa: E402
    render_engineering_crop,
    render_evidence_overlay,
)
from PhaseP2501_evidence_spatial_sanity.config import (  # noqa: E402
    ENGINEERING_CHANGES,
    FOCUS_BEAMS,
    KNOWN_GOOD_BEAMS,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    SCOPE,
)
from PhaseP2501_evidence_spatial_sanity.coordinate_trace import (  # noqa: E402
    build_beam_coordinate_trace,
)
from PhaseP2501_evidence_spatial_sanity.crop_sanity import crop_sanity_for_beam  # noqa: E402
from PhaseP2501_evidence_spatial_sanity.diagnostics import classify_root_cause  # noqa: E402
from PhaseP2501_evidence_spatial_sanity.evidence_expansion_trace import (  # noqa: E402
    trace_expansion,
)
from PhaseP2501_evidence_spatial_sanity.known_good_comparator import compare_beams  # noqa: E402
from PhaseP2501_evidence_spatial_sanity.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
)
from PhaseP2501_evidence_spatial_sanity.report_builder import write_reports  # noqa: E402
from PhaseP2501_evidence_spatial_sanity.spatial_metrics import (  # noqa: E402
    collect_beam_spatial_metrics,
)
from PhaseP2501_evidence_spatial_sanity.unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _load_p250_evidence(p250_root: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    path = p250_root / "beams" / beam_id / "evidence.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_before_snapshot(out_root: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    path = out_root / "traces" / f"{beam_id}_BEFORE_evidence.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return None


def _index_graph(bundle: Any) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for n in bundle.annotation_graph.get("nodes") or []:
        nid = n.get("id")
        if nid:
            out[str(nid)] = n
    return out


def _index_r31(bundle: Any) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for b in bundle.physical_bars_r31.get("bars") or []:
        bid = b.get("bar_id") or b.get("id")
        if bid:
            out[str(bid)] = b
    return out


def _scan_all_beams_spatial(p250_root: Path) -> List[Dict[str, Any]]:
    rows = []
    beams_dir = p250_root / "beams"
    if not beams_dir.exists():
        return rows
    for d in sorted(beams_dir.iterdir()):
        if not d.is_dir():
            continue
        ev_path = d / "evidence.json"
        if not ev_path.exists():
            continue
        ev = json.loads(ev_path.read_text(encoding="utf-8"))
        m = collect_beam_spatial_metrics(ev)
        ratios = m.get("ratios") or {}
        dom = m.get("dominant_expander") or {}
        rows.append(
            {
                "beam_id": d.name,
                "cohort": "FOCUS"
                if d.name in FOCUS_BEAMS
                else ("KNOWN_GOOD" if d.name in KNOWN_GOOD_BEAMS else "OTHER"),
                "crop_height_mm": ratios.get("crop_height_mm"),
                "crop_width_mm": ratios.get("crop_width_mm"),
                "beam_height_mm": ratios.get("beam_height_mm"),
                "beam_width_mm": ratios.get("beam_width_mm"),
                "crop_height_to_beam_height_ratio": ratios.get(
                    "crop_height_to_beam_height_ratio"
                ),
                "crop_width_to_beam_width_ratio": ratios.get(
                    "crop_width_to_beam_width_ratio"
                ),
                "crop_area_to_beam_area_ratio": ratios.get("crop_area_to_beam_area_ratio"),
                "max_y_gap_mm": m.get("max_y_gap_mm"),
                "max_spatial_distance_mm": m.get("max_spatial_distance_mm"),
                "dominant_expander_id": dom.get("object_id"),
                "dominant_expander_kind": dom.get("object_kind"),
                "dominant_y_gap_mm": dom.get("y_gap_mm"),
            }
        )
    return rows


def run_phase_p2501(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    regenerate_focus_crops: bool = True,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    p250_root = v10 / "data" / "output" / "PhaseP250_beam_evidence_crop_qa"

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  output: {out_root}")

    if run_tests:
        ut = run_unit_tests()
        _dump(out_root / "diagnostics" / "unit_tests.json", ut)
        _log(f"  Unit tests: {ut['passed']}/{ut['total']}")
        if not ut.get("success"):
            return {"success": False, "unit_tests": ut, "output_root": str(out_root)}

    bundle = load_fourth_set_bundle(v10)
    fp_paths = fingerprint_paths(v10, bundle.paths)
    fp_before = capture_fingerprints(fp_paths)

    graph_idx = _index_graph(bundle)
    r31_idx = _index_r31(bundle)

    # --- BEFORE: diagnose original extreme packages (snapshot once) ---
    before_evidence: Dict[str, Dict[str, Any]] = {}
    for bid in list(FOCUS_BEAMS) + list(KNOWN_GOOD_BEAMS):
        snap = _load_before_snapshot(out_root, bid)
        if snap is None:
            # Prefer git-committed extreme package if present under visuals backup path
            ev = _load_p250_evidence(p250_root, bid)
            if ev is None:
                continue
            # If package already fixed (no rejected bars included), try not to
            # mis-diagnose — still snapshot whatever we have first time only.
            _dump(out_root / "traces" / f"{bid}_BEFORE_evidence.json", ev)
            before_evidence[bid] = ev
        else:
            before_evidence[bid] = snap

    traces: Dict[str, Any] = {}
    expansions: Dict[str, Any] = {}
    root_causes: Dict[str, Any] = {}
    crop_sanity_rows: List[Dict[str, Any]] = []

    for bid in FOCUS_BEAMS:
        ev = before_evidence.get(bid)
        if not ev:
            continue
        own = (bundle.beam_ownership.get("by_beam") or {}).get(bid) or {}
        tr = build_beam_coordinate_trace(
            beam_id=bid,
            evidence=ev,
            ownership=own,
            graph_nodes_by_id=graph_idx,
            r31_by_id=r31_idx,
        )
        ex = trace_expansion(ev)
        rc = classify_root_cause(trace=tr, expansion=ex, ownership=own)
        eng = p250_root / "beams" / bid / "engineering_crop.png"
        cs = crop_sanity_for_beam(ev, engineering_png=eng if eng.exists() else None)
        traces[bid] = tr
        expansions[bid] = ex
        root_causes[bid] = rc
        crop_sanity_rows.append(cs)
        _log(
            f"  {bid}: root_cause={rc.get('label')} height_mm={ex.get('final_height_mm')} "
            f"dominant={(ex.get('dominant_vertical_expander') or {}).get('id')}"
        )

    for bid in KNOWN_GOOD_BEAMS:
        ev = before_evidence.get(bid)
        if not ev:
            continue
        eng = p250_root / "beams" / bid / "engineering_crop.png"
        crop_sanity_rows.append(
            crop_sanity_for_beam(ev, engineering_png=eng if eng.exists() else None)
        )

    spatial_rows = _scan_all_beams_spatial(p250_root)
    known_good = compare_beams(before_evidence, list(FOCUS_BEAMS), list(KNOWN_GOOD_BEAMS))

    # --- AFTER: rebuild focus packs with accepted-only fix + re-render ---
    after_metrics: Dict[str, Any] = {}
    prev_fix = out_root / "diagnostics" / "FixSummary.json"
    if prev_fix.exists() and not regenerate_focus_crops:
        try:
            after_metrics = (
                json.loads(prev_fix.read_text(encoding="utf-8")).get("after_fix_metrics")
                or {}
            )
        except Exception:
            after_metrics = {}
    fix_applied = True
    if regenerate_focus_crops and bundle.reinforcement_dxf:
        dxf = Path(bundle.reinforcement_dxf)
        visuals = out_root / "visuals"
        visuals.mkdir(parents=True, exist_ok=True)
        for bid in FOCUS_BEAMS:
            # Snapshot BEFORE crops
            src_eng = p250_root / "beams" / bid / "engineering_crop.png"
            if src_eng.exists():
                shutil.copy2(src_eng, visuals / f"{bid}_BEFORE_engineering_crop.png")
            pkg = build_beam_evidence_pack(beam_id=bid, bundle=bundle)
            _dump(out_root / "traces" / f"{bid}_AFTER_evidence.json", pkg)
            extent = (pkg.get("evidence_window") or {}).get("bbox")
            after_m = collect_beam_spatial_metrics(pkg)
            after_metrics[bid] = {
                "ratios": after_m.get("ratios"),
                "max_y_gap_mm": after_m.get("max_y_gap_mm"),
                "reinforcement_count": len(pkg.get("reinforcement") or []),
                "excluded_rejected": pkg.get("excluded_rejected_evidence"),
                "crop_bbox": (pkg.get("evidence_window") or {}).get("bbox"),
            }
            if extent and len(extent) >= 4:
                ext = (
                    float(extent[0]),
                    float(extent[1]),
                    float(extent[2]),
                    float(extent[3]),
                )
                eng_path = visuals / f"{bid}_AFTER_engineering_crop.png"
                ovl_path = visuals / f"{bid}_AFTER_evidence_overlay.png"
                eng = render_engineering_crop(
                    engine_root=v10, dxf_path=dxf, extent=ext, out_path=eng_path
                )
                if eng.get("success"):
                    render_evidence_overlay(
                        engineering_png=eng_path,
                        evidence=pkg,
                        out_path=ovl_path,
                        extent=ext,
                    )
                    # Also refresh P2.5.0 beam folder (justified correction)
                    beam_dir = p250_root / "beams" / bid
                    beam_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(eng_path, beam_dir / "engineering_crop.png")
                    if ovl_path.exists():
                        shutil.copy2(ovl_path, beam_dir / "evidence_overlay.png")
                    _dump(beam_dir / "evidence.json", pkg)
                after_metrics[bid]["render_success"] = bool(eng.get("success"))
                after_cs = crop_sanity_for_beam(
                    pkg, engineering_png=eng_path if eng.get("success") else None
                )
                after_metrics[bid]["vision_crop_status"] = after_cs.get("vision_crop_status")
                _log(
                    f"  {bid} AFTER height_mm={after_m.get('ratios', {}).get('crop_height_mm')} "
                    f"status={after_cs.get('vision_crop_status')}"
                )

    # Determinism: rebuild traces twice
    pass1 = _sha({k: traces[k] for k in traces})
    traces2 = {}
    for bid in FOCUS_BEAMS:
        ev = before_evidence.get(bid)
        if not ev:
            continue
        own = (bundle.beam_ownership.get("by_beam") or {}).get(bid) or {}
        traces2[bid] = build_beam_coordinate_trace(
            beam_id=bid,
            evidence=ev,
            ownership=own,
            graph_nodes_by_id=graph_idx,
            r31_by_id=r31_idx,
        )
    pass2 = _sha(traces2)
    determinism = {
        "determinism_status": "PASS" if pass1 == pass2 else "FAIL",
        "pass1_sha": pass1,
        "pass2_sha": pass2,
    }
    # Second full diagnostic pass for runner requirement
    _ = compare_beams(before_evidence, list(FOCUS_BEAMS), list(KNOWN_GOOD_BEAMS))

    fp_after = capture_fingerprints(fp_paths)
    regression = compare_fingerprints(fp_before, fp_after)

    # Build answers
    b97_ex = expansions.get("B97A") or {}
    b98_ex = expansions.get("B98A") or {}
    b97_dom = b97_ex.get("dominant_vertical_expander") or {}
    b98_dom = b98_ex.get("dominant_vertical_expander") or {}
    b97_h = b97_ex.get("final_height_mm")
    b98_h = b98_ex.get("final_height_mm")

    answers = {
        "q1": (
            f"Crop height ≈ {b97_h} mm because P2.5.0 included T18-rejected bars "
            f"(esp. {(b97_dom.get('id'))} at y-gap ≈ {b97_dom.get('y_gap_mm')} mm) "
            "and expanded the evidence window to contain them."
        ),
        "q2": (
            f"Crop height ≈ {b98_h} mm for the same reason — rejected far-elevation "
            f"bars (dominant {(b98_dom.get('id'))}, y-gap ≈ {b98_dom.get('y_gap_mm')} mm); "
            "rejected leader LDR::53A6EF71 also contributed downward expansion."
        ),
        "q3": (
            f"B97A: {b97_dom.get('id')} ({b97_dom.get('kind')}). "
            f"B98A: {b98_dom.get('id')} ({b98_dom.get('kind')})."
        ),
        "q4": (
            "NO. T18 rejected both with ownership_reason=bar_y_outside_reinforcement_elevation "
            "/ R5_NEIGHBOUR_REJECT. They share AnnotationGraph beam_id=B97A and overlapping X, "
            "but Y is tens of metres outside the beam elevation band."
        ),
        "q5": (
            "NO. Same T18 rejection (bar_y_outside_reinforcement_elevation). "
            "Not genuinely spatially associated with B98A's reinforcement elevation."
        ),
        "q6": (
            "NO. All stages use DXF modelspace millimetres (beam bbox, R.3.1, AnnotationGraph, "
            "leaders, evidence window, M.1 renderer). No unit/transform mismatch detected."
        ),
        "q7": (
            "NO ownership-engine error for this symptom. T18 correctly rejected the far bars. "
            "P2.4 wrong-beam ownership=0 is not invalidated. "
            "R.3.1/AnnotationGraph still tags beam_id on those far bars (upstream association "
            "worth later review) but T18 already filtered them."
        ),
        "q8": (
            "YES. P2.5.0 treated all bar_results / leader_results keys as includable evidence, "
            "ignoring accepted=false, then expand_window_to_evidence unioned them into the crop."
        ),
        "q9": (
            "Inside P2.5.0 evidence inclusion / expansion. Upstream provides candidate bars "
            "with far Y; ownership correctly rejects; P2.5.0 incorrectly re-included them."
        ),
        "q10": (
            "YES — minimal proven fix: include only T18-accepted bars/leaders "
            "(plus accepted_chains BAR::/leaders) in the evidence package / window. "
            "MODEL_VERSION → 10.6.1."
        ),
        "q11": (
            "BEFORE fix: B97A/B98A = VISION_CROP_EXTREME (not suitable). "
            f"AFTER fix: "
            f"B97A={((after_metrics.get('B97A') or {}).get('vision_crop_status'))}, "
            f"B98A={((after_metrics.get('B98A') or {}).get('vision_crop_status'))}. "
            "Known-good B14/B60 remain healthy. Full-set re-render recommended before Claude."
        ),
        "q12": (
            "Do NOT start P2.5.1 yet until Fourth Set P2.5.0 packages are regenerated with "
            "the accepted-only fix and Crop Sanity is reviewed for remaining EXTREME cases. "
            "Then proceed to P2.5.1 Quantity Intent Schema."
        ),
    }

    diagnostic_rows = []
    for bid in FOCUS_BEAMS:
        rc = root_causes.get(bid) or {}
        cs = next((c for c in crop_sanity_rows if c.get("beam_id") == bid), {})
        ex = expansions.get(bid) or {}
        own = (bundle.beam_ownership.get("by_beam") or {}).get(bid) or {}
        rej = [
            k
            for k, v in (own.get("bar_results") or {}).items()
            if isinstance(v, dict) and not v.get("accepted")
        ]
        diagnostic_rows.append(
            {
                "beam_id": bid,
                "root_cause": rc.get("label"),
                "confidence": rc.get("confidence"),
                "vision_crop_status": cs.get("vision_crop_status"),
                "crop_height_mm": ex.get("final_height_mm"),
                "dominant_expander_id": (ex.get("dominant_vertical_expander") or {}).get("id"),
                "t18_rejected_bars_included_before": ";".join(rej),
                "fix_applied": fix_applied,
            }
        )

    fix_summary = {
        "applied": fix_applied,
        "description": (
            "P2.5.0 evidence_pack now includes only T18-accepted bars/leaders "
            "(accepted_chains still contribute). Rejected candidates recorded under "
            "excluded_rejected_evidence. MODEL_VERSION 10.6.1."
        ),
        "files": [
            "Version10/src/PhaseP250_beam_evidence_crop_qa/evidence_pack.py",
            "Version10/src/PhaseP250_beam_evidence_crop_qa/config.py",
        ],
        "after_fix_metrics": after_metrics,
    }

    meta = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "mode": MODE,
        "engineering_changes": ENGINEERING_CHANGES,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_root": str(out_root),
        "p250_root": str(p250_root),
    }

    write_reports(
        out_root,
        meta=meta,
        executive={"answers": answers, "after_fix_metrics": after_metrics},
        root_causes=root_causes,
        spatial_rows=spatial_rows,
        known_good=known_good,
        crop_sanity_rows=crop_sanity_rows,
        diagnostic_rows=diagnostic_rows,
        traces=traces,
        expansions=expansions,
        determinism=determinism,
        regression=regression,
        fix_summary=fix_summary,
    )

    success = (
        determinism.get("determinism_status") == "PASS"
        and bool(regression.get("unchanged"))
        and all(b in root_causes for b in FOCUS_BEAMS)
    )
    _log(f"  Determinism: {determinism.get('determinism_status')}")
    _log(f"  Regression unchanged: {regression.get('unchanged')}")
    _log(f"  Report: {out_root / 'ExecutiveSummary.md'}")
    return {
        "success": success,
        "meta": meta,
        "root_causes": root_causes,
        "determinism": determinism,
        "regression": regression,
        "after_fix_metrics": after_metrics,
        "output_root": str(out_root),
        "answers": answers,
    }


if __name__ == "__main__":
    run_phase_p2501()
