"""Phase D.2 — DXF debug overlay for parsed annotations."""

from pathlib import Path
from typing import List

import ezdxf
from loguru import logger

from src.parsing.annotation_parsing_pipeline import ParsedRecord

DEBUG_LAYER = "DEBUG_PARSED_ANNOTATIONS"
TEXT_HEIGHT_MM = 280.0
MARKER_RADIUS_MM = 100.0
LABEL_OFFSET_MM = 280.0

_TYPE_PREFIX = {
    "BAR": "[BAR]",
    "STIRRUP": "[STIRRUP]",
    "ANCHORAGE": "[ANCHORAGE]",
    "SIDE_FACE_REINF": "[SFR]",
}


def _format_label(rec: ParsedRecord) -> str:
    ann_type = str(rec["annotation_type"])
    prefix = _TYPE_PREFIX.get(ann_type, f"[{ann_type}]")
    clean = rec["clean_text"]
    fields = rec.get("parsed_fields", {})

    if ann_type == "BAR":
        detail = f"Q={fields.get('quantity')} D={fields.get('diameter_mm')}"
    elif ann_type == "STIRRUP":
        spacing = fields.get("spacing_mm", [])
        sp = "/".join(str(s) for s in spacing)
        detail = f"L={fields.get('leg_count')} D={fields.get('diameter_mm')} S={sp}"
    elif ann_type == "ANCHORAGE":
        ext = fields.get("extension_db", 0)
        detail = f"EXT={ext}" if ext else "LD"
    elif ann_type == "SIDE_FACE_REINF":
        detail = f"Q={fields.get('quantity')} D={fields.get('diameter_mm')}"
    else:
        detail = ""

    return f"{prefix}\n{clean}\n{detail}"


class AnnotationParsingDebugExporter:
    """Mark successfully parsed annotations on a debug DXF layer."""

    def export(self, parsed_records: List[ParsedRecord], output_path: Path) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        count = 0
        for rec in parsed_records:
            if rec.get("parser_status") != "PARSED":
                continue
            ax = float(rec["x"])
            ay = float(rec["y"])
            label = _format_label(rec)

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
            count += 1

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Wrote {} ({} markers)", output_path.resolve(), count)
