"""Unit tests for P2.5.2.1 crop readability refinement."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    CROP_LOCAL_REFINED,
    EXTREME_CROP_HEIGHT_MM,
    READABILITY_FAIL,
    READABILITY_PASS,
    READABILITY_PARTIAL,
    READABILITY_REVIEW_REQUIRED,
)
from .geometry import local_beam_snippet, union_bbox
from .readability import classify_readability, compute_occupancy_metrics
from .refine import select_best_crop

MODEL_VERSION = "10.6.6"


def _synthetic_evidence() -> Dict[str, Any]:
    # Broad original crop, small annotation near beam center
    beam = [0.0, 0.0, 4000.0, 800.0]
    ann = [1800.0, 900.0, 2600.0, 1100.0]
    leader = [2000.0, 700.0, 2200.0, 900.0]
    original = [-5000.0, -2000.0, 12000.0, 5000.0]  # too broad
    return {
        "target_beam": {"bbox": beam},
        "evidence_window": {"bbox": original, "base_bbox": beam},
        "annotations": [
            {
                "annotation_id": "ANN-TEST",
                "raw_text": r"4L-Y12@\X100C/C",
                "bbox": ann,
                "position": {"x": 2200.0, "y": 1000.0},
            }
        ],
        "leaders": [
            {
                "leader_id": "LDR::1",
                "bbox": leader,
                "geometry": {"tip_x": 2100, "tip_y": 750, "tail_x": 2150, "tail_y": 880},
            }
        ],
        "leader_chains": {
            "accepted": [
                {
                    "annotation_id": "ANN-TEST",
                    "leaders": ["LDR::1"],
                    "describes": [],
                    "accepted": True,
                }
            ]
        },
        "reinforcement": [],
        "owned_geometry": [],
    }


def test_local_beam_snippet_prefers_near_annotation() -> None:
    beam = (0.0, 0.0, 20000.0, 1000.0)
    snip = local_beam_snippet(
        beam, center_x=1000.0, center_y=500.0, half_span_x=1600.0, half_span_y=1200.0
    )
    assert snip[2] - snip[0] <= 3200.0 + 1e-6
    assert snip[0] >= beam[0] - 1e-6


def test_occupancy_detects_too_small_annotation() -> None:
    crop = (0.0, 0.0, 20000.0, 10000.0)
    beam = (100.0, 100.0, 4000.0, 900.0)
    ann = (500.0, 950.0, 700.0, 1050.0)
    m = compute_occupancy_metrics(
        crop_bbox=crop,
        target_beam_bbox=beam,
        annotation_bbox=ann,
        evidence_bbox=ann,
    )
    cls = classify_readability(m)
    assert cls["readability_status"] in (
        READABILITY_FAIL,
        READABILITY_PARTIAL,
        READABILITY_REVIEW_REQUIRED,
    )
    assert m["annotation_occupancy"] < 0.01


def test_tight_crop_improves_readability() -> None:
    ev = _synthetic_evidence()
    baseline = compute_occupancy_metrics(
        crop_bbox=tuple(ev["evidence_window"]["bbox"]),  # type: ignore[arg-type]
        target_beam_bbox=tuple(ev["target_beam"]["bbox"]),  # type: ignore[arg-type]
        annotation_bbox=tuple(ev["annotations"][0]["bbox"]),  # type: ignore[arg-type]
        evidence_bbox=tuple(ev["annotations"][0]["bbox"]),  # type: ignore[arg-type]
    )
    sel = select_best_crop(ev, annotation_id="ANN-TEST", crop_kind=CROP_LOCAL_REFINED)
    assert sel.get("success")
    refined = sel.get("selected") or {}
    rm = refined.get("metrics") or {}
    assert rm.get("annotation_occupancy", 0) > baseline.get("annotation_occupancy", 0)
    assert rm.get("crop_width_mm", 1e9) < baseline.get("crop_width_mm", 0)
    assert int(sel.get("refinement_iteration") or 0) > 1
    assert (sel.get("readability_status") in (
        READABILITY_PASS,
        READABILITY_PARTIAL,
    ))


def test_extreme_not_forced() -> None:
    crop = (0.0, 0.0, 1000.0, EXTREME_CROP_HEIGHT_MM + 100)
    m = compute_occupancy_metrics(
        crop_bbox=crop,
        target_beam_bbox=(100.0, 100.0, 800.0, 500.0),
        annotation_bbox=(200.0, 200.0, 400.0, 300.0),
        evidence_bbox=(200.0, 200.0, 400.0, 300.0),
    )
    cls = classify_readability(m)
    assert cls["readability_status"] == READABILITY_REVIEW_REQUIRED


def test_union_bbox_available() -> None:
    u = union_bbox([(0, 0, 1, 1), (2, 2, 3, 3)])
    assert u == (0, 0, 3, 3)


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("local_beam_snippet_prefers_near_annotation", test_local_beam_snippet_prefers_near_annotation),
        ("occupancy_detects_too_small_annotation", test_occupancy_detects_too_small_annotation),
        ("tight_crop_improves_readability", test_tight_crop_improves_readability),
        ("extreme_not_forced", test_extreme_not_forced),
        ("union_bbox_available", test_union_bbox_available),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    passed = sum(1 for r in results if r.get("pass"))
    return {
        "success": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
