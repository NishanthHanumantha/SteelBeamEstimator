"""Phase D.1.7 — DXF debug overlay for DIMENSION extraction and ownership."""

from pathlib import Path
from typing import List

import ezdxf
from loguru import logger

from src.annotations.dimension_annotation_integrator import DimensionAssignment

DEBUG_LAYER = "DEBUG_DIMENSION_EXTRACTION"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0


class DimensionAnnotationDebugExporter:
    """Mark extracted DIMENSION annotations and their ownership assignment."""

    def export(
        self,
        assignments: List[DimensionAssignment],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for assignment in assignments:
            dimension = assignment["dimension"]
            ax = float(dimension["x"])
            ay = float(dimension["y"])
            text = dimension["text"]
            label = f"DIM: {text}"

            if assignment["assigned"]:
                owner = f"{assignment['beam_mark']}_H{assignment['occurrence_id']}"
                label = f"{label} -> {owner}"

            msp.add_circle(
                (ax, ay),
                MARKER_RADIUS_MM,
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
        logger.info("Wrote {} ({} markers)", output_path.resolve(), len(assignments))
