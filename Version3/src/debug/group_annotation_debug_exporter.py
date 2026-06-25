"""Phase D.3 — DXF debug overlay for beam groups and shared annotations."""

from pathlib import Path
from typing import Any, List

import ezdxf
from loguru import logger

from src.grouping.beam_group_types import BeamGroup, ExpandedAnnotation, SharedAnnotation

DEBUG_LAYER = "DEBUG_BEAM_GROUPS"
TEXT_HEIGHT_MM = 220.0
MARKER_RADIUS_MM = 120.0

_COLOR_SINGLE = 3
_COLOR_GROUP = 2
_COLOR_EXPANDED = 5
_COLOR_GROUP_BBOX = 8


class GroupAnnotationDebugExporter:
    """Visualise beam groups, shared annotations, and expanded ownership."""

    def export(
        self,
        beam_groups: List[BeamGroup],
        shared_annotations: List[SharedAnnotation],
        expanded: List[ExpandedAnnotation],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for group in beam_groups:
            bbox = group["bounding_box"]
            color = _COLOR_GROUP if group["is_multi_beam"] else _COLOR_SINGLE
            self._draw_rect(
                msp,
                bbox,
                color,
                f"{group['beam_group_id']} [{','.join(group['members'])}]",
            )
            detail = group["detail_band"]
            self._draw_rect(
                msp,
                detail,
                _COLOR_GROUP_BBOX,
                f"{group['beam_group_id']} detail",
                dashed=True,
            )

        for ann in shared_annotations:
            x, y = float(ann["x"]), float(ann["y"])
            color = _COLOR_GROUP if ann["ownership_mode"] == "GROUP" else _COLOR_SINGLE
            label = (
                f"{ann['ownership_mode']}\n"
                f"{ann.get('beam_group_id', '')}\n"
                f"{ann['clean_text'][:40]}"
            )
            msp.add_circle((x, y), MARKER_RADIUS_MM, dxfattribs={"layer": DEBUG_LAYER, "color": color})
            msp.add_text(
                label,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "color": color,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (x, y + 280),
                },
            )

        for entry in expanded:
            if not entry.get("expanded_from_group"):
                continue
            x, y = float(entry["x"]), float(entry["y"])
            msp.add_line(
                (x, y),
                (x + 400, y + 400),
                dxfattribs={"layer": DEBUG_LAYER, "color": _COLOR_EXPANDED},
            )
            msp.add_text(
                f"EXP->{entry['beam_mark']}",
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "color": _COLOR_EXPANDED,
                    "height": TEXT_HEIGHT_MM * 0.8,
                    "insert": (x + 420, y + 420),
                },
            )

        doc.saveas(output_path)
        logger.info("Beam group debug DXF -> {}", output_path)

    def _draw_rect(
        self,
        msp: Any,
        bbox: dict[str, float],
        color: int,
        label: str,
        dashed: bool = False,
    ) -> None:
        xmin, ymin, xmax, ymax = bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]
        points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)]
        attribs: dict[str, Any] = {"layer": DEBUG_LAYER, "color": color}
        if dashed:
            attribs["linetype"] = "DASHED"
        msp.add_lwpolyline(points, dxfattribs=attribs, close=True)
        msp.add_text(
            label,
            dxfattribs={
                "layer": DEBUG_LAYER,
                "color": color,
                "height": TEXT_HEIGHT_MM,
                "insert": (xmin, ymax + 200),
            },
        )
