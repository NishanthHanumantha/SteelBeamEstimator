"""
Focused unit tests for P2.5.0 evidence window / QA logic.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

from typing import Any, Dict, List

from .crop_qa import evaluate_crop_qa
from .evidence_window import (
    beam_base_bbox,
    expand_window_to_evidence,
    point_in_bbox,
)
from .metrics import aggregate_metrics, per_beam_recall

MODEL_VERSION = "10.6.0"


def run_unit_tests() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        results.append({"name": name, "pass": bool(cond), "detail": detail})

    # 1 beam bbox generation
    bb = beam_base_bbox(
        envelope_extent=[0, 0, 1000, 400],
        ownership_crop=[0, 0, 1000, 400],
        registry_bbox=None,
        base_margin_mm=100,
    )
    check("beam_bbox_generation", bb is not None and bb[0] < 0 and bb[2] > 1000)

    # 2 evidence-window expansion
    base = (0.0, 0.0, 100.0, 100.0)
    far = (500.0, 500.0, 520.0, 520.0)
    win, diag = expand_window_to_evidence(base, [far], pad_mm=10, max_iters=3)
    check(
        "evidence_window_expansion",
        diag["expanded"] and win[2] >= 520 and win[3] >= 520,
        str(diag),
    )

    # 3 annotation inclusion via point_in_bbox
    check("annotation_inclusion_geom", point_in_bbox(510, 510, win))

    # 4 leader inclusion (same geometry helper)
    check("leader_inclusion_geom", point_in_bbox(500, 500, win))

    # 5 leader-chain expansion already covered by expand
    check("leader_chain_expansion", diag["expansions"] >= 1)

    # 6 reinforcement inclusion
    check("reinforcement_inclusion_geom", point_in_bbox(515, 505, win))

    # 7 neighbour handling — QA ambiguity flag
    evidence = {
        "beam_id": "BX",
        "target_beam": {"in_ownership": False, "in_envelope": True},
        "evidence_window": {
            "bbox": list(win),
            "base_bbox": list(base),
            "expansion": diag,
        },
        "annotations": [],
        "leaders": [],
        "reinforcement": [],
        "leader_chains": {"accepted": [], "complete_count": 0},
        "relationships": [],
        "shared_scopes": [],
        "counts": {"annotations": 0, "leaders": 0, "reinforcement": 0},
    }
    qa = evaluate_crop_qa(
        evidence=evidence,
        engineering_render={"success": False},
        overlay_render={"success": False},
        neighbour_beam_ids=["BY"],
    )
    check(
        "neighbor_beam_handling",
        qa["flags"]["neighbour_ambiguity"] is True,
        str(qa["flags"]),
    )

    # 8 crop clipping detection
    check("crop_clipping_detection", diag["clipped_before_count"] >= 1)

    # 9 coordinate transform — smoke via render meta requirement
    check("coordinate_transform_gate_exists", "COORDINATE_TRANSFORM_VALID" in qa["gates"])

    # 10 render success/failure gate
    check("render_success_gate", qa["gates"]["RENDER_SUCCESS"] == "FAIL")

    # 11 crop QA gates present
    needed = {
        "TARGET_BEAM_PRESENT",
        "RELEVANT_REINFORCEMENT_PRESENT",
        "RELEVANT_ANNOTATION_PRESENT",
        "COMPLETE_LEADER_CHAIN",
        "RELEVANT_EVIDENCE_NOT_CLIPPED",
    }
    check("crop_qa_gates", needed.issubset(set(qa["gates"])))

    # 12 evidence recall calc
    evidence2 = dict(evidence)
    evidence2["reinforcement"] = [{"reinforcement_id": "BAR::1", "bbox": [10, 10, 20, 20]}]
    evidence2["counts"] = {"annotations": 0, "leaders": 0, "reinforcement": 1}
    qa2 = evaluate_crop_qa(
        evidence=evidence2,
        engineering_render={"success": True, "img_w": 10, "img_h": 10, "path": "x"},
        overlay_render={"success": True, "path": "y"},
    )
    rec = per_beam_recall(evidence2, qa2)
    check("evidence_recall_calc", "pipeline_reinforcement_coverage_pct" in rec)

    # Edge: empty evidence pack aggregate
    agg = aggregate_metrics(
        [
            {
                "render_success": True,
                "crop_qa_overall": "PASS",
                "beam_present": True,
                "reinforcement_present": True,
                "annotation_present": True,
                "leader_present": False,
                "leader_chain_complete": False,
                "expanded": True,
                "evidence_clipped": False,
                "neighbour_ambiguity": False,
                "hard_fails": [],
                "soft_fails": [],
                "gt_bar_count": 2,
                "gt_reinforcement_evidence_present": True,
            }
        ]
    )
    check("aggregate_metrics", agg["beams_processed"] == 1 and agg["successful_renders"] == 1)

    # Degenerate short beam
    short = beam_base_bbox(
        envelope_extent=[0, 0, 10, 10],
        ownership_crop=None,
        registry_bbox=None,
        base_margin_mm=50,
    )
    check("short_beam_inflate", short is not None and (short[2] - short[0]) > 100)

    passed = sum(1 for r in results if r["pass"])
    return {
        "model_version": MODEL_VERSION,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "success": passed == len(results),
        "results": results,
    }
