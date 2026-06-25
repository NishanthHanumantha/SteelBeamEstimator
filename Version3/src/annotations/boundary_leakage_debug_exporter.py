"""Phase D.1.3.1 — DXF debug overlay for boundary leakage analysis."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import ezdxf
from loguru import logger

from src.annotations.annotation_region_validator import (
    AnnotationRegionValidator,
    OwnershipRegion,
)
from src.annotations.boundary_leakage_analyzer import BoundaryLeakageRecord

DEBUG_LAYER = "DEBUG_BOUNDARY_LEAKAGE"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0


class BoundaryLeakageDebugExporter:
    """Draw leakage vectors from outside annotations to current and neighbor centers."""

    def export(
        self,
        records: List[BoundaryLeakageRecord],
        regions: Dict[Tuple[str, int], OwnershipRegion],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)

        if "DASHED" not in doc.linetypes:
            doc.linetypes.add(
                "DASHED",
                pattern=[0.5, 0.25, -0.25],
                description="Dashed line",
            )

        msp = doc.modelspace()

        for record in records:
            ax = float(record["x"])
            ay = float(record["y"])
            current_key = (
                record["current_region"]["beam_mark"],
                record["current_region"]["occurrence_id"],
            )
            neighbor_key = (
                record["nearest_region"]["beam_mark"],
                record["nearest_region"]["occurrence_id"],
            )

            current_region = regions.get(current_key)
            neighbor_region = regions.get(neighbor_key)
            if current_region is None or neighbor_region is None:
                continue

            current_center = (
                float(current_region["center_x"]),
                float(current_region["center_y"]),
            )
            neighbor_center = (
                float(neighbor_region["center_x"]),
                float(neighbor_region["center_y"]),
            )

            msp.add_circle(
                (ax, ay),
                MARKER_RADIUS_MM,
                dxfattribs={"layer": DEBUG_LAYER},
            )

            msp.add_line(
                (ax, ay),
                current_center,
                dxfattribs={"layer": DEBUG_LAYER, "linetype": "DASHED"},
            )
            msp.add_line(
                (ax, ay),
                neighbor_center,
                dxfattribs={"layer": DEBUG_LAYER},
            )

            current_label = AnnotationRegionValidator.region_label(
                record["current_region"]["beam_mark"],
                record["current_region"]["occurrence_id"],
            )
            neighbor_label = AnnotationRegionValidator.region_label(
                record["nearest_region"]["beam_mark"],
                record["nearest_region"]["occurrence_id"],
            )
            label_lines = [
                "CURRENT",
                current_label,
                f"{record['distance_to_current_region_mm']:.0f}",
                "NEIGHBOR",
                neighbor_label,
                f"{record['distance_to_neighbor_region_mm']:.0f}",
                record["classification"],
            ]
            label = "\n".join(label_lines)

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
