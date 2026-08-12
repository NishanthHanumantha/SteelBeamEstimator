"""Focused unit tests for P2.5.0.3 OWN TOP_BAR packaging."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseP250_beam_evidence_crop_qa.owned_geometry import collect_accepted_owned_geometry
from PhaseP250_beam_evidence_crop_qa.evidence_window import expand_window_to_evidence
from PhaseP250_beam_evidence_crop_qa.crop_qa import evaluate_crop_qa

from .config import FOCUS

MODEL_VERSION = "10.6.2"


def run_unit_tests() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        results.append({"name": name, "pass": bool(cond), "detail": detail})

    # Synthetic ownership + graph for B97A-like chain
    ownership = {
        "accepted_chains": [
            {
                "accepted": True,
                "annotation_id": FOCUS["B97A"]["ann_4y25"],
                "text": "4-Y25",
                "semantic_type": "BarCallout",
                "leaders": [FOCUS["B97A"]["leader"]],
                "describes": [FOCUS["B97A"]["own_entity"]],
            }
        ],
        "bar_results": {
            "BAR::2B7B3233": {"accepted": False, "reason": "bar_y_outside_reinforcement_elevation"},
            "BAR::5B1BFCC2": {"accepted": False, "reason": "bar_y_outside_reinforcement_elevation"},
        },
    }
    graph = {
        "nodes": [
            {
                "id": FOCUS["B97A"]["own_entity"],
                "type": "OwnedEntity",
                "beam_id": "B97A",
                "attributes": {
                    "handle": "1247FFF",
                    "entity_type": "LWPOLYLINE",
                    "layer": "-STR-BEAM",
                    "role": "TOP_BAR",
                },
            }
        ]
    }

    class _FakeEnt:
        def __init__(self):
            self._pts = [[0.0, 0.0], [1000.0, 0.0]]

        def dxftype(self):
            return "LWPOLYLINE"

        def get_points(self, _fmt):
            return self._pts

        @property
        def dxf(self):
            class D:
                handle = "1247FFF"
                layer = "-STR-BEAM"

            return D()

    handle_index = {"1247FFF": _FakeEnt()}
    owned = collect_accepted_owned_geometry(
        beam_id="B97A",
        ownership=ownership,
        annotation_graph=graph,
        handle_index=handle_index,
    )
    check("b97a_own_top_bar_lookup", len(owned) == 1 and owned[0]["ownership_id"] == FOCUS["B97A"]["own_entity"])
    check("source_dxf_handle_resolution", owned[0]["source_handle"] == "1247FFF" and owned[0]["dxf_resolved"])
    check("own_geometry_coordinate_consistency", owned[0]["bbox"] == [0.0, 0.0, 1000.0, 0.0] or (
        owned[0]["bbox"][0] == 0.0 and owned[0]["bbox"][2] == 1000.0
    ))
    check(
        "annotation_leader_own_linkage",
        owned[0]["annotation_id"] == FOCUS["B97A"]["ann_4y25"]
        and owned[0]["leader_id"] == FOCUS["B97A"]["leader"],
    )
    check("deterministic_evidence_id", owned[0]["evidence_id"] == "OWNGEO::B97A::1247FFF")

    # B98A lookup shape
    ownership98 = {
        "accepted_chains": [
            {
                "accepted": True,
                "annotation_id": FOCUS["B98A"]["ann_4y25"],
                "text": "4-Y25",
                "semantic_type": "BarCallout",
                "leaders": [FOCUS["B98A"]["leader"]],
                "describes": [FOCUS["B98A"]["own_entity"]],
            }
        ]
    }
    graph98 = {
        "nodes": [
            {
                "id": FOCUS["B98A"]["own_entity"],
                "type": "OwnedEntity",
                "attributes": {
                    "handle": "1247FFE",
                    "entity_type": "LWPOLYLINE",
                    "layer": "-STR-BEAM",
                    "role": "TOP_BAR",
                },
            }
        ]
    }

    class _Fake98:
        def dxftype(self):
            return "LWPOLYLINE"

        def get_points(self, _fmt):
            return [[10.0, 5.0], [500.0, 5.0]]

        @property
        def dxf(self):
            class D:
                handle = "1247FFE"
                layer = "-STR-BEAM"

            return D()

    owned98 = collect_accepted_owned_geometry(
        beam_id="B98A",
        ownership=ownership98,
        annotation_graph=graph98,
        handle_index={"1247FFE": _Fake98()},
    )
    check("b98a_own_top_bar_lookup", len(owned98) == 1 and owned98[0]["source_handle"] == "1247FFE")

    # OWN participates in crop bounds
    base = (0.0, -100.0, 200.0, 100.0)
    win, diag = expand_window_to_evidence(
        base, [(0.0, 0.0, 1000.0, 0.0)], pad_mm=10, max_iters=3
    )
    check("own_geometry_participates_in_crop_bounds", win[2] >= 1000.0 and diag["expanded"])

    # Rejected bars excluded from package QA
    evidence = {
        "beam_id": "B97A",
        "target_beam": {"in_ownership": True, "in_envelope": True},
        "evidence_window": {
            "bbox": list(win),
            "base_bbox": list(base),
            "expansion": {"still_clipped_count": 0, "expanded": True, "expansions": 1},
        },
        "annotations": [{"annotation_id": FOCUS["B97A"]["ann_4y25"], "bbox": [50, 50, 60, 60]}],
        "leaders": [{"leader_id": FOCUS["B97A"]["leader"], "bbox": [40, 40, 80, 80]}],
        "reinforcement": [],
        "owned_geometry": owned,
        "leader_chains": {
            "accepted": ownership["accepted_chains"],
            "complete_count": 1,
        },
        "relationships": [],
        "shared_scopes": [],
        "excluded_rejected_evidence": {"bars": FOCUS["B97A"]["rejected_bars"], "leaders": []},
    }
    qa = evaluate_crop_qa(
        evidence=evidence,
        engineering_render={
            "success": True,
            "img_w": 100,
            "img_h": 100,
            "path": "x",
            "owned_geometry_paint_count": 1,
        },
        overlay_render={"success": True, "path": "y"},
        render_validation={"rendered": True, "distinguishable": True},
    )
    check("own_geometry_included_gate", qa["gates"]["OWN_TOP_BAR_PRESENT"] == "PASS")
    check("rejected_physical_bars_excluded_gate", qa["gates"]["REJECTED_PHYSICAL_BAR_EXCLUDED"] == "PASS")
    check("no_extreme_crop_gate", qa["gates"]["CROP_NOT_EXTREME"] == "PASS", str(qa["gates"]))
    check("own_linked_gate", qa["gates"]["OWN_TOP_BAR_LINKED_TO_ACCEPTED_CHAIN"] == "PASS")
    check("own_source_valid_gate", qa["gates"]["OWN_TOP_BAR_SOURCE_VALID"] == "PASS")

    # Deterministic IDs twice
    owned_b = collect_accepted_owned_geometry(
        beam_id="B97A",
        ownership=ownership,
        annotation_graph=graph,
        handle_index=handle_index,
    )
    check("deterministic_ids_x2", owned[0]["evidence_id"] == owned_b[0]["evidence_id"])

    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "model_version": MODEL_VERSION,
    }
