"""Phase D.1.4 — DXF debug overlay for ownership reassignment."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import ezdxf
from loguru import logger

from src.annotations.annotation_region_validator import AnnotationRegionValidator
from src.annotations.ownership_reassignment_engine import ReassignmentLogEntry

DEBUG_LAYER = "DEBUG_REASSIGNMENT"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0


class OwnershipReassignmentDebugExporter:
    """Draw reassignment vectors from annotations to old and new owner centers."""

    def export(
        self,
        log_entries: List[ReassignmentLogEntry],
        occurrences: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        centers = {
            (str(occ["beam_mark"]), int(occ["occurrence_id"])): (
                float(occ["x"]),
                float(occ["y"]),
            )
            for occ in occurrences
        }

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

        for entry in log_entries:
            ax = float(entry["x"])
            ay = float(entry["y"])
            old_key = (
                str(entry["old_owner"]["beam_mark"]),
                int(entry["old_owner"]["occurrence_id"]),
            )
            new_key = (
                str(entry["new_owner"]["beam_mark"]),
                int(entry["new_owner"]["occurrence_id"]),
            )
            old_center = centers.get(old_key)
            new_center = centers.get(new_key)
            if old_center is None or new_center is None:
                continue

            msp.add_circle(
                (ax, ay),
                MARKER_RADIUS_MM,
                dxfattribs={"layer": DEBUG_LAYER},
            )
            msp.add_line(
                (ax, ay),
                old_center,
                dxfattribs={"layer": DEBUG_LAYER, "linetype": "DASHED"},
            )
            msp.add_line(
                (ax, ay),
                new_center,
                dxfattribs={"layer": DEBUG_LAYER},
            )

            preview = AnnotationRegionValidator._preview_text(entry["annotation"])
            old_label = AnnotationRegionValidator.region_label(*old_key)
            new_label = AnnotationRegionValidator.region_label(*new_key)
            label = "\n".join(
                [
                    preview,
                    f"OLD {old_label}",
                    f"NEW {new_label}",
                    f"cur {entry['current_distance_mm']:.0f}",
                    f"nei {entry['neighbor_distance_mm']:.0f}",
                ]
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
