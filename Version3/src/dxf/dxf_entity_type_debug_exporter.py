"""Phase D.1.6B — DXF debug overlay for entity-type pattern matches."""

from pathlib import Path
from typing import List

import ezdxf
from loguru import logger

from src.dxf.dxf_entity_type_survey import PatternSearchResult

DEBUG_LAYER = "DEBUG_ENTITY_SURVEY"
TEXT_HEIGHT_MM = 350.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 300.0


class DxfEntityTypeDebugExporter:
    """Mark discovered pattern matches from the entity-type survey."""

    def export(
        self,
        pattern_search: List[PatternSearchResult],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        seen: set[tuple[str, str, float, float]] = set()
        for result in pattern_search:
            for match in result["matches"]:
                key = (
                    match["entity_type"],
                    match["text"],
                    match["x"],
                    match["y"],
                )
                if key in seen:
                    continue
                seen.add(key)

                ax = float(match["x"])
                ay = float(match["y"])
                display = match["text"].replace("\\P", "").strip()
                label = f"{match['entity_type']}: {display}"

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
        logger.info("Wrote {} ({} markers)", output_path.resolve(), len(seen))
