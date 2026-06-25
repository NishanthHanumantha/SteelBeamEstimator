"""Phase D.1.7E — DXF debug overlay for SFR ownership validation."""

from pathlib import Path
from typing import List

import ezdxf
from loguru import logger

from src.validation.sfr_ownership_validator import SfrValidationRecord

DEBUG_LAYER = "DEBUG_SFR_VALIDATION"
TEXT_HEIGHT_MM = 280.0
MARKER_RADIUS_MM = 120.0
LABEL_OFFSET_MM = 320.0

_STATUS_COLOR = {
    "VALIDATED": 3,
    "AMBIGUOUS": 2,
    "REJECTED": 1,
}


class SfrOwnershipDebugExporter:
    """Visualise SFR ownership decisions on a debug DXF layer."""

    def export(
        self,
        records: List[SfrValidationRecord],
        sketches: List[dict],
        output_path: Path,
    ) -> None:
        sketch_lookup = {str(s["sketch_id"]): s for s in sketches}

        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for rec in records:
            ax = float(rec["x"])
            ay = float(rec["y"])
            status = str(rec["validator_status"])
            color = _STATUS_COLOR.get(status, 7)
            score = rec["ownership_score"]
            validated = rec.get("validated_beam_mark") or "none"
            candidates = ", ".join(rec.get("candidate_beams", [])[:5])
            scores = ", ".join(str(s) for s in rec.get("candidate_scores", [])[:5])

            label = (
                f"[SFR {status}]\n"
                f"score={score}\n"
                f"win={validated}\n"
                f"cands={candidates}\n"
                f"scores={scores}\n"
                f"{rec['clean_text'][:36]}"
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

            if status == "VALIDATED" and rec.get("validated_sketch_id"):
                sketch = sketch_lookup.get(str(rec["validated_sketch_id"]))
                if sketch:
                    bbox = sketch["bbox"]
                    cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
                    cy = (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0
                    msp.add_line(
                        (ax, ay),
                        (cx, cy),
                        dxfattribs={"layer": DEBUG_LAYER, "color": color},
                    )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info(
            "SFR ownership debug DXF: {} annotations -> {}",
            len(records),
            output_path.resolve(),
        )
