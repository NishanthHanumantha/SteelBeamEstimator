"""Phase D.1.7F — DXF debug overlay for SFR semantic classification."""

from pathlib import Path
from typing import List

import ezdxf
from loguru import logger

from src.validation.sfr_semantic_validator import SfrSemanticRecord

DEBUG_LAYER = "DEBUG_SFR_SEMANTICS"
TEXT_HEIGHT_MM = 260.0
MARKER_RADIUS_MM = 110.0
LABEL_OFFSET_MM = 300.0

_CLASS_COLOR = {
    "ENGINEERING_SFR": 3,
    "REFERENCE_NOTE": 5,
    "PARTIAL_SFR": 2,
    "UNKNOWN": 1,
}


class SfrSemanticDebugExporter:
    """Visualise semantic SFR classification on a debug DXF layer."""

    def export(self, records: List[SfrSemanticRecord], output_path: Path) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for rec in records:
            ax = float(rec["x"])
            ay = float(rec["y"])
            semantic_class = str(rec["semantic_class"])
            color = _CLASS_COLOR.get(semantic_class, 7)
            final_status = str(rec["final_status"])

            label = (
                f"[{semantic_class}]\n"
                f"status={final_status}\n"
                f"{rec['beam_mark']} {rec['sketch_id']}\n"
                f"{rec['clean_text'][:40]}"
            )

            msp.add_circle(
                (ax, ay),
                MARKER_RADIUS_MM,
                dxfattribs={"layer": DEBUG_LAYER, "color": color},
            )
            msp.add_text(
                label,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "color": color,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (ax, ay + LABEL_OFFSET_MM),
                },
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info(
            "SFR semantic debug DXF: {} annotations -> {}",
            len(records),
            output_path.resolve(),
        )
