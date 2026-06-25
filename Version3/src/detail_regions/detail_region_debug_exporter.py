"""Phase D.3.2 — DXF debug overlay for detail regions."""

from pathlib import Path
from typing import Any, Dict, List

import ezdxf
from loguru import logger

DEBUG_LAYER = "DEBUG_DETAIL_REGIONS"
TEXT_HEIGHT_MM = 220.0

_COLOR_VALID = 3
_COLOR_WARNING = 2
_COLOR_INVALID = 1


class DetailRegionDebugExporter:
    """Visualise detail region envelopes with confidence coloring."""

    def export(
        self,
        regions: List[dict[str, Any]],
        region_results: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        score_by_id = {r["region_id"]: r for r in region_results}
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for region in regions:
            result = score_by_id.get(region["region_id"], {})
            status = result.get("status", "VALID")
            label = result.get("confidence_label", "LOW")
            if status == "INVALID_REGION":
                color = _COLOR_INVALID
            elif label == "HIGH":
                color = _COLOR_VALID
            elif label == "MEDIUM":
                color = _COLOR_WARNING
            else:
                color = _COLOR_INVALID

            titles = ", ".join(region.get("beam_titles", []))
            sketch_ids = ", ".join(
                s["sketch_id"] for s in region.get("member_sketches", [])[:6]
            )
            envelope = region["bbox"]
            self._draw_rect(
                msp,
                envelope,
                color,
                (
                    f"{region['region_id']} {result.get('confidence_score', '?')} {label}\n"
                    f"titles={titles}\n"
                    f"sketches={sketch_ids}"
                ),
            )

        doc.saveas(output_path)
        logger.info("Detail region debug DXF -> {}", output_path)

    def _draw_rect(
        self,
        msp: Any,
        bbox: Dict[str, float],
        color: int,
        label: str,
    ) -> None:
        xmin, ymin, xmax, ymax = bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]
        points = [
            (xmin, ymin),
            (xmax, ymin),
            (xmax, ymax),
            (xmin, ymax),
            (xmin, ymin),
        ]
        msp.add_lwpolyline(
            points, dxfattribs={"layer": DEBUG_LAYER, "color": color}, close=True
        )
        msp.add_text(
            label,
            dxfattribs={
                "layer": DEBUG_LAYER,
                "color": color,
                "height": TEXT_HEIGHT_MM,
                "insert": (xmin, ymax + 250),
            },
        )
