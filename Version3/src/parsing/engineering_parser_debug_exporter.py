"""Phase D.4 — DXF debug overlay for engineering objects."""

from pathlib import Path
from typing import Any, Dict, List

import ezdxf
from loguru import logger

DEBUG_LAYER = "DEBUG_ENGINEERING_OBJECTS"
TEXT_HEIGHT_MM = 180.0

_COLOR_SUCCESS = 3
_COLOR_FAIL = 1
_COLOR_OTHER = 5


class EngineeringParserDebugExporter:
    """Visualise parsed engineering objects."""

    def export(
        self,
        objects: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for obj in objects:
            coords = obj.get("coordinates", {})
            x = float(coords.get("x", 0))
            y = float(coords.get("y", 0))
            status = obj.get("parser_status", "FAILED")
            eng_type = obj.get("engineering_type", "UNKNOWN")
            color = (
                _COLOR_SUCCESS
                if status == "SUCCESS"
                else _COLOR_FAIL
                if status == "FAILED"
                else _COLOR_OTHER
            )

            msp.add_circle(
                (x, y),
                120.0,
                dxfattribs={"layer": DEBUG_LAYER, "color": color},
            )
            leader = obj.get("leader_endpoint")
            if leader:
                msp.add_line(
                    (x, y),
                    (float(leader["x"]), float(leader["y"])),
                    dxfattribs={"layer": DEBUG_LAYER, "color": color},
                )

            label = (
                f"{obj.get('object_id', '')[:8]} {eng_type}\n"
                f"{str(obj.get('clean_text', ''))[:20]}\n"
                f"{obj.get('resolved_beam_mark', '')}"
            )
            msp.add_text(
                label,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "color": color,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (x, y + 250),
                },
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Engineering parser debug DXF -> {}", output_path)
