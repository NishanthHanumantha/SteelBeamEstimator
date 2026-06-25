"""Phase D.3.3 — shared ownership types and helpers."""

import hashlib
import re
from typing import Any, Dict, List, Literal, Tuple

OwnershipStatus = Literal["OWNED", "AMBIGUOUS", "UNASSIGNED"]
ConfidenceLabel = Literal["HIGH", "MEDIUM", "LOW"]

REGION_MARGIN_MM = 2000.0
SKETCH_MARGIN_MM = 600.0
CELL_MARGIN_MM = 800.0
AMBIGUITY_MARGIN = 8.0
MIN_OWNERSHIP_SCORE = 22.0

WEIGHT_LEADER = 40.0
WEIGHT_SKETCH = 20.0
WEIGHT_REGION = 15.0
WEIGHT_GEOMETRY = 15.0
WEIGHT_DISTANCE = 5.0
WEIGHT_ORIENTATION = 5.0


def annotation_id(ann: dict[str, Any]) -> str:
    payload = (
        f"{ann.get('clean_text')}|{ann.get('x')}|{ann.get('y')}|"
        f"{ann.get('entity_type')}|{ann.get('annotation_type')}"
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def coord_key(clean_text: str, x: float, y: float) -> Tuple[str, float, float]:
    normalized = re.sub(r"\s+", " ", str(clean_text).upper().strip())
    return (normalized, round(x, 1), round(y, 1))


def confidence_label(score: float) -> ConfidenceLabel:
    if score >= 85:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"


def flatten_engineering_records(
    records: List[dict[str, Any]],
) -> List[dict[str, Any]]:
    flat: List[dict[str, Any]] = []
    for record in records:
        sketch_id = str(record.get("sketch_id", ""))
        historical_mark = str(record.get("beam_mark", "")).upper()
        occurrence_id = int(record.get("occurrence_id", 0))
        for ann in record.get("annotations", []):
            entry = dict(ann)
            entry["historical_beam_mark"] = str(
                ann.get("beam_mark", historical_mark)
            ).upper()
            entry["historical_sketch_id"] = str(
                ann.get("sketch_id", sketch_id)
            )
            entry["historical_occurrence_id"] = int(
                ann.get("occurrence_id", occurrence_id)
            )
            entry.setdefault("clean_text", entry.get("text", ""))
            entry["ownership_status"] = "UNASSIGNED"
            entry["annotation_id"] = annotation_id(entry)
            flat.append(entry)
    return flat
