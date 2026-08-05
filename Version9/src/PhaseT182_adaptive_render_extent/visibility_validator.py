"""
T1.8.2 — Visibility QA: every owned object must lie inside render_bbox.
MODEL_VERSION: 9.5.2
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .adaptive_bbox import BBox, contains, touches_border

MODEL_VERSION = "9.5.2"


def _norm_text(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").upper().replace("%%U", "")).strip()


def validate_visibility(extent_doc: Dict[str, Any]) -> Dict[str, Any]:
    if not extent_doc.get("success"):
        return {
            "beam": extent_doc.get("beam"),
            "model_version": MODEL_VERSION,
            "visual_validation": "FAIL",
            "error": extent_doc.get("error"),
            "annotation_clipped": True,
            "leader_clipped": True,
            "text_bbox_outside_image": True,
            "arrowhead_outside_image": True,
            "render_bbox_contains_all_owned_objects": False,
            "visibility_failures": [],
            "objects_touching_border": [],
        }

    rb = tuple(extent_doc["computed_render_bbox"])
    assert len(rb) == 4
    render_bb: BBox = (rb[0], rb[1], rb[2], rb[3])

    failures: List[Dict[str, Any]] = []
    touching: List[Dict[str, Any]] = []
    flags = {
        "annotation_clipped": False,
        "leader_clipped": False,
        "text_bbox_outside_image": False,
        "arrowhead_outside_image": False,
    }

    for obj in extent_doc.get("owned_objects") or []:
        bb = tuple(obj["bbox"])
        ob: BBox = (bb[0], bb[1], bb[2], bb[3])
        kind = obj.get("kind") or ""
        if not contains(render_bb, ob):
            fail = {
                "id": obj.get("id"),
                "kind": kind,
                "bbox": list(ob),
                "reason": "object_bbox_not_subset_of_render_bbox",
            }
            failures.append(fail)
            if "annotation" in kind or "text" in kind:
                flags["annotation_clipped"] = True
                if "text" in kind:
                    flags["text_bbox_outside_image"] = True
            if "leader" in kind and "arrow" not in kind:
                flags["leader_clipped"] = True
            if "arrow" in kind:
                flags["arrowhead_outside_image"] = True
        elif touches_border(render_bb, ob, tol=0.5):
            # After inflate, objects should not touch the outer edge
            touching.append(
                {
                    "id": obj.get("id"),
                    "kind": kind,
                    "bbox": list(ob),
                    "reason": "object_touches_render_border",
                }
            )
            # Touching border after margin is a soft engineering fail
            if "annotation" in kind or "text" in kind:
                flags["annotation_clipped"] = True
            if "leader" in kind and "arrow" not in kind:
                flags["leader_clipped"] = True
            if "arrow" in kind:
                flags["arrowhead_outside_image"] = True

    contains_all = len(failures) == 0 and len(touching) == 0
    # Strict: failures fail; touching-border also fails per prompt
    # ("If any owned object intersects image boundary: FAIL")
    status = "PASS" if contains_all and not any(flags.values()) else "FAIL"

    return {
        "beam": extent_doc.get("beam"),
        "model_version": MODEL_VERSION,
        "computed_render_bbox": list(render_bb),
        "beam_bbox": extent_doc.get("beam_bbox"),
        "owned_union_bbox": extent_doc.get("owned_union_bbox"),
        "margin_applied": extent_doc.get("margin_applied"),
        "largest_margin_used": extent_doc.get("largest_margin_used"),
        "annotation_clipped": flags["annotation_clipped"],
        "leader_clipped": flags["leader_clipped"],
        "text_bbox_outside_image": flags["text_bbox_outside_image"],
        "arrowhead_outside_image": flags["arrowhead_outside_image"],
        "render_bbox_contains_all_owned_objects": len(failures) == 0,
        "visibility_failures": failures,
        "objects_touching_border": touching,
        "visual_validation": status,
        "checks": {
            "annotation_clipped_false": not flags["annotation_clipped"],
            "leader_clipped_false": not flags["leader_clipped"],
            "text_bbox_outside_image_false": not flags["text_bbox_outside_image"],
            "arrowhead_outside_image_false": not flags["arrowhead_outside_image"],
            "render_bbox_contains_all_owned_objects": len(failures) == 0,
            "no_objects_touching_border": len(touching) == 0,
        },
    }


def validate_regression_vs_t181(
    beam_id: str,
    *,
    t182_render_counts: Dict[str, Any],
    t181_validation: Optional[Dict[str, Any]],
    t182_ann_texts: List[str],
) -> Dict[str, Any]:
    """Ownership / count regression: must match T1.8.1 rendered sets."""
    if not t181_validation:
        return {
            "beam": beam_id,
            "regression_ok": True,
            "note": "no_t181_baseline",
        }
    t181_texts = list(t181_validation.get("rendered_annotations") or [])
    t182_norm = [_norm_text(t) for t in t182_ann_texts]
    t181_norm = [_norm_text(t) for t in t181_texts]
    counts_ok = (
        int(t182_render_counts.get("annotations") or 0)
        == len(t181_texts)
        and int(t182_render_counts.get("leaders") or 0)
        == int(t181_validation.get("rendered_leaders") or 0)
        # bars may increase slightly if OwnedEntity redraw — allow >= T181 bars
        and int(t182_render_counts.get("bars") or 0)
        >= int(t181_validation.get("rendered_bars") or 0)
    )
    texts_ok = sorted(t182_norm) == sorted(t181_norm)
    neighbour = t181_validation.get("neighbour_leak_annotations") or []
    return {
        "beam": beam_id,
        "regression_ok": counts_ok and texts_ok and len(neighbour) == 0,
        "annotation_count_match": len(t182_norm) == len(t181_norm) and texts_ok,
        "leader_count_match": int(t182_render_counts.get("leaders") or 0)
        == int(t181_validation.get("rendered_leaders") or 0),
        "bar_count_non_regressing": int(t182_render_counts.get("bars") or 0)
        >= int(t181_validation.get("rendered_bars") or 0),
        "neighbour_leakage_zero": len(neighbour) == 0,
        "t181_annotations": t181_norm,
        "t182_annotations": t182_norm,
    }
