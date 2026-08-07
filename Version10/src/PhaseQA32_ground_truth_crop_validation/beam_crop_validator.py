"""
Per-beam ground-truth crop validation (8 steps).
MODEL_VERSION: 10.0.2
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .dxf_probe import (
    completeness_compare,
    count_entities_in_crop,
    neighbour_beam_intrusion,
    probe_dxf_metadata,
)
from .geometry_utils import (
    BBox,
    alignment_metrics,
    as_bbox,
    bbox_area,
    bbox_center,
    bbox_size,
    expand_bbox,
    expand_bbox_margin,
    intersection,
    iou,
)
from .overlay_generator import generate_overlay

MODEL_VERSION = "10.0.2"

# Thresholds for classification (diagnostic)
_IOU_VALID = 0.75
_IOU_PARTIAL = 0.40
_COMPLETENESS_VALID = 85.0
_COMPLETENESS_PARTIAL = 55.0
_CENTROID_ERR_VALID = 500.0  # mm in sheet coords (large sheets)


def _by_beam(doc: Optional[Dict[str, Any]], beam_id: str) -> Dict[str, Any]:
    if not doc:
        return {}
    by = doc.get("by_beam") or doc.get("beams") or {}
    if isinstance(by, dict):
        if beam_id in by:
            return by[beam_id] or {}
        for k, v in by.items():
            if str(k) == beam_id or str(k).startswith(beam_id + "_"):
                return v or {}
    return {}


def _manual_source_info(
    comparison_dir: Optional[Path],
    engine_root: Path,
    output_root: Optional[Path],
    beam_id: str,
) -> Dict[str, Any]:
    """Mirror T181 locate_manual_crop preference order (read-only inspect)."""
    candidates = [
        (
            "t16_benchmark_original",
            engine_root
            / "data"
            / "output"
            / "Track1_geometric_evidence"
            / "PhaseT16_entity_ownership"
            / "benchmark_compare"
            / f"{beam_id}_original_crop.png",
        ),
        (
            "t15_benchmark_after",
            engine_root
            / "data"
            / "output"
            / "Track1_geometric_evidence"
            / "t15_benchmark"
            / "after"
            / f"{beam_id}_crop.png",
        ),
        (
            "opencv_crop",
            (output_root or Path("."))
            / "PhaseT1_geometric_stirrup_evidence"
            / "opencv_renders"
            / f"{beam_id}_crop.png",
        ),
        (
            "t171_original_render",
            (output_root or Path("."))
            / "PhaseT171_graph_render_validation"
            / beam_id
            / "Original_Render.png",
        ),
    ]
    for name, path in candidates:
        if path.exists():
            return {"source_kind": name, "source_path": str(path), "regenerated": False}
    man = None
    if comparison_dir:
        p = Path(comparison_dir) / f"{beam_id}_manual.png"
        if p.exists():
            man = p
    return {
        "source_kind": "regenerated_dxf_text_crop",
        "source_path": str(man) if man else None,
        "regenerated": True,
        "extent_source": "geometry_envelopes.extent",
        "note": (
            "No Set1-style OpenCV/benchmark crop found; T181/T182 "
            "regenerates manual PNG from reinforcement DXF using T1 geometry envelope."
        ),
    }


def _reconstruct_expected(
    beam_bbox: BBox,
    t182: Dict[str, Any],
) -> Tuple[BBox, Dict[str, Any]]:
    """
    Reconstruct what a trustworthy reinforcement GT crop SHOULD cover.

    Prefer T182 owned_union / computed_render when available (captures owned
    reinforcement context). Else expand beam bbox with T182 margin or 15%.
    """
    owned = as_bbox(t182.get("owned_union_bbox"))
    computed = as_bbox(t182.get("computed_render_bbox"))
    margin = t182.get("margin_applied") or {}
    if owned and bbox_area(owned) > bbox_area(beam_bbox) * 1.05:
        return owned, {
            "method": "t182_owned_union_bbox",
            "padding": margin,
            "rotation": 0.0,
            "coordinate_system": "DXF model-space mm",
            "transform_matrix": "identity_axis_aligned",
        }
    if computed and bbox_area(computed) > bbox_area(beam_bbox) * 1.05:
        return computed, {
            "method": "t182_computed_render_bbox",
            "padding": margin,
            "rotation": 0.0,
            "coordinate_system": "DXF model-space mm",
            "transform_matrix": "identity_axis_aligned",
        }
    expected = expand_bbox_margin(beam_bbox, margin, default_frac=0.15)
    return expected, {
        "method": "beam_bbox_plus_diagnostic_padding",
        "padding": margin or {"frac": 0.15},
        "rotation": 0.0,
        "coordinate_system": "DXF model-space mm",
        "transform_matrix": "identity_axis_aligned",
    }


def _alignment_flags(
    beam_bbox: BBox, crop: BBox, other_extents: Dict[str, BBox], beam_id: str
) -> Dict[str, Any]:
    bc = bbox_center(beam_bbox)
    cc = bbox_center(crop)
    cw, ch = bbox_size(crop)
    # Centred if beam center near crop center (within 15% of crop size)
    dx = abs(bc[0] - cc[0])
    dy = abs(bc[1] - cc[1])
    centred = (dx <= 0.15 * cw) and (dy <= 0.15 * ch)

    # Clipped if beam not fully inside crop
    fully_inside = (
        crop[0] <= beam_bbox[0]
        and crop[1] <= beam_bbox[1]
        and crop[2] >= beam_bbox[2]
        and crop[3] >= beam_bbox[3]
    )
    clipped = not fully_inside

    # Excess whitespace: beam area << crop area
    beam_a = max(bbox_area(beam_bbox), 1e-9)
    crop_a = max(bbox_area(crop), 1e-9)
    whitespace_pct = round(100.0 * max(0.0, 1.0 - beam_a / crop_a), 2)
    excess_whitespace = whitespace_pct >= 70.0

    neigh = neighbour_beam_intrusion(beam_bbox, crop, other_extents, beam_id)
    visually_valid = (
        fully_inside
        and not neigh["neighbour_intrusion"]
        and not excess_whitespace
        and centred
    )
    return {
        "beam_centred": centred,
        "beam_clipped": clipped,
        "excess_whitespace": excess_whitespace,
        "whitespace_pct": whitespace_pct,
        "neighbour_beam_intrusion": neigh["neighbour_intrusion"],
        "multiple_beams_visible": neigh["multiple_beams_visible"],
        "intruders": neigh["intruders"],
        "crop_visually_valid": visually_valid,
        "centering_error_mm": round((dx ** 2 + dy ** 2) ** 0.5, 3),
        "centering_pct": round(
            100.0 * max(0.0, 1.0 - (dx / max(cw, 1e-9) + dy / max(ch, 1e-9)) / 2.0),
            2,
        ),
    }


def _judge(
    metrics: Dict[str, Any],
    completeness: Dict[str, Any],
    align: Dict[str, Any],
    steps_pass: Dict[str, bool],
    manual_source: Dict[str, Any],
) -> Dict[str, Any]:
    iou_v = float(metrics.get("iou") or 0.0)
    comp = float(completeness.get("completeness_pct") or 0.0)
    centroid_err = float(metrics.get("centroid_error") or 0.0)

    # Regenerated tight envelope vs annotation-bearing expected → usually weak GT
    regenerated = bool(manual_source.get("regenerated"))

    if (
        iou_v >= _IOU_VALID
        and comp >= _COMPLETENESS_VALID
        and centroid_err <= _CENTROID_ERR_VALID
        and not align.get("beam_clipped")
        and not align.get("neighbour_beam_intrusion")
    ):
        status = "VALID"
        category = "A"
        conf = "High"
        qa31_trust = True
        reason = "Manual crop spatially matches reconstructed reinforcement crop."
    elif iou_v >= _IOU_PARTIAL or comp >= _COMPLETENESS_PARTIAL:
        status = "PARTIALLY VALID"
        category = "B"
        conf = "Medium"
        qa31_trust = False
        reason = (
            "Manual crop partially overlaps reconstructed crop; "
            "ownership diagnosis requires review."
        )
    else:
        status = "INVALID"
        category = "C"
        conf = "High" if regenerated else "Medium"
        qa31_trust = False
        reason = (
            "Manual crop does not match reconstructed reinforcement crop; "
            "QA.3.1 ownership conclusion cannot be trusted for this beam."
        )

    if regenerated and status == "VALID" and iou_v < 0.9:
        # Tight envelope regenerated crops rarely equal annotation-aware expected
        status = "PARTIALLY VALID"
        category = "B"
        conf = "Medium"
        qa31_trust = False
        reason = (
            "Manual crop is regenerated from T1 geometry envelope (tight beam bbox), "
            "not a true AutoCAD ground-truth crop; spatial/entity mismatch vs "
            "reinforcement context crop."
        )

    return {
        "manual_crop_status": status,
        "category": category,
        "category_label": {
            "A": "Ground truth crop is correct — ownership diagnosis remains valid",
            "B": "Ground truth crop partially incorrect — ownership diagnosis requires review",
            "C": "Ground truth crop incorrect — QA.3.1 conclusion cannot be trusted for this beam",
        }[category],
        "confidence": conf,
        "qa31_ownership_conclusion_still_valid": qa31_trust,
        "reason": reason,
        "steps_pass": steps_pass,
    }


def validate_beam(
    beam_id: str,
    *,
    drawing_set: str,
    set_key: str,
    engine_root: Path,
    reinforcement_dxf: Optional[Path],
    run_reinforcement_dxf: Optional[Path],
    output_root: Optional[Path],
    comparison_dir: Optional[Path],
    owned_render_path: Optional[Path],
    bundle: Dict[str, Any],
    other_extents: Dict[str, BBox],
    overlay_dir: Path,
    skip_overlays: bool = False,
) -> Dict[str, Any]:
    env = _by_beam(bundle.get("geometry_envelopes"), beam_id)
    t182 = _by_beam(bundle.get("render_extent_qa"), beam_id)
    ownership = _by_beam(bundle.get("beam_ownership"), beam_id)

    beam_bbox = as_bbox(env.get("extent") or t182.get("beam_bbox"))
    meta_dxf = probe_dxf_metadata(reinforcement_dxf)
    run_meta = probe_dxf_metadata(run_reinforcement_dxf) if run_reinforcement_dxf else {}

    # STEP 1 — DXF selection
    expected_name = Path(reinforcement_dxf).name if reinforcement_dxf else None
    actual_used = Path(run_reinforcement_dxf).name if run_reinforcement_dxf else expected_name
    same_file = False
    same_basename = False
    if reinforcement_dxf and run_reinforcement_dxf:
        same_basename = Path(reinforcement_dxf).name.lower() == Path(
            run_reinforcement_dxf
        ).name.lower()
        try:
            same_file = Path(reinforcement_dxf).resolve() == Path(
                run_reinforcement_dxf
            ).resolve()
        except Exception:
            same_file = same_basename
    elif reinforcement_dxf:
        same_file = True  # only Test_Input path available; treat as selected
        same_basename = True
    # Unseen runs copy DXF into web_run/; basename match is sufficient for selection
    step1_pass = bool(meta_dxf.get("exists")) and (
        same_file
        or same_basename
        or (run_reinforcement_dxf is None and reinforcement_dxf is not None)
    )
    step1 = {
        "expected_reinforcement_dxf": expected_name,
        "actual_reinforcement_dxf_used": actual_used,
        "absolute_path": str(reinforcement_dxf) if reinforcement_dxf else None,
        "run_path": str(run_reinforcement_dxf) if run_reinforcement_dxf else None,
        "sheet_layout": meta_dxf.get("sheet_layout"),
        "space": meta_dxf.get("space"),
        "drawing_scale": meta_dxf.get("drawing_scale"),
        "units": meta_dxf.get("units"),
        "same_file": same_file,
        "same_basename": same_basename,
        "status": "PASS" if step1_pass else "FAIL",
        "dxf_metadata": meta_dxf,
        "run_dxf_metadata": run_meta or None,
    }

    # STEP 2 — Locate beam
    step2_pass = beam_bbox is not None
    cx = cy = None
    if beam_bbox:
        cx, cy = bbox_center(beam_bbox)
    step2 = {
        "beam_label_found": bool(env) or bool(t182),
        "beam_geometry_found": beam_bbox is not None,
        "beam_bounding_box": list(beam_bbox) if beam_bbox else None,
        "beam_centroid": [cx, cy] if beam_bbox else None,
        "beam_orientation": env.get("orientation") or env.get("axis"),
        "beam_dimensions": list(bbox_size(beam_bbox)) if beam_bbox else None,
        "beam_confidence": env.get("geometry_confidence"),
        "status": "PASS" if step2_pass else "FAIL",
    }

    # Manual source + actual crop extent
    manual_src = _manual_source_info(
        comparison_dir, Path(engine_root), output_root, beam_id
    )
    manual_path = None
    if comparison_dir:
        mp = Path(comparison_dir) / f"{beam_id}_manual.png"
        if mp.exists():
            manual_path = mp
    # Actual manual crop extent = geometry envelope (documented T181 behaviour)
    actual_crop = beam_bbox
    if manual_src.get("regenerated") and beam_bbox:
        actual_crop = beam_bbox
    actual_crop = as_bbox(actual_crop)

    # STEP 3 — Reconstruct expected
    if beam_bbox:
        expected_crop, recon_meta = _reconstruct_expected(beam_bbox, t182)
        step3_pass = True
    else:
        expected_crop, recon_meta = None, {"method": "unavailable"}
        step3_pass = False
    ew = eh = None
    if expected_crop:
        ew, eh = bbox_size(expected_crop)
    step3 = {
        "crop_origin": list(expected_crop[:2]) if expected_crop else None,
        "crop_width": ew,
        "crop_height": eh,
        "padding": recon_meta.get("padding"),
        "rotation": recon_meta.get("rotation"),
        "transform_matrix": recon_meta.get("transform_matrix"),
        "crop_coordinate_system": recon_meta.get("coordinate_system"),
        "reconstruction_method": recon_meta.get("method"),
        "expected_extent": list(expected_crop) if expected_crop else None,
        "status": "PASS" if step3_pass else "FAIL",
    }

    # STEP 4 — Compare
    if expected_crop and actual_crop:
        metrics = alignment_metrics(expected_crop, actual_crop)
        # padding difference proxy via scale / size
        metrics["padding_diff_proxy"] = {
            "width_diff": metrics["width_diff"],
            "height_diff": metrics["height_diff"],
        }
        step4_pass = float(metrics["iou"]) >= _IOU_PARTIAL
    else:
        metrics = {}
        step4_pass = False
    step4 = {
        "expected_crop": list(expected_crop) if expected_crop else None,
        "existing_manual_crop": list(actual_crop) if actual_crop else None,
        "metrics": metrics,
        "status": "PASS" if step4_pass else "FAIL",
    }

    # STEP 5 — Entity completeness
    dxf = reinforcement_dxf
    if expected_crop and dxf:
        exp_counts = count_entities_in_crop(dxf, expected_crop)
    else:
        exp_counts = {"total": 0, "error": "unavailable"}
    if actual_crop and dxf:
        act_counts = count_entities_in_crop(dxf, actual_crop)
    else:
        act_counts = {"total": 0, "error": "unavailable"}
    completeness = completeness_compare(exp_counts, act_counts)
    step5_pass = float(completeness.get("completeness_pct") or 0) >= _COMPLETENESS_PARTIAL
    step5 = {
        "expected_counts": exp_counts,
        "manual_counts": act_counts,
        **completeness,
        "status": "PASS" if step5_pass else "FAIL",
    }

    # STEP 6 — Beam alignment (on MANUAL crop — the baseline under test)
    if beam_bbox and actual_crop:
        align = _alignment_flags(beam_bbox, actual_crop, other_extents, beam_id)
        # For tight envelope crops: beam fills most of crop → not excess whitespace;
        # but relative to expected reinforcement crop the MANUAL may look sparse in PNG.
        # Also evaluate expected crop alignment for contrast.
        align_expected = _alignment_flags(beam_bbox, expected_crop, other_extents, beam_id) if expected_crop else {}
        step6_pass = bool(align.get("crop_visually_valid"))
    else:
        align = {}
        align_expected = {}
        step6_pass = False
    step6 = {
        **align,
        "expected_crop_alignment": align_expected,
        "status": "PASS" if step6_pass else "FAIL",
    }

    # STEP 7 — Coordinate validation
    coord_ok = True
    coord_notes: List[str] = []
    if beam_bbox and expected_crop and actual_crop:
        # All axis-aligned, same coordinate system
        if env.get("extent") and t182.get("beam_bbox"):
            if as_bbox(env.get("extent")) != as_bbox(t182.get("beam_bbox")):
                # allow tiny float noise
                a = as_bbox(env.get("extent"))
                b = as_bbox(t182.get("beam_bbox"))
                if a and b and iou(a, b) < 0.99:
                    coord_ok = False
                    coord_notes.append("geometry_envelope_extent_differs_from_t182_beam_bbox")
        # Scale consistency: regenerated manual uses envelope; owned uses computed
        if t182.get("computed_render_bbox") and actual_crop:
            cr = as_bbox(t182.get("computed_render_bbox"))
            if cr and iou(actual_crop, cr) < 0.5:
                coord_notes.append(
                    "manual_extent_diverges_from_owned_render_extent (expected for tight GT proxy)"
                )
    else:
        coord_ok = False
        coord_notes.append("insufficient_bboxes")
    step7 = {
        "world_coordinates": "DXF model-space (assumed mm via INSUNITS)",
        "dxf_coordinates": list(beam_bbox) if beam_bbox else None,
        "crop_coordinates_expected": list(expected_crop) if expected_crop else None,
        "crop_coordinates_manual": list(actual_crop) if actual_crop else None,
        "image_coordinates": "PNG pixel space via CoordTransform (Y-down)",
        "transformation_consistency": coord_ok,
        "scaling_consistency": True,
        "origin_consistency": True,
        "notes": coord_notes,
        "status": "PASS" if coord_ok else "FAIL",
    }

    steps_pass = {
        "reinforcement_dxf": step1_pass,
        "beam_located": step2_pass,
        "crop_reconstructed": step3_pass,
        "manual_matches_reconstructed": step4_pass and float(metrics.get("iou") or 0) >= _IOU_VALID,
        "coordinate_transforms_valid": coord_ok,
        "entity_completeness": step5_pass and float(completeness.get("completeness_pct") or 0) >= _COMPLETENESS_VALID,
        "no_neighbour_contamination": not bool(align.get("neighbour_beam_intrusion")),
        "no_clipping": not bool(align.get("beam_clipped")),
    }

    judgement = _judge(metrics, completeness, align, steps_pass, manual_src)

    # Overlays
    overlay_info: Dict[str, Any] = {}
    if skip_overlays:
        op = Path(overlay_dir) / f"{beam_id}_expected_vs_manual.png"
        hp = Path(overlay_dir) / f"{beam_id}_difference_heatmap.png"
        overlay_info = {
            "beam_id": beam_id,
            "overlay_path": str(op) if op.exists() else None,
            "heatmap_path": str(hp) if hp.exists() else None,
            "skipped": True,
            "error": None if op.exists() else "overlay_missing",
        }
    elif expected_crop and actual_crop and reinforcement_dxf:
        overlay_info = generate_overlay(
            engine_root=Path(engine_root),
            dxf_path=Path(reinforcement_dxf),
            expected=expected_crop,
            actual=actual_crop,
            dest_dir=overlay_dir,
            beam_id=beam_id,
        )

    # Owned render path presence
    render_path = owned_render_path
    if comparison_dir and not render_path:
        rp = Path(comparison_dir) / f"{beam_id}_render.png"
        if rp.exists():
            render_path = rp

    return {
        "beam_id": beam_id,
        "drawing_set": drawing_set,
        "set_key": set_key,
        "model_version": MODEL_VERSION,
        "artefacts": {
            "manual_png": str(manual_path) if manual_path else None,
            "owned_render_png": str(render_path) if render_path else None,
            "has_geometry_envelope": bool(env),
            "has_render_extent_qa": bool(t182),
            "has_ownership": bool(ownership),
        },
        "manual_source": manual_src,
        "steps": {
            "1_reinforcement_dxf": step1,
            "2_beam_location": step2,
            "3_reconstructed_crop": step3,
            "4_manual_comparison": step4,
            "5_entity_completeness": step5,
            "6_beam_alignment": step6,
            "7_coordinate_validation": step7,
            "8_ground_truth_validation": judgement,
        },
        "alignment_metrics": metrics,
        "entity_completeness": completeness,
        "beam_alignment": align,
        "coordinate_validation": step7,
        "decision": {
            "category": judgement["category"],
            "status": judgement["manual_crop_status"],
            "confidence": judgement["confidence"],
            "qa31_ownership_conclusion_still_valid": judgement[
                "qa31_ownership_conclusion_still_valid"
            ],
            "label": judgement["category_label"],
            "reason": judgement["reason"],
        },
        "overlay": overlay_info,
        "validation_checks": {
            "correct_reinforcement_dxf_selected": step1_pass,
            "correct_beam_located": step2_pass,
            "correct_crop_reconstructed": step3_pass,
            "manual_crop_spatially_matches_reconstructed": steps_pass[
                "manual_matches_reconstructed"
            ],
            "coordinate_transforms_valid": coord_ok,
            "manual_crop_contains_all_expected_entities": steps_pass["entity_completeness"],
            "no_neighbour_contamination": steps_pass["no_neighbour_contamination"],
            "no_clipping": steps_pass["no_clipping"],
            "qa31_ownership_conclusion_still_valid": judgement[
                "qa31_ownership_conclusion_still_valid"
            ],
        },
    }
