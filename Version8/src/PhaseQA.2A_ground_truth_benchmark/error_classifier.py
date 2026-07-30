"""
error_classifier.py — Classify ground-truth benchmark errors.
MODEL_VERSION: 8.9.1
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List

MODEL_VERSION = "8.9.1"

ERROR_TYPES = (
    "Beam Missing",
    "Beam Mismatch",
    "Missing Bar",
    "Extra Bar",
    "Wrong Diameter",
    "Wrong Quantity",
    "Wrong Role",
    "Steel Difference",
)


class ErrorClassifier:
    def classify(
        self,
        drawing_set: str,
        beam_matching: Dict[str, Any],
        bar_matching: Dict[str, Any],
        steel: Dict[str, Any],
    ) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        beams_affected: set = set()

        for bid in beam_matching.get("missing_ids") or []:
            items.append({
                "error_type": "Beam Missing",
                "drawing_set": drawing_set,
                "beam_id": bid,
                "detail": f"Estimator beam {bid} not found in model",
            })
            beams_affected.add(bid)
        for bid in beam_matching.get("extra_ids") or []:
            items.append({
                "error_type": "Beam Mismatch",
                "drawing_set": drawing_set,
                "beam_id": bid,
                "detail": f"Extra model beam {bid}",
            })
            beams_affected.add(bid)

        status_map = {
            "MISSING": "Missing Bar",
            "EXTRA": "Extra Bar",
            "WRONG_DIAMETER": "Wrong Diameter",
            "WRONG_QUANTITY": "Wrong Quantity",
            "WRONG_ROLE": "Wrong Role",
        }
        for row in bar_matching.get("rows") or []:
            st = row.get("status")
            if st in status_map:
                items.append({
                    "error_type": status_map[st],
                    "drawing_set": drawing_set,
                    "beam_id": row.get("beam_id"),
                    "detail": (
                        f"{row.get('bar_role')} Y{row.get('diameter')} "
                        f"est_qty={row.get('estimator_qty')} model_qty={row.get('model_qty')}"
                    ),
                })
                if row.get("beam_id"):
                    beams_affected.add(row["beam_id"])

        if float(steel.get("difference_pct") or 0) > 2.0:
            items.append({
                "error_type": "Steel Difference",
                "drawing_set": drawing_set,
                "beam_id": "PROJECT",
                "detail": (
                    f"est={steel.get('estimator_total_kg')} kg "
                    f"model={steel.get('model_total_kg')} kg "
                    f"({steel.get('difference_pct')}%)"
                ),
            })

        freq = Counter(i["error_type"] for i in items)
        total = len(items) or 1
        return {
            "model_version": MODEL_VERSION,
            "drawing_set": drawing_set,
            "items": items,
            "frequency": dict(sorted(freq.items(), key=lambda x: -x[1])),
            "percentage": {k: round(100.0 * v / total, 2) for k, v in freq.items()},
            "total_errors": len(items),
            "affected_beams": sorted(beams_affected),
            "affected_beam_count": len(beams_affected),
        }
