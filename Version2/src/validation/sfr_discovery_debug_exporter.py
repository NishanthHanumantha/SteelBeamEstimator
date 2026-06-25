"""Phase D.1.7G — DXF debug overlay for SFR discovery audit."""

from pathlib import Path
from typing import Any, List

import ezdxf
from loguru import logger

DEBUG_LAYER = "DEBUG_SFR_DISCOVERY"
TEXT_HEIGHT_MM = 260.0
MARKER_RADIUS_MM = 110.0
LABEL_OFFSET_MM = 300.0

_COLOR_PARSER_READY = 3
_COLOR_FOUND_REJECTED = 2
_COLOR_EXPECTED_MISSING = 1
_COLOR_DEFAULT = 5


class SfrDiscoveryDebugExporter:
    """Visualise discovered SFR entities and expected-beam status."""

    def export(
        self,
        inventory: List[dict[str, Any]],
        expected_vs_found: List[dict[str, Any]],
        engineering_d17f_path: Path,
        output_path: Path,
    ) -> None:
        parser_ready_keys = self._parser_ready_keys(engineering_d17f_path)
        missing_beams = {
            row["beam_mark"] for row in expected_vs_found if not row.get("parser_ready")
        }

        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for item in inventory:
            ax = float(item["x"])
            ay = float(item["y"])
            key = (
                str(item["clean_text"]),
                round(ax, 1),
                round(ay, 1),
            )
            nearest = str(item.get("nearest_beam", ""))

            if key in parser_ready_keys:
                color = _COLOR_PARSER_READY
                status = "PARSER_READY"
            elif nearest in missing_beams and item.get("is_sfr_text"):
                color = _COLOR_EXPECTED_MISSING
                status = "EXPECTED_MISSING"
            else:
                color = _COLOR_FOUND_REJECTED
                status = "FOUND_REJECTED"

            nearest_sketch = item.get("nearest_sketch") or {}
            label = (
                f"[{status}]\n"
                f"{nearest} {nearest_sketch.get('sketch_id', '')}\n"
                f"own={item.get('inside_ownership_region')}\n"
                f"bbox={item.get('inside_sketch_bbox')}\n"
                f"{item['clean_text'][:36]}"
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
            "SFR discovery debug DXF: {} markers -> {}",
            len(inventory),
            output_path.resolve(),
        )

    @staticmethod
    def _parser_ready_keys(engineering_path: Path) -> set[tuple[str, float, float]]:
        if not engineering_path.exists():
            return set()
        import json

        with engineering_path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        keys: set[tuple[str, float, float]] = set()
        if not isinstance(data, list):
            return keys
        for sketch_record in data:
            for ann in sketch_record.get("annotations", []):
                if str(ann.get("annotation_type")) != "SIDE_FACE_REINF":
                    continue
                if str(ann.get("final_status")) != "PARSER_READY":
                    continue
                keys.add(
                    (
                        str(ann["clean_text"]),
                        round(float(ann["x"]), 1),
                        round(float(ann["y"]), 1),
                    )
                )
        return keys
