"""Phase D.1.7D — DXF debug overlay for finalized engineering dataset."""

from pathlib import Path
from typing import Any, Dict, List

import ezdxf
from loguru import logger

from src.annotations.engineering_dataset_finalizer import SketchFinalRecord

DEBUG_LAYER = "DEBUG_ENGINEERING_FINAL"
TEXT_HEIGHT_MM = 300.0
MARKER_RADIUS_MM = 100.0
LABEL_OFFSET_MM = 280.0

_STATUS_LABEL = {
    "PARSER_READY": "[PARSER_READY]",
    "IGNORED_FRAGMENT": "[IGNORED_FRAGMENT]",
    "DEDUPLICATED": "[DEDUPED]",
}


class EngineeringDatasetDebugExporter:
    """Mark finalized annotations by final_status on a debug DXF layer."""

    def export(
        self,
        final_records: List[SketchFinalRecord],
        deduplicated_entries: List[dict[str, Any]],
        fragment_resolutions: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()
        count = 0

        for record in final_records:
            for item in record["annotations"]:
                self._add_marker(msp, item)
                count += 1

        for item in deduplicated_entries:
            self._add_marker(msp, item)
            count += 1

        for res in fragment_resolutions:
            marker: Dict[str, Any] = {
                "x": res["x"],
                "y": res["y"],
                "clean_text": res["clean_text"],
                "final_status": "IGNORED_FRAGMENT",
            }
            self._add_marker(msp, marker, label_suffix=" (rejected)")
            count += 1

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Wrote {} ({} markers)", output_path.resolve(), count)

    def _add_marker(
        self,
        msp: Any,
        item: dict[str, Any],
        label_suffix: str = "",
    ) -> None:
        ax = float(item["x"])
        ay = float(item["y"])
        status = str(item.get("final_status", "PARSER_READY"))
        prefix = _STATUS_LABEL.get(status, f"[{status}]")
        text = item.get("clean_text", "")
        label = f"{prefix} {text}{label_suffix}"

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
