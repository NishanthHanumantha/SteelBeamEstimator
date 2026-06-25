"""Phase D.1.7C — DXF debug overlay for integrity audit findings."""

from pathlib import Path
from typing import Any, Dict, List

import ezdxf
from loguru import logger

from src.annotations.engineering_annotation_integrity_auditor import AuditResult

DEBUG_LAYER = "DEBUG_ENGINEERING_INTEGRITY"
TEXT_HEIGHT_MM = 300.0
MARKER_RADIUS_MM = 100.0
LABEL_OFFSET_MM = 280.0


class EngineeringAnnotationIntegrityDebugExporter:
    """Mark integrity audit findings on a debug DXF layer."""

    def export(self, audit_result: AuditResult, output_path: Path) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)
        msp = doc.modelspace()

        markers: List[Dict[str, Any]] = []

        for rec in audit_result["fragments"]:
            if rec["classification"] == "SUSPICIOUS_FRAGMENT":
                markers.append(
                    {
                        "x": rec["x"],
                        "y": rec["y"],
                        "label": f"[FRAGMENT] {rec['fragment_text']}",
                    }
                )

        for rec in audit_result["stirrups"]["records"]:
            if rec["classification"] == "PARTIAL":
                markers.append(
                    {
                        "x": rec["x"],
                        "y": rec["y"],
                        "label": f"[PARTIAL_STIRRUP] {rec['clean_text']}",
                    }
                )
            elif rec["classification"] == "INVALID":
                markers.append(
                    {
                        "x": rec["x"],
                        "y": rec["y"],
                        "label": f"[PARTIAL_STIRRUP] {rec['clean_text']}",
                    }
                )

        for rec in audit_result["anchorage"]["records"]:
            if rec["classification"] == "SUSPICIOUS_ANCHORAGE":
                markers.append(
                    {
                        "x": rec["x"],
                        "y": rec["y"],
                        "label": f"[BAD_ANCHORAGE] {rec['clean_text']}",
                    }
                )

        for rec in audit_result["type_consistency"]["mismatches"]:
            markers.append(
                {
                    "x": rec["x"],
                    "y": rec["y"],
                    "label": (
                        f"[TYPE_MISMATCH] {rec['text']} "
                        f"({rec['assigned_type']} vs {rec['expected_type']})"
                    ),
                }
            )

        for dup in audit_result["duplicates"]:
            if dup["classification"] in (
                "DUPLICATE_OWNERSHIP",
                "DUPLICATE_SKETCH_ENTRY",
            ):
                label = f"[DUPLICATE] {dup['clean_text']}"
                markers.append({"x": dup["x"], "y": dup["y"], "label": label})

        for rec in audit_result["rejected_review"]["false_rejections"]:
            markers.append(
                {
                    "x": rec["x"],
                    "y": rec["y"],
                    "label": f"[FALSE_REJECT] {rec['clean_text']}",
                }
            )

        for marker in markers:
            ax = float(marker["x"])
            ay = float(marker["y"])
            msp.add_circle(
                (ax, ay),
                MARKER_RADIUS_MM,
                dxfattribs={"layer": DEBUG_LAYER},
            )
            msp.add_text(
                marker["label"],
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (ax, ay + LABEL_OFFSET_MM),
                },
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Wrote {} ({} markers)", output_path.resolve(), len(markers))
