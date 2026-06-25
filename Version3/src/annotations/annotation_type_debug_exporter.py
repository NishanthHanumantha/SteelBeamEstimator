"""Phase D.1.6 — DXF debug overlay for annotation type classification."""

from pathlib import Path
from typing import Any, List

import ezdxf
from loguru import logger

DEBUG_LAYER = "DEBUG_ANNOTATION_TYPES"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0


class AnnotationTypeDebugExporter:
    """Label each annotation with its classified engineering type."""

    def export(
        self,
        classified_records: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for record in classified_records:
            ax = float(record["x"])
            ay = float(record["y"])
            annotation_type = str(record["annotation_type"])
            clean_text = str(record["clean_text"])
            label = f"[{annotation_type}] {clean_text}"

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
        logger.info("Wrote {}", output_path.resolve())
