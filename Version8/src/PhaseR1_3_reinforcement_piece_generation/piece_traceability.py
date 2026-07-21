"""Piece traceability helpers. MODEL_VERSION: 8.5.0"""
from __future__ import annotations

from typing import Any, Dict, List

MODEL_VERSION = "8.5.0"


class PieceTraceability:
    def build(self, pieces: List[Any]) -> List[Dict[str, Any]]:
        rows = []
        for p in pieces:
            rows.append({
                "piece_id": p.piece_id,
                "detail_id": p.detail_id,
                "intent_id": p.intent_id,
                "beam_id": p.beam_id,
                "piece_type": p.piece_type,
                "annotation_ids": list(p.annotation_ids),
                "geometry_ids": list(p.geometry_ids),
                "relationship_ids": list(p.relationship_ids),
                "fact_ids": list(p.fact_ids),
                "evidence": list(p.evidence),
                "chain": (
                    f"Intent:{p.intent_id} -> Detail:{p.detail_id} -> Piece:{p.piece_id}"
                ),
            })
        return rows
