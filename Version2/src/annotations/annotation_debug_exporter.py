"""Phase D.1 — DXF debug overlay for raw sketch annotations."""

from pathlib import Path
from typing import Any, List

import ezdxf
from loguru import logger

from src.annotations.raw_annotation_extractor import RawAnnotationRecord

DEBUG_LAYER = "DEBUG_ANNOTATIONS"
TEXT_HEIGHT_MM = 500.0
LABEL_OFFSET_MM = 800.0
MAX_PREVIEW_TEXTS = 3


class AnnotationDebugExporter:
    """Draw per-sketch annotation counts at sketch centroids."""

    def export(
        self,
        records: List[RawAnnotationRecord],
        sketches: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}

        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for record in records:
            sketch = sketch_lookup.get(record["sketch_id"])
            if sketch is None:
                continue

            bbox = sketch["bbox"]
            xmin = float(bbox["xmin"])
            ymin = float(bbox["ymin"])
            xmax = float(bbox["xmax"])
            ymax = float(bbox["ymax"])
            cx = (xmin + xmax) / 2.0
            cy = (ymin + ymax) / 2.0

            label_lines = [
                record["sketch_id"],
                f"{record['annotation_count']} texts",
            ]
            for item in record["texts"][:MAX_PREVIEW_TEXTS]:
                preview = item["text"].replace("\n", " ").strip()
                if len(preview) > 40:
                    preview = preview[:37] + "..."
                label_lines.append(preview)

            label = "\n".join(label_lines)
            label_y = cy + LABEL_OFFSET_MM

            msp.add_text(
                label,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (cx, label_y),
                },
            )
            msp.add_line(
                (cx, label_y),
                (cx, cy),
                dxfattribs={"layer": DEBUG_LAYER},
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Wrote {}", output_path.resolve())
