"""Phase D.1.7A — DXF debug overlay for DIMENSION text source audit."""

from pathlib import Path
from typing import List

import ezdxf
from loguru import logger

from src.annotations.dimension_source_auditor import DimensionSourceRecord

DEBUG_LAYER = "DEBUG_DIMENSION_SOURCE"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0

_SOURCE_PREFIX = {
    "ENGINEERING_TEXT": "[ENG]",
    "MEASUREMENT_VALUE": "[MEAS]",
    "UNKNOWN_SOURCE": "[UNKNOWN]",
}


class DimensionSourceDebugExporter:
    """Mark DIMENSION entities with their audited text source classification."""

    def export(
        self,
        records: List[DimensionSourceRecord],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for record in records:
            ax = float(record["x"])
            ay = float(record["y"])
            prefix = _SOURCE_PREFIX.get(record["source_type"], "[UNKNOWN]")
            label = f"{prefix} {record['final_extracted_text']}"

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
        logger.info("Wrote {} ({} markers)", output_path.resolve(), len(records))
