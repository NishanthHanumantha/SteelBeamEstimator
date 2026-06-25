"""Phase D.3.3 — DXF debug overlay for ownership reconciliation."""

from pathlib import Path
from typing import Any, Dict, List

import ezdxf
from loguru import logger

DEBUG_LAYER = "DEBUG_OWNERSHIP"
TEXT_HEIGHT_MM = 180.0

_COLOR_HIGH = 3
_COLOR_MEDIUM = 2
_COLOR_LOW = 1
_COLOR_CONFLICT = 6
_COLOR_SHARED = 4


class OwnershipDebugExporter:
    """Visualise ownership arrows, regions, and confidence coloring."""

    def export(
        self,
        master: List[dict[str, Any]],
        detail_regions: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for region in detail_regions:
            bbox = region["bbox"]
            xmin, ymin, xmax, ymax = bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]
            points = [
                (xmin, ymin),
                (xmax, ymin),
                (xmax, ymax),
                (xmin, ymax),
                (xmin, ymin),
            ]
            msp.add_lwpolyline(
                points,
                dxfattribs={"layer": DEBUG_LAYER, "color": 8},
                close=True,
            )
            titles = ",".join(region.get("beam_titles", []))
            msp.add_text(
                f"{region['region_id']} {titles}",
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "color": 8,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (xmin, ymax + 200),
                },
            )

        for record in master:
            color = self._color_for(record)
            ax, ay = float(record["x"]), float(record["y"])
            msp.add_circle(
                (ax, ay),
                120.0,
                dxfattribs={"layer": DEBUG_LAYER, "color": color},
            )

            leader = record.get("leader_endpoint")
            if leader:
                msp.add_line(
                    (ax, ay),
                    (float(leader["x"]), float(leader["y"])),
                    dxfattribs={"layer": DEBUG_LAYER, "color": color},
                )
                ex, ey = float(leader["x"]), float(leader["y"])
            else:
                ex, ey = float(record.get("eval_x", ax)), float(record.get("eval_y", ay))

            msp.add_line(
                (ax, ay),
                (ex, ey),
                dxfattribs={"layer": DEBUG_LAYER, "color": color},
            )

            label = (
                f"{record['annotation_id'][:8]} "
                f"{record.get('confidence_score', 0)} "
                f"{record.get('resolved_beam_mark', '?')}\n"
                f"{str(record.get('clean_text', ''))[:24]}"
            )
            msp.add_text(
                label,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "color": color,
                    "height": TEXT_HEIGHT_MM * 0.8,
                    "insert": (ax, ay + 250),
                },
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Ownership debug DXF -> {}", output_path)

    def _color_for(self, record: dict[str, Any]) -> int:
        if record.get("is_ambiguous"):
            return _COLOR_CONFLICT
        if record.get("expanded_from_region"):
            return _COLOR_SHARED
        label = record.get("confidence_label", "LOW")
        if label == "HIGH":
            return _COLOR_HIGH
        if label == "MEDIUM":
            return _COLOR_MEDIUM
        return _COLOR_LOW
