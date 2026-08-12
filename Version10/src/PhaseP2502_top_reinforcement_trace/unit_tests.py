"""Focused unit tests for P2.5.0.2."""
from __future__ import annotations

from typing import Any, Dict, List

from .classification import classify_rejected_bar, completeness_state, decide_next_action
from .spatial_metrics import bar_spatial_vs_beam, y_offset

MODEL_VERSION = "10.6.1"


def run_unit_tests() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        results.append({"name": name, "pass": bool(cond), "detail": detail})

    # Spatial
    check("y_offset_far", abs(y_offset(0, 600, 45000) - 44400) < 1)
    spat = bar_spatial_vs_beam(
        bar_y=-21139158.0,
        bar_sx=31651894.0,
        bar_ex=31654294.0,
        concrete={"x0": 31651470.0, "x1": 31654670.0, "y0": -21208896.0, "y1": -21208329.0},
        depth_mm=600.0,
    )
    check("b98a_y_gap_huge", spat["beam_to_bar_y_offset_mm"] > 60000)
    check("b98a_x_overlap", spat["beam_to_bar_x_overlap_mm"] > 0)

    # Classification false candidate
    bar_trace = {
        "2_dxf_entity_type": "LINE",
        "1_dxf_entity_id": "11CD1B5",
        "3_layer": "-STR-REINF",
        "14_t18_accepted": False,
        "16_t18_rejection_reason": "bar_y_outside_reinforcement_elevation",
        "17_relationship_to_target_beam": {
            "spatial": {
                "beam_to_bar_y_offset_mm": 68690.0,
                "beam_depth_mm": 600.0,
                "bar_vs_envelope_position": "above",
            }
        },
    }
    own = {
        "own_id": "OWN::B98A::1247FFE",
        "is_actual_top_reinforcement_geometry": True,
    }
    c = classify_rejected_bar(bar_trace, own)
    check("classify_false_candidate", c["classification"] == "FALSE_CANDIDATE")

    # Completeness
    evidence = {
        "annotations": [{"annotation_id": "ANN-2a9913fa", "raw_text": "4-Y25"}],
        "leaders": [{"leader_id": "L"}],
        "reinforcement": [],
    }
    ownership = {
        "accepted_chains": [
            {"annotation_id": "ANN-2a9913fa", "text": "4-Y25", "describes": ["OWN::B98A::1247FFE"]}
        ]
    }
    comp = completeness_state(
        beam_id="B98A",
        evidence=evidence,
        ownership=ownership,
        own_trace=own,
        ann_id="ANN-2a9913fa",
    )
    check(
        "accepted_semantic_without_physical",
        comp["condition_ACCEPTED_SEMANTIC_WITHOUT_PHYSICAL_GEOMETRY"] is True,
    )
    check(
        "upstream_geometry_packaged_gap",
        comp["legitimate_or_missing_detection"]
        == "UPSTREAM_GEOMETRY_EXISTS_BUT_NOT_PACKAGED",
    )

    # Decision
    d = decide_next_action(
        classifications=[
            {"classification": "FALSE_CANDIDATE"},
            {"classification": "FALSE_CANDIDATE"},
            {"classification": "FALSE_CANDIDATE"},
            {"classification": "FALSE_CANDIDATE"},
        ],
        completeness=[
            {"legitimate_or_missing_detection": "UPSTREAM_GEOMETRY_EXISTS_BUT_NOT_PACKAGED"},
            {"legitimate_or_missing_detection": "UPSTREAM_GEOMETRY_EXISTS_BUT_NOT_PACKAGED"},
        ],
    )
    check("decision_fix_evidence_layer", d["decision"] == "FIX_EVIDENCE_LAYER")

    # Determinism of classification
    c2 = classify_rejected_bar(bar_trace, own)
    check("classification_reproducible", c == c2)

    passed = sum(1 for r in results if r["pass"])
    return {
        "model_version": MODEL_VERSION,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "success": passed == len(results),
        "results": results,
    }
