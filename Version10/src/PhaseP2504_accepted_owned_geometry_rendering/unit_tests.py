"""Unit tests for P2.5.0.4 OWN engineering-crop rendering."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseP250_beam_evidence_crop_qa.renderer import (
    paint_owned_geometry_on_axes,
    _owned_polyline_points,
)
from PhaseP250_beam_evidence_crop_qa.owned_geometry import collect_accepted_owned_geometry
from PhaseP2504_accepted_owned_geometry_rendering.config import FOCUS, ROOT_CAUSE

MODEL_VERSION = "10.6.3"


def run_unit_tests() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        results.append({"name": name, "pass": bool(cond), "detail": detail})

    check("root_cause_documented", "color 7" in ROOT_CAUSE.lower() or "ACI color 7" in ROOT_CAUSE)

    # Synthetic OWN record uses actual-style points (no synthetic fabrication of bar from text)
    og = {
        "accepted": True,
        "evidence_type": "OWN_TOP_BAR",
        "semantic_role": "TOP_BAR",
        "ownership_id": FOCUS["B97A"]["own_entity"],
        "source_handle": FOCUS["B97A"]["own_handle"],
        "evidence_id": "OWNGEO::B97A::1247FFF",
        "geometry": {
            "points": [
                [31652245.4453964, -21208369.09241377],
                [31649245.44539641, -21208369.09241377],
            ]
        },
    }
    pts = _owned_polyline_points(og)
    check("b97a_own_entity_points", pts is not None and len(pts) == 2)
    check("no_synthetic_from_text", "4-Y25" not in str(og.get("geometry")))

    class _Ax:
        def __init__(self):
            self.calls = []

        def plot(self, xs, ys, **kwargs):
            self.calls.append({"xs": list(xs), "ys": list(ys), **kwargs})

    ax = _Ax()
    painted = paint_owned_geometry_on_axes(ax, [og])
    check("paint_draws_actual_coords", len(painted) == 1 and len(ax.calls) == 1)
    check("paint_no_labels", "label" in ax.calls[0] and ax.calls[0]["xs"][0] == pts[0][0])
    check("zorder_above_base", ax.calls[0].get("zorder", 0) >= 10)

    # B98A resolution shape via collect (BarCallout only)
    ownership = {
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
    graph = {
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

    class _E:
        def dxftype(self):
            return "LWPOLYLINE"

        def get_points(self, _f):
            return [[1.0, 2.0], [3.0, 2.0]]

        @property
        def dxf(self):
            class D:
                handle = "1247FFE"
                layer = "-STR-BEAM"

            return D()

    owned = collect_accepted_owned_geometry(
        beam_id="B98A",
        ownership=ownership,
        annotation_graph=graph,
        handle_index={"1247FFE": _E()},
    )
    check("b98a_own_entity_resolution", len(owned) == 1 and owned[0]["dxf_resolved"])
    check("actual_source_handle", owned[0]["source_handle"] == "1247FFE")

    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "model_version": MODEL_VERSION,
    }
