"""Phase D.1.6A — DXF debug overlay for annotation coverage gaps."""

from pathlib import Path
from typing import List

import ezdxf
from loguru import logger

from src.annotations.annotation_coverage_auditor import MissingAnnotation

DEBUG_LAYER = "DEBUG_ANNOTATION_COVERAGE"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0


class AnnotationCoverageDebugExporter:
    """Mark missing region texts not captured in ownership output."""

    def export(
        self,
        missing_annotations: List[MissingAnnotation],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for item in missing_annotations:
            ax = float(item["x"])
            ay = float(item["y"])
            display = item["clean_text"] or item["raw_text"]
            label = f"MISSING: {display}"

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
