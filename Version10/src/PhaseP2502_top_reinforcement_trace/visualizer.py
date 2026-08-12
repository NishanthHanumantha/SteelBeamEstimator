"""Diagnostic overlay PNGs (does not mutate production crops)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

BBox = Tuple[float, float, float, float]


def render_diagnostic_overlay(
    *,
    engine_root: Path,
    dxf_path: Path,
    extent: BBox,
    out_path: Path,
    beam_id: str,
    own_geom: Optional[Dict[str, Any]],
    rejected_bars: list,
    ann_pos: Optional[Dict[str, float]],
    leader_geom: Optional[Dict[str, float]],
) -> Dict[str, Any]:
    from PhaseP250_beam_evidence_crop_qa.renderer import (
        render_engineering_crop,
        render_evidence_overlay,
    )

    out_path = Path(out_path)
    eng = out_path.with_name(out_path.stem + "_base.png")
    r = render_engineering_crop(
        engine_root=engine_root, dxf_path=dxf_path, extent=extent, out_path=eng
    )
    if not r.get("success"):
        return r

    # Build a pseudo evidence dict for overlay labels
    reinforcement = []
    for b in rejected_bars:
        g = b.get("9_final_r31_coordinates") or {}
        reinforcement.append(
            {
                "reinforcement_id": f"REJECTED::{b.get('bar_id')}",
                "geometry": {
                    "start_x": g.get("start_x"),
                    "end_x": g.get("end_x"),
                    "y_position": g.get("y_position"),
                },
            }
        )
    if own_geom and own_geom.get("dxf", {}).get("bbox"):
        bb = own_geom["dxf"]["bbox"]
        reinforcement.append(
            {
                "reinforcement_id": f"ACTUAL_TOP::{own_geom.get('own_id')}",
                "geometry": {
                    "start_x": bb[0],
                    "end_x": bb[2],
                    "y_position": own_geom["dxf"].get("y_position"),
                },
            }
        )
    evidence = {
        "beam_id": beam_id,
        "annotations": (
            [
                {
                    "annotation_id": "4-Y25",
                    "raw_text": "4-Y25",
                    "position": ann_pos,
                }
            ]
            if ann_pos
            else []
        ),
        "leaders": (
            [{"leader_id": "LDR", "geometry": leader_geom}] if leader_geom else []
        ),
        "reinforcement": reinforcement,
        "evidence_window": {"expansion": {"expanded": False, "expansions": 0, "still_clipped_count": 0}},
    }
    return render_evidence_overlay(
        engineering_png=eng, evidence=evidence, out_path=out_path, extent=extent
    )
