"""Phase C.5 — DXF debug overlay for sketch ownership."""

from pathlib import Path
from typing import Any, List

import ezdxf
from loguru import logger

from src.grid.sketch_ownership_auditor import LONG_DISTANCE_WARNING_MM

DEBUG_LAYER = "DEBUG_SKETCH_OWNERSHIP"
HEADER_MARKER_RADIUS_MM = 300.0
TEXT_HEIGHT_MM = 600.0
LABEL_OFFSET_MM = 900.0


class SketchOwnershipDebugExporter:
    """Draw header occurrences, sketch bboxes, and ownership leader lines."""

    def export(
        self,
        occurrences: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}
        occurrence_lookup = {
            (occ["beam_mark"], occ["occurrence_id"]): occ for occ in occurrences
        }

        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for record in ownership:
            mark = record["beam_mark"]
            occurrence_id = int(record["occurrence_id"])
            occurrence = occurrence_lookup.get((mark, occurrence_id))
            if occurrence is None:
                continue

            header_x = float(occurrence["x"])
            header_y = float(occurrence["y"])
            owned_items = record.get("owned_sketches", [])
            if len(owned_items) == 1 and isinstance(owned_items[0], dict):
                distance_mm = owned_items[0].get("distance_mm")
                label = (
                    f"{mark}_H{occurrence_id}\nd={int(distance_mm)}"
                    if distance_mm is not None
                    else f"{mark}_H{occurrence_id}"
                )
            else:
                label = f"{mark}_H{occurrence_id}"

            msp.add_circle(
                (header_x, header_y),
                HEADER_MARKER_RADIUS_MM,
                dxfattribs={"layer": DEBUG_LAYER},
            )
            msp.add_text(
                label,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (header_x, header_y + LABEL_OFFSET_MM),
                },
            )

            for owned in record.get("owned_sketches", []):
                if isinstance(owned, dict):
                    sketch_id = str(owned["sketch_id"])
                    distance_mm = owned.get("distance_mm")
                else:
                    sketch_id = str(owned)
                    distance_mm = None
                sketch = sketch_lookup.get(sketch_id)
                if sketch is None:
                    continue
                self._draw_sketch_link(
                    msp,
                    sketch,
                    header_x,
                    header_y,
                    sketch_id,
                    distance_mm,
                )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Wrote {}", output_path.resolve())

    def _draw_sketch_link(
        self,
        msp: Any,
        sketch: dict[str, Any],
        header_x: float,
        header_y: float,
        sketch_id: str,
        distance_mm: float | None = None,
    ) -> None:
        bbox = sketch["bbox"]
        xmin = float(bbox["xmin"])
        ymin = float(bbox["ymin"])
        xmax = float(bbox["xmax"])
        ymax = float(bbox["ymax"])
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0

        corners = [
            (xmin, ymin),
            (xmax, ymin),
            (xmax, ymax),
            (xmin, ymax),
            (xmin, ymin),
        ]
        msp.add_lwpolyline(
            corners,
            dxfattribs={"layer": DEBUG_LAYER},
            close=True,
        )
        if distance_mm is not None:
            sketch_label = f"{sketch_id}\n{int(distance_mm)} mm"
            if distance_mm > LONG_DISTANCE_WARNING_MM:
                sketch_label = f"{sketch_label}\nWARNING"
        else:
            sketch_label = sketch_id
        msp.add_text(
            sketch_label,
            dxfattribs={
                "layer": DEBUG_LAYER,
                "height": TEXT_HEIGHT_MM * 0.75,
                "insert": (cx, cy),
            },
        )
        msp.add_line(
            (header_x, header_y),
            (cx, cy),
            dxfattribs={"layer": DEBUG_LAYER},
        )
