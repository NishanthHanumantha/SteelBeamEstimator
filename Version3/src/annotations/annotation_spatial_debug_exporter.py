"""Phase D.1.2 — DXF debug overlay for annotation spatial validation."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import ezdxf
from loguru import logger

from src.annotations.annotation_spatial_validator import (
    AnnotationSpatialValidator,
    BBOX_MARGIN_MM,
    SpatialValidationRecord,
)

DEBUG_LAYER = "DEBUG_ANNOTATION_SPATIAL"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0


class AnnotationSpatialDebugExporter:
    """Draw sketch bboxes, expanded bboxes, and spatial classification labels."""

    def export(
        self,
        records: List[SpatialValidationRecord],
        sketches: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}
        drawn_sketches: set[str] = set()

        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for record in records:
            sketch_id = record["sketch_id"]
            sketch = sketch_lookup.get(sketch_id)
            if sketch is None:
                continue

            if sketch_id not in drawn_sketches:
                self._draw_bbox_pair(msp, sketch["bbox"])
                drawn_sketches.add(sketch_id)

            ax = float(record["x"])
            ay = float(record["y"])
            classification = record["classification"]
            tag = classification[0]  # I, N, O

            msp.add_circle(
                (ax, ay),
                MARKER_RADIUS_MM,
                dxfattribs={"layer": DEBUG_LAYER},
            )

            if classification == "OUTSIDE":
                orig_bbox = AnnotationSpatialValidator._bbox_tuple(sketch["bbox"])
                nearest = AnnotationSpatialValidator._nearest_point_on_bbox(
                    ax, ay, orig_bbox
                )
                msp.add_line(
                    (ax, ay),
                    nearest,
                    dxfattribs={"layer": DEBUG_LAYER},
                )
                label = f"O {int(record['distance_to_bbox_mm'])}"
            else:
                label = tag

            msp.add_text(
                label,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (ax, ay + LABEL_OFFSET_MM),
                },
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Wrote {}", output_path.resolve())

    def _draw_bbox_pair(self, msp: Any, bbox: dict[str, Any]) -> None:
        xmin = float(bbox["xmin"])
        ymin = float(bbox["ymin"])
        xmax = float(bbox["xmax"])
        ymax = float(bbox["ymax"])

        expanded = (
            xmin - BBOX_MARGIN_MM,
            ymin - BBOX_MARGIN_MM,
            xmax + BBOX_MARGIN_MM,
            ymax + BBOX_MARGIN_MM,
        )
        self._draw_rectangle(msp, expanded)
        self._draw_rectangle(msp, (xmin, ymin, xmax, ymax))

    @staticmethod
    def _draw_rectangle(
        msp: Any, bbox: Tuple[float, float, float, float]
    ) -> None:
        xmin, ymin, xmax, ymax = bbox
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
