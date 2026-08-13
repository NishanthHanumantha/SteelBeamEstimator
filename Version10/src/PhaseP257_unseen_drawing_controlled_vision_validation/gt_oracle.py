"""Independent ground-truth oracle. Never sent to Claude. Never derived from Vision."""
from __future__ import annotations

from typing import Any, Dict

from PhaseP254_semantic_reinforcement_vision_benchmark.benchmark_builder import (
    derive_ground_truth,
)


def ground_truth_for_intent(intent_row: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    """
    Evaluation-only. Uses the P2.5.4 text/OCR/SFR oracle.

    P2.5.1 parse fallback is NOT independent GT and is discarded.
    Longitudinal TOP/BOTTOM role from P2.5.1 is NOT independent GT.
    """
    ocr = "\\X" in (raw_text or "") or "\x00" in (raw_text or "")
    payload = dict(intent_row or {})
    payload["raw_text"] = raw_text
    gt = derive_ground_truth(payload, ocr=ocr)

    if gt.get("source") == "P251_STIRRUP_PARSE":
        gt = {
            "available": False,
            "source": "NONE",
            "semantic_type": None,
            "role": None,
            "quantity": None,
            "diameter_mm": None,
            "legs": None,
            "spacing_mm": [],
            "spacing_pattern": None,
            "beam_association": None,
            "zone": None,
            "normalized_notation": None,
            "fields_available": [],
            "reason": "P251_NOT_INDEPENDENT_GT",
        }

    if gt.get("semantic_type") == "LONGITUDINAL_BAR":
        fields = [f for f in (gt.get("fields_available") or []) if f != "role"]
        gt["fields_available"] = fields
        gt["role"] = None

    gt["sent_to_claude"] = False
    return gt


__all__ = ["ground_truth_for_intent"]
