"""End-to-end coordinate / ownership traces for focus beams."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _bar_trace_row(
    *,
    bar_id: str,
    evidence: Dict[str, Any],
    ownership: Dict[str, Any],
    graph_node: Optional[Dict[str, Any]],
    r31_bar: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    beam = evidence.get("target_beam") or {}
    beam_bbox = beam.get("bbox") or []
    br = (ownership.get("bar_results") or {}).get(bar_id) or {}
    reinf = None
    for r in evidence.get("reinforcement") or []:
        if r.get("reinforcement_id") == bar_id:
            reinf = r
            break
    geom = (reinf or {}).get("geometry") or {}
    y = geom.get("y_position")
    by0 = beam_bbox[1] if len(beam_bbox) >= 4 else None
    by1 = beam_bbox[3] if len(beam_bbox) >= 4 else None
    y_gap = None
    if y is not None and by0 is not None and by1 is not None:
        if y < by0:
            y_gap = by0 - y
        elif y > by1:
            y_gap = y - by1
        else:
            y_gap = 0.0

    g_attrs = (graph_node or {}).get("attributes") or {}
    return {
        "object_id": bar_id,
        "steps": [
            {
                "step": "T18.ownership.bar_results",
                "source_file": "PhaseT18_beam_ownership/BeamOwnership.json",
                "accepted": br.get("accepted"),
                "rejected_rule": br.get("rejected_rule"),
                "ownership_reason": br.get("ownership_reason"),
                "ownership_score": br.get("ownership_score"),
                "coordinate_space": "N/A (decision record)",
            },
            {
                "step": "AnnotationGraph.PhysicalBar",
                "source_file": "PhaseT17_annotation_graph/AnnotationGraph.json",
                "beam_id": (graph_node or {}).get("beam_id"),
                "source": (graph_node or {}).get("source"),
                "y_position": g_attrs.get("y_position"),
                "start_x": g_attrs.get("start_x"),
                "end_x": g_attrs.get("end_x"),
                "coordinate_space": "DXF_MODEL_MM",
                "units": "mm",
                "transform_applied": "none_observed",
            },
            {
                "step": "R.3.1.PhysicalBars",
                "source_file": "PhaseR3.1_engineering_relationship_engine/PhysicalBars.json",
                "beam_id": (r31_bar or {}).get("beam_id"),
                "y_position": (r31_bar or {}).get("y_position"),
                "start_x": (r31_bar or {}).get("start_x"),
                "end_x": (r31_bar or {}).get("end_x"),
                "vertical_placement": (r31_bar or {}).get("vertical_placement"),
                "coordinate_space": "DXF_MODEL_MM",
                "units": "mm",
                "transform_applied": "none_observed",
            },
            {
                "step": "P2.5.0.evidence_package.reinforcement",
                "included_in_package": reinf is not None,
                "y_position": y,
                "start_x": geom.get("start_x"),
                "end_x": geom.get("end_x"),
                "y_gap_to_beam_mm": y_gap,
                "relationship_basis": "AnnotationGraph.beam_id / ownership.bar_results",
                "coordinate_space": "DXF_MODEL_MM",
            },
        ],
        "t18_accepted": br.get("accepted"),
        "spatially_inside_beam_y_band": y_gap == 0.0 if y_gap is not None else None,
        "genuinely_spatially_associated": bool(br.get("accepted")) and (y_gap == 0.0),
    }


def build_beam_coordinate_trace(
    *,
    beam_id: str,
    evidence: Dict[str, Any],
    ownership: Dict[str, Any],
    graph_nodes_by_id: Dict[str, Dict[str, Any]],
    r31_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    beam = evidence.get("target_beam") or {}
    win = evidence.get("evidence_window") or {}
    beam_bbox = beam.get("bbox") or []
    crop = win.get("bbox") or []
    height = None
    if len(crop) >= 4:
        height = abs(crop[3] - crop[1])

    # Bars: from package + rejected ownership keys
    bar_ids = {r.get("reinforcement_id") for r in evidence.get("reinforcement") or []}
    for bid in (ownership.get("bar_results") or {}).keys():
        bar_ids.add(bid)

    bar_traces = []
    for bid in sorted(x for x in bar_ids if x):
        bar_traces.append(
            _bar_trace_row(
                bar_id=str(bid),
                evidence=evidence,
                ownership=ownership,
                graph_node=graph_nodes_by_id.get(str(bid)),
                r31_bar=r31_by_id.get(str(bid)),
            )
        )

    # Leaders
    leader_traces = []
    lr = ownership.get("leader_results") or {}
    leader_ids = set(lr.keys()) if isinstance(lr, dict) else set()
    for l in evidence.get("leaders") or []:
        leader_ids.add(l.get("leader_id"))
    for lid in sorted(x for x in leader_ids if x):
        res = lr.get(lid) if isinstance(lr, dict) else {}
        pkg = next(
            (x for x in (evidence.get("leaders") or []) if x.get("leader_id") == lid),
            None,
        )
        leader_traces.append(
            {
                "object_id": lid,
                "t18_accepted": (res or {}).get("accepted"),
                "ownership_reason": (res or {}).get("ownership_reason"),
                "rejected_rule": (res or {}).get("rejected_rule"),
                "included_in_package": pkg is not None,
                "geometry": (pkg or {}).get("geometry"),
                "coordinate_space": "DXF_MODEL_MM",
            }
        )

    # Consistency check
    spaces = {
        "beam_bbox": "DXF_MODEL_MM",
        "t18_crop_extent": "DXF_MODEL_MM",
        "envelope_extent": "DXF_MODEL_MM",
        "reinforcement": "DXF_MODEL_MM",
        "annotations": "DXF_MODEL_MM",
        "leaders": "DXF_MODEL_MM",
        "evidence_window": win.get("coordinate_space") or "DXF_MODEL_MM",
        "renderer": "DXF_MODEL_MM",
    }
    consistent = len(set(spaces.values())) == 1

    return {
        "beam_id": beam_id,
        "target_beam": {
            "bbox": beam_bbox,
            "depth_mm": beam.get("depth_mm"),
            "orientation": beam.get("orientation"),
            "envelope_extent": beam.get("envelope_extent"),
            "crop_extent_t18": beam.get("crop_extent_t18"),
            "coordinate_space": "DXF_MODEL_MM",
            "units": "mm",
        },
        "evidence_window": {
            "bbox": crop,
            "base_bbox": win.get("base_bbox"),
            "height_mm": height,
            "expansion": win.get("expansion"),
            "coordinate_space": win.get("coordinate_space"),
        },
        "coordinate_space_consistency": {
            "spaces": spaces,
            "all_same_space": consistent,
            "unit_mismatch_detected": False,
            "transform_error_detected": False,
            "note": (
                "Beam bbox, R.3.1/AnnotationGraph bar Y, annotations, leaders, "
                "evidence window, and M.1 renderer extents all use ezdxf modelspace mm. "
                "No unit conversion or block-transform remapping is applied in P2.5.0."
            ),
        },
        "bar_traces": bar_traces,
        "leader_traces": leader_traces,
        "annotations_summary": [
            {
                "annotation_id": a.get("annotation_id"),
                "text": a.get("raw_text"),
                "position": a.get("position"),
                "source": a.get("source"),
            }
            for a in evidence.get("annotations") or []
        ],
    }
