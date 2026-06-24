"""Phase D.1.5 — DXF debug overlay for post-reassignment validation."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import ezdxf
from loguru import logger

from src.annotations.annotation_region_validator import (
    AnnotationRegionValidator,
    OwnershipRegion,
)

DEBUG_LAYER = "DEBUG_POST_REASSIGNMENT"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0
REGION_LABEL_OFFSET_MM = 600.0


class PostReassignmentDebugExporter:
    """Draw ownership regions, annotations, and validation labels."""

    def export(
        self,
        audit_records: List[dict[str, Any]],
        region_records: List[dict[str, Any]],
        leakage_records: List[dict[str, Any]],
        regions: Dict[Tuple[str, int], OwnershipRegion],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for key, region in regions.items():
            self._draw_region(msp, region)

        leakage_lookup = {
            (
                str(r["beam_mark"]),
                int(r["occurrence_id"]),
                r["annotation"],
                round(float(r["x"]), 1),
                round(float(r["y"]), 1),
            ): r["classification"]
            for r in leakage_records
        }

        for record in region_records:
            ax = float(record["x"])
            ay = float(record["y"])
            classification = str(record["classification"])
            confidence = self._audit_confidence(record, audit_records)
            preview = AnnotationRegionValidator._preview_text(record["annotation"])

            msp.add_circle(
                (ax, ay),
                MARKER_RADIUS_MM,
                dxfattribs={"layer": DEBUG_LAYER},
            )

            leakage_key = (
                record["beam_mark"],
                record["occurrence_id"],
                record["annotation"],
                round(ax, 1),
                round(ay, 1),
            )
            leakage_class = leakage_lookup.get(leakage_key)

            label_parts = [preview, confidence]
            if classification == "OUTSIDE_REGION":
                label_parts.append("OUTSIDE")
                label_parts.append(f"{record['distance_to_region_mm']:.0f}")
            if leakage_class == "REASSIGN_CANDIDATE":
                label_parts.append("CANDIDATE")

            msp.add_text(
                " ".join(label_parts),
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (ax, ay + LABEL_OFFSET_MM),
                },
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Wrote {}", output_path.resolve())

    def _audit_confidence(
        self, region_record: dict[str, Any], audit_records: List[dict[str, Any]]
    ) -> str:
        for audit in audit_records:
            if (
                audit["beam_mark"] == region_record["beam_mark"]
                and audit["sketch_id"] == region_record["sketch_id"]
                and audit["annotation"] == region_record["annotation"]
                and float(audit["x"]) == float(region_record["x"])
                and float(audit["y"]) == float(region_record["y"])
            ):
                return str(audit["confidence"])
        return "?"

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
