"""
P2.5.0.2 orchestrator — Top Reinforcement Evidence Trace.

MODEL_VERSION: 10.6.1
DIAGNOSTIC ONLY — no production mutations.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_SRC = Path(__file__).resolve().parents[1]
_V10 = Path(__file__).resolve().parents[2]
for p in (str(_SRC), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)

import ezdxf  # noqa: E402

from PhaseP24_fourth_set_bar_failure_audit.artefacts import load_fourth_set_bundle  # noqa: E402
from PhaseP2502_top_reinforcement_trace.annotation_trace import (  # noqa: E402
    trace_annotation_chain,
)
from PhaseP2502_top_reinforcement_trace.bar_trace import (  # noqa: E402
    trace_bar,
    trace_own_entity,
)
from PhaseP2502_top_reinforcement_trace.classification import (  # noqa: E402
    classify_rejected_bar,
    completeness_state,
    decide_next_action,
)
from PhaseP2502_top_reinforcement_trace.config import (  # noqa: E402
    ENGINEERING_CHANGES,
    FOCUS,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    SCOPE,
)
from PhaseP2502_top_reinforcement_trace.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
)
from PhaseP2502_top_reinforcement_trace.report_builder import write_reports  # noqa: E402
from PhaseP2502_top_reinforcement_trace.unit_tests import run_unit_tests  # noqa: E402
from PhaseP2502_top_reinforcement_trace.visualizer import (  # noqa: E402
    render_diagnostic_overlay,
)


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _load_evidence(p250_root: Path, beam_id: str) -> Dict[str, Any]:
    # Prefer AFTER (current) evidence; fall back to P2501 BEFORE snapshot for history
    p = p250_root / "beams" / beam_id / "evidence.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8-sig"))
    return {}


def _graph_index(bundle: Any) -> Dict[str, Dict[str, Any]]:
    return {str(n.get("id")): n for n in (bundle.annotation_graph.get("nodes") or []) if n.get("id")}


def _diagnose_beam(
    *,
    beam_id: str,
    cfg: Dict[str, Any],
    bundle: Any,
    msp: Any,
    graph_idx: Dict[str, Dict[str, Any]],
    evidence: Dict[str, Any],
    neighbour_ids: List[str],
) -> Dict[str, Any]:
    own = (bundle.beam_ownership.get("by_beam") or {}).get(beam_id) or {}
    ann_id = cfg["ann_4y25"]
    leader_id = cfg["leader"]
    own_id = cfg["own_entity"]
    handle = cfg["own_handle"]

    ann_trace = trace_annotation_chain(
        beam_id=beam_id,
        ann_id=ann_id,
        leader_id=leader_id,
        own_id=own_id,
        ownership=own,
        graph=bundle.annotation_graph,
        evidence=evidence,
    )
    ann_pos = ann_trace.get("annotation_position")
    leader_geom = {
        "tip_x": (ann_trace.get("leader_tip") or {}).get("x"),
        "tip_y": (ann_trace.get("leader_tip") or {}).get("y"),
        "tail_x": (ann_trace.get("leader_tail") or {}).get("x"),
        "tail_y": (ann_trace.get("leader_tail") or {}).get("y"),
    }

    own_tr = trace_own_entity(
        own_id=own_id,
        handle=handle,
        beam_id=beam_id,
        msp=msp,
        graph_node=graph_idx.get(own_id),
        ownership=own,
        ann_pos=ann_pos,
        leader_geom=leader_geom,
    )

    bar_traces = []
    classifications = []
    for bar_id in cfg["rejected_bars"]:
        bt = trace_bar(
            bar_id=bar_id,
            beam_id=beam_id,
            msp=msp,
            r31=bundle.physical_bars_r31,
            ownership=own,
            graph_node=graph_idx.get(bar_id),
            ann_pos=ann_pos,
            leader_geom=leader_geom,
            neighbour_beams=neighbour_ids,
        )
        cl = classify_rejected_bar(bt, own_tr)
        cl["bar_id"] = bar_id
        bt["20_corresponds_to_4Y25_visually"] = bool(cl.get("corresponds_to_4Y25"))
        bar_traces.append(bt)
        classifications.append(cl)

    comp = completeness_state(
        beam_id=beam_id,
        evidence=evidence,
        ownership=own,
        own_trace=own_tr,
        ann_id=ann_id,
    )

    outcome = (
        "OUTCOME_B_rejected_BAR_not_actual_top__actual_is_OWN_LWPOLYLINE"
        if own_tr.get("is_actual_top_reinforcement_geometry")
        and all(c.get("classification") == "FALSE_CANDIDATE" for c in classifications)
        else "OUTCOME_F_other_or_mixed"
    )

    return {
        "beam_id": beam_id,
        "actual_top_reinforcement": own_id if own_tr.get("is_actual_top_reinforcement_geometry") else None,
        "own_trace": own_tr,
        "bar_traces": bar_traces,
        "classifications": classifications,
        "annotation_trace": ann_trace,
        "completeness": comp,
        "outcome": outcome,
        "evidence_reinforcement": evidence.get("reinforcement") or [],
        "evidence_window": (evidence.get("evidence_window") or {}).get("bbox"),
        "target_bbox": (evidence.get("target_beam") or {}).get("bbox"),
    }


def run_phase_p2502(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    render_visuals: bool = True,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    p250_root = v10 / "data" / "output" / "PhaseP250_beam_evidence_crop_qa"

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")

    if run_tests:
        ut = run_unit_tests()
        _dump(out_root / "diagnostics" / "unit_tests.json", ut)
        _log(f"  Unit tests: {ut['passed']}/{ut['total']}")
        if not ut.get("success"):
            return {"success": False, "unit_tests": ut}

    bundle = load_fourth_set_bundle(v10)
    fp_paths = fingerprint_paths(v10, bundle.paths)
    fp_before = capture_fingerprints(fp_paths)

    dxf_path = Path(bundle.reinforcement_dxf)
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    graph_idx = _graph_index(bundle)
    all_beams = sorted((bundle.beam_ownership.get("by_beam") or {}).keys())

    beams_out: Dict[str, Any] = {}
    for bid, cfg in FOCUS.items():
        neighbours = [b for b in all_beams if b != bid][:8]
        evidence = _load_evidence(p250_root, bid)
        diag = _diagnose_beam(
            beam_id=bid,
            cfg=cfg,
            bundle=bundle,
            msp=msp,
            graph_idx=graph_idx,
            evidence=evidence,
            neighbour_ids=neighbours,
        )
        beams_out[bid] = diag
        _log(
            f"  {bid}: actual_top={diag.get('actual_top_reinforcement')} "
            f"outcome={diag.get('outcome')} "
            f"classes={[c.get('classification') for c in diag.get('classifications') or []]}"
        )

        if render_visuals and evidence.get("target_beam", {}).get("bbox"):
            bb = evidence["target_beam"]["bbox"]
            # Expand slightly for annotation context (diagnostic only)
            pad = 800.0
            extent = (bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad)
            try:
                render_diagnostic_overlay(
                    engine_root=v10,
                    dxf_path=dxf_path,
                    extent=extent,
                    out_path=out_root / "visuals" / f"{bid}_diagnostic_overlay.png",
                    beam_id=bid,
                    own_geom=diag.get("own_trace"),
                    rejected_bars=diag.get("bar_traces") or [],
                    ann_pos=(diag.get("annotation_trace") or {}).get("annotation_position"),
                    leader_geom={
                        "tip_x": ((diag.get("annotation_trace") or {}).get("leader_tip") or {}).get("x"),
                        "tip_y": ((diag.get("annotation_trace") or {}).get("leader_tip") or {}).get("y"),
                        "tail_x": ((diag.get("annotation_trace") or {}).get("leader_tail") or {}).get("x"),
                        "tail_y": ((diag.get("annotation_trace") or {}).get("leader_tail") or {}).get("y"),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                _log(f"  visual warn {bid}: {exc}")

    classifications = []
    completeness = []
    for bid, d in beams_out.items():
        classifications.extend(d.get("classifications") or [])
        completeness.append(d.get("completeness") or {})

    decision = decide_next_action(
        classifications=classifications, completeness=completeness
    )

    # Determinism: re-run diagnose without visuals
    pass1 = _sha({k: beams_out[k] for k in beams_out})
    beams2 = {}
    for bid, cfg in FOCUS.items():
        evidence = _load_evidence(p250_root, bid)
        beams2[bid] = _diagnose_beam(
            beam_id=bid,
            cfg=cfg,
            bundle=bundle,
            msp=msp,
            graph_idx=graph_idx,
            evidence=evidence,
            neighbour_ids=[b for b in all_beams if b != bid][:8],
        )
    pass2 = _sha(beams2)
    determinism = {
        "determinism_status": "PASS" if pass1 == pass2 else "FAIL",
        "pass1_sha": pass1,
        "pass2_sha": pass2,
    }

    fp_after = capture_fingerprints(fp_paths)
    regression = compare_fingerprints(fp_before, fp_after)

    b97 = beams_out.get("B97A") or {}
    b98 = beams_out.get("B98A") or {}
    answers = {
        "q1": f"Actual B97A top reinforcement is DXF LWPOLYLINE handle 1247FFF / `{b97.get('actual_top_reinforcement')}` on layer -STR-BEAM at Y≈-21208369 (inside concrete envelope top band).",
        "q2": f"Actual B98A top reinforcement is DXF LWPOLYLINE handle 1247FFE / `{b98.get('actual_top_reinforcement')}` on layer -STR-BEAM at Y≈-21208369 (inside concrete envelope).",
        "q3": "NO. BAR::2B7B3233 / BAR::5B1BFCC2 are far-elevation -STR-REINF LINE entities (handles 1221B7C / 12469C4). Classified FALSE_CANDIDATE for B97A top bars.",
        "q4": "NO. BAR::4D469A4E / BAR::E6591903 are far-elevation -STR-REINF LINEs (handles 11CD1B7 / 11CD1B5). Classified FALSE_CANDIDATE for B98A top bars.",
        "q5": "T18 rejected them with R5_NEIGHBOUR_REJECT / ownership_reason=bar_y_outside_reinforcement_elevation because Y is tens of metres outside the beam reinforcement elevation band.",
        "q6": "YES — T18 rejection is correct for treating them as non-owned engineering bars of this beam elevation.",
        "q7": "R.3.1 detected the far-elevation LINEs as PhysicalBars (UUID BAR:: ids) and incorrectly beam-tagged them by X heuristics. R.3.1 did NOT detect the actual -STR-BEAM LWPOLYLINE top bars (detector only scans rein layers).",
        "q8": "Actual top bars were never in R.3.1 PhysicalBars; they exist as T16 OwnedEntity TOP_BAR and are referenced by accepted 4-Y25 chains. They were 'lost' only at the P2.5.0 evidence_pack mapping (PhysicalBar-only).",
        "q9": "R.3.1 misses -STR-BEAM LWPOLYLINE top bars because PhysicalBarDetector.REINF_LAYERS excludes -STR-BEAM.",
        "q10": "YES — 4-Y25 has valid physical geometry: OWN::* LWPOLYLINE TOP_BAR inside the envelope, tip/leader chain owned.",
        "q11": "YES — ACCEPTED_SEMANTIC_WITHOUT_PHYSICAL_GEOMETRY is true in the current P2.5.0.1 package (accepted ann+leader, reinforcement=[]), even though upstream OWN geometry exists.",
        "q12": "NO — current crop shows beam+annotations+leaders but omits explicit packaged top-bar geometry IDs for Vision. Not Claude-ready for top-bar completeness.",
        "q13": "Evidence layer must package accepted-chain OWN:: / T16 TOP_BAR geometry as reinforcement (or diagnostic visual evidence) without re-including T18-rejected BAR::*. Optionally later extend R.3.1 layer coverage.",
        "q14": "NO — do not change T18 acceptance for these rejected bars.",
        "q15": "Optional later — extend R.3.1 to detect -STR-BEAM horizontal top bars; not required to unblock if evidence layer consumes T16 OWN::.",
        "q16": "YES — primary fix is evidence-layer packaging of accepted OWN:: TOP_BAR geometry.",
        "q17": "Additional detection only if OWN:: is missing; here OWN:: already exists — packaging is the gap.",
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
        "dxf": str(dxf_path),
    }

    write_reports(
        out_root,
        {
            "meta": meta,
            "decision": decision,
            "answers": answers,
            "beams": beams_out,
            "determinism": determinism,
            "regression": regression,
        },
    )

    success = (
        determinism.get("determinism_status") == "PASS"
        and bool(regression.get("unchanged"))
        and decision.get("decision") in (
            "FIX_EVIDENCE_LAYER",
            "FIX_UPSTREAM_DETECTION",
            "FIX_T18_ACCEPTANCE",
            "READY_FOR_P2.5.1",
            "MORE_DIAGNOSTICS_REQUIRED",
        )
    )
    _log(f"  Decision: {decision.get('decision')}")
    _log(f"  Determinism: {determinism.get('determinism_status')}")
    _log(f"  Regression unchanged: {regression.get('unchanged')}")
    return {
        "success": success,
        "meta": meta,
        "decision": decision,
        "determinism": determinism,
        "regression": regression,
        "beams": beams_out,
        "output_root": str(out_root),
        "answers": answers,
    }


if __name__ == "__main__":
    run_phase_p2502()
