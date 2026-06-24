"""Phase D.1.3 — DXF debug overlay for annotation ownership region validation."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import ezdxf
from loguru import logger

from src.annotations.annotation_region_validator import (
    AnnotationRegionValidator,
    OwnershipRegion,
    RegionValidationRecord,
)

DEBUG_LAYER = "DEBUG_ANNOTATION_REGION"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0
REGION_LABEL_OFFSET_MM = 600.0


class AnnotationRegionDebugExporter:
    """Draw ownership regions and spatial classification labels."""

    def export(
        self,
        records: List[RegionValidationRecord],
        regions: Dict[Tuple[str, int], OwnershipRegion],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for key, region in regions.items():
            self._draw_region(msp, region)

        region_centers = {
            key: (float(region["center_x"]), float(region["center_y"]))
            for key, region in regions.items()
        }

        for record in records:
            ax = float(record["x"])
            ay = float(record["y"])
            classification = record["classification"]
            preview = AnnotationRegionValidator._preview_text(record["annotation"])

            msp.add_circle(
                (ax, ay),
                MARKER_RADIUS_MM,
                dxfattribs={"layer": DEBUG_LAYER},
            )

            if classification == "INSIDE_REGION":
                label = preview
            elif classification == "NEAR_REGION_EDGE":
                label = f"{preview} EDGE"
            else:
                label = f"{preview} OUTSIDE"
                center = region_centers.get(
                    (record["beam_mark"], record["occurrence_id"])
                )
                if center is not None:
                    msp.add_line(
                        (ax, ay),
                        center,
                        dxfattribs={"layer": DEBUG_LAYER},
                    )

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

    def _draw_region(self, msp: Any, region: OwnershipRegion) -> None:
        xmin = float(region["xmin"])
        ymin = float(region["ymin"])
        xmax = float(region["xmax"])
        ymax = float(region["ymax"])
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

        label = AnnotationRegionValidator.region_label(
            region["beam_mark"],
            region["occurrence_id"],
        )
        label_x = (xmin + xmax) / 2.0
        label_y = ymax + REGION_LABEL_OFFSET_MM
        msp.add_text(
            label,
            dxfattribs={
                "layer": DEBUG_LAYER,
                "height": TEXT_HEIGHT_MM,
                "insert": (label_x, label_y),
            },
        )
