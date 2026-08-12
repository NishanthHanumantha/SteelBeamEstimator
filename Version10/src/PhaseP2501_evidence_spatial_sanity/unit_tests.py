"""Focused unit tests for P2.5.0.1 spatial sanity."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseP250_beam_evidence_crop_qa.evidence_pack import (
    _bar_ids_from_ownership,
    _leader_ids_from_ownership,
)
from PhaseP250_beam_evidence_crop_qa.evidence_window import expand_window_to_evidence

from .crop_sanity import classify_crop_health
from .evidence_expansion_trace import trace_expansion
from .spatial_metrics import as_bbox, collect_beam_spatial_metrics, y_gap

MODEL_VERSION = "10.6.1"


def run_unit_tests() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        results.append({"name": name, "pass": bool(cond), "detail": detail})

    # Accepted-only bar filter (B97A reproduction of inclusion bug)
    own = {
        "bar_results": {
            "BAR::2B7B3233": {
                "accepted": False,
                "ownership_reason": "bar_y_outside_reinforcement_elevation",
            },
            "BAR::5B1BFCC2": {"accepted": False},
            "BAR::OK": {"accepted": True},
        },
        "accepted_chains": [],
        "leader_results": {
            "LDR::BAD": {"accepted": False},
            "LDR::GOOD": {"accepted": True},
        },
    }
    bars = _bar_ids_from_ownership(own)
    leads = _leader_ids_from_ownership(own)
    check("b97a_rejected_bars_excluded", "BAR::2B7B3233" not in bars and "BAR::OK" in bars)
    check("b98a_rejected_leaders_excluded", "LDR::BAD" not in leads and "LDR::GOOD" in leads)

    # Spatial metric
    beam = (0.0, 0.0, 100.0, 50.0)
    far = (10.0, 5000.0, 90.0, 5010.0)
    check("spatial_y_gap", abs(y_gap(beam, far) - 4950.0) < 1.0)

    evidence = {
        "beam_id": "B97A",
        "target_beam": {"bbox": [0, 0, 1000, 600]},
        "evidence_window": {
            "bbox": [0, 0, 1000, 47000],
            "base_bbox": [0, 0, 1000, 600],
            "expansion": {"expanded": True, "expansions": 1},
        },
        "annotations": [],
        "leaders": [],
        "reinforcement": [
            {
                "reinforcement_id": "BAR::5B1BFCC2",
                "bbox": [100, 46000, 900, 46100],
                "geometry": {"y_position": 46050},
            }
        ],
    }
    spat = collect_beam_spatial_metrics(evidence)
    check(
        "b97a_reproduction_extreme_height_ratio",
        (spat.get("ratios") or {}).get("crop_height_to_beam_height_ratio", 0) > 50,
    )
    check(
        "crop_health_extreme",
        classify_crop_health(spat) == "VISION_CROP_EXTREME",
    )

    # Expansion trace identifies dominant bar
    ex = trace_expansion(evidence)
    check(
        "expansion_trace_dominant",
        (ex.get("dominant_vertical_expander") or {}).get("id") == "BAR::5B1BFCC2",
    )

    # Coordinate-space consistency helper: same-space bbox ops
    base = (0.0, 0.0, 100.0, 100.0)
    win, diag = expand_window_to_evidence(base, [far], pad_mm=10)
    check("expansion_includes_far", win[3] >= 5010 and diag["expanded"])

    # B98A-like metric
    evidence98 = dict(evidence)
    evidence98["beam_id"] = "B98A"
    evidence98["evidence_window"] = {
        "bbox": [0, -1000, 1000, 75000],
        "base_bbox": [0, 0, 1000, 600],
        "expansion": {"expanded": True},
    }
    spat98 = collect_beam_spatial_metrics(evidence98)
    check(
        "b98a_reproduction_extreme",
        (spat98.get("ratios") or {}).get("crop_height_mm", 0) > 70000,
    )

    # Known-good-like
    good = {
        "beam_id": "B14",
        "target_beam": {"bbox": [0, 0, 3000, 2500]},
        "evidence_window": {
            "bbox": [-200, -200, 3200, 2700],
            "base_bbox": [0, 0, 3000, 2500],
            "expansion": {"expanded": True},
        },
        "annotations": [{"annotation_id": "A1", "bbox": [100, 100, 200, 200]}],
        "leaders": [],
        "reinforcement": [{"reinforcement_id": "R1", "bbox": [50, 50, 2800, 100]}],
    }
    sg = collect_beam_spatial_metrics(good)
    check("known_good_not_extreme", classify_crop_health(sg) == "VISION_CROP_HEALTHY")

    passed = sum(1 for r in results if r["pass"])
    return {
        "model_version": MODEL_VERSION,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "success": passed == len(results),
        "results": results,
    }
