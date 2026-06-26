"""Phase D.4.1 — DXF debug overlay for reinforcement classification."""

from pathlib import Path
from typing import Any, Dict, List

import ezdxf
from loguru import logger

DEBUG_LAYER = "DEBUG_REINFORCEMENT_CLASSIFICATION"
TEXT_HEIGHT_MM = 180.0

_COLOR_TOP = 3
_COLOR_BOTTOM = 4
_COLOR_OTHER = 5
_COLOR_UNCLASSIFIED = 1


class ReinforcementDebugExporter:
    """Visualise classified reinforcement objects."""

    def export(
        self,
        classified: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for entry in classified:
            coords = entry.get("coordinates") or {}
            x = float(coords.get("x", 0))
            y = float(coords.get("y", 0))
            category = entry.get("estimator_category", "UNCLASSIFIED")
            color = _color_for(entry)

            msp.add_circle(
                (x, y),
                130.0,
                dxfattribs={"layer": DEBUG_LAYER, "color": color},
            )
            leader = entry.get("leader_endpoint")
            if leader:
                msp.add_line(
                    (x, y),
                    (float(leader["x"]), float(leader["y"])),
                    dxfattribs={"layer": DEBUG_LAYER, "color": color},
                )

            label = (
                f"{str(entry.get('object_id', ''))[:8]}\n"
                f"{category}\n"
                f"P={entry.get('position', '-')}"
                f" C={entry.get('continuity', '-')}\n"
                f"{entry.get('resolved_beam_mark', '')}"
            )
            msp.add_text(
                label,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "color": color,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (x, y + 280),
                },
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Reinforcement classification debug DXF -> {}", output_path)


def _color_for(entry: dict[str, Any]) -> int:
    cat = entry.get("estimator_category", "")
    if cat == "UNCLASSIFIED":
        return _COLOR_UNCLASSIFIED
    if cat.startswith("TOP"):
        return _COLOR_TOP
    if cat.startswith("BOTTOM"):
        return _COLOR_BOTTOM
    return _COLOR_OTHER
