"""Phase D.3.1 — DXF debug overlay for beam group confidence validation."""

from pathlib import Path
from typing import Any, Dict, List

import ezdxf
from loguru import logger

DEBUG_LAYER = "DEBUG_BEAM_GROUP_VALIDATION"
TEXT_HEIGHT_MM = 220.0

_COLOR_HIGH = 3
_COLOR_MEDIUM = 2
_COLOR_LOW = 1


class BeamGroupDebugExporterV2:
    """Visualise group confidence on detail envelopes."""

    def export(
        self,
        beam_groups: List[dict[str, Any]],
        confidence_results: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        score_by_id = {r["group_id"]: r for r in confidence_results}
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for group in beam_groups:
            gid = group["beam_group_id"]
            result = score_by_id.get(gid, {})
            confidence = result.get("confidence", "LOW")
            color = {
                "HIGH": _COLOR_HIGH,
                "MEDIUM": _COLOR_MEDIUM,
                "LOW": _COLOR_LOW,
            }.get(confidence, _COLOR_LOW)

            envelope = group.get("detail_band", group["bounding_box"])
            self._draw_rect(
                msp,
                envelope,
                color,
                (
                    f"{gid} {result.get('confidence_score', '?')} {confidence}\n"
                    f"beams={len(group['members'])} "
                    f"clusters={result.get('detail_sketch_cluster_count', '?')}"
                ),
            )

            warning_text = "; ".join(result.get("warnings", [])[:2])
            if warning_text:
                msp.add_text(
                    warning_text[:80],
                    dxfattribs={
                        "layer": DEBUG_LAYER,
                        "color": color,
                        "height": TEXT_HEIGHT_MM * 0.75,
                        "insert": (envelope["xmin"], envelope["ymin"] - 400),
                    },
                )

        doc.saveas(output_path)
        logger.info("Beam group validation debug DXF -> {}", output_path)

    def _draw_rect(
        self,
        msp: Any,
        bbox: Dict[str, float],
        color: int,
        label: str,
    ) -> None:
        xmin, ymin, xmax, ymax = bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]
        points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)]
        msp.add_lwpolyline(points, dxfattribs={"layer": DEBUG_LAYER, "color": color}, close=True)
        msp.add_text(
            label,
            dxfattribs={
                "layer": DEBUG_LAYER,
                "color": color,
                "height": TEXT_HEIGHT_MM,
                "insert": (xmin, ymax + 250),
            },
        )
