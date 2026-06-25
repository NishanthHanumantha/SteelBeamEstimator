"""Phase D.1.1 — DXF debug overlay for annotation ownership audit."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import ezdxf
from loguru import logger

from src.annotations.annotation_ownership_auditor import AnnotationOwnershipAuditRecord

DEBUG_LAYER = "DEBUG_ANNOTATION_OWNERSHIP"
MARKER_RADIUS_MM = 150.0
TEXT_HEIGHT_MM = 400.0
LABEL_OFFSET_MM = 350.0


class AnnotationOwnershipDebugExporter:
    """Draw annotation points, leader lines to sketch centroids, and audit labels."""

    def export(
        self,
        audit_records: List[AnnotationOwnershipAuditRecord],
        sketches: List[dict[str, Any]],
        output_path: Path,
    ) -> None:
        centroids = self._sketch_centroids(sketches)

        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        for record in audit_records:
            sketch_id = record["sketch_id"]
            centroid = centroids.get(sketch_id)
            if centroid is None:
                continue

            ax = float(record["x"])
            ay = float(record["y"])
            cx, cy = centroid

            msp.add_circle(
                (ax, ay),
                MARKER_RADIUS_MM,
                dxfattribs={"layer": DEBUG_LAYER},
            )
            msp.add_line(
                (ax, ay),
                (cx, cy),
                dxfattribs={"layer": DEBUG_LAYER},
            )

            preview = self._label_annotation(record["annotation"])
            label = f"{preview}\nD={int(record['distance_mm'])}\n{record['confidence']}"
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
        logger.info("Wrote {}", output_path.resolve())

    @staticmethod
    def _sketch_centroids(sketches: List[dict[str, Any]]) -> Dict[str, Tuple[float, float]]:
        centroids: Dict[str, Tuple[float, float]] = {}
        for sketch in sketches:
            bbox = sketch["bbox"]
            cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
            cy = (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0
            centroids[str(sketch["sketch_id"])] = (cx, cy)
        return centroids

    @staticmethod
    def _label_annotation(text: str) -> str:
        cleaned = text.replace("\\P", " ").replace("\n", " ").strip()
        if cleaned.startswith("\\A1;"):
            cleaned = cleaned[4:]
        if len(cleaned) > 24:
            return cleaned[:21] + "..."
        return cleaned
