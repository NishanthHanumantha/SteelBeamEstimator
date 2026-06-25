"""Phase D.1.7B — DXF debug overlay for engineering annotation filter."""

from pathlib import Path
from typing import List

import ezdxf
from loguru import logger

from src.annotations.engineering_annotation_filter import SketchFilterRecord

DEBUG_LAYER = "DEBUG_ENGINEERING_ANNOTATIONS"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0

_TYPE_LABEL = {
    "BAR": "[BAR]",
    "STIRRUP": "[STIRRUP]",
    "ANCHORAGE": "[ANCHORAGE]",
    "SIDE_FACE_REINF": "[SFR]",
}


class EngineeringAnnotationDebugExporter:
    """Mark retained engineering annotations by classification type."""

    def export(
        self,
        engineering_records: List[SketchFilterRecord],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for record in engineering_records:
            for item in record["annotations"]:
                ax = float(item["x"])
                ay = float(item["y"])
                ann_type = str(item["annotation_type"])
                prefix = _TYPE_LABEL.get(ann_type, f"[{ann_type}]")
                display = item["clean_text"]
                label = f"{prefix} {display}"

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
        count = sum(len(r["annotations"]) for r in engineering_records)
        logger.info("Wrote {} ({} markers)", output_path.resolve(), count)
