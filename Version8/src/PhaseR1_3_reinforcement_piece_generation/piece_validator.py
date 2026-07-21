"""Piece validation. MODEL_VERSION: 8.5.0"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

MODEL_VERSION = "8.5.0"


class PieceValidator:
    """Validate Detail↔Piece integrity."""

    def validate(
        self, details: List[Any], pieces: List[Any]
    ) -> Dict[str, Any]:
        detail_ids = {d.detail_id for d in details}
        piece_details = {p.detail_id for p in pieces}
        orphan_details = sorted(detail_ids - piece_details)
        orphan_pieces = [p.piece_id for p in pieces if p.detail_id not in detail_ids]

        # Every piece maps to exactly one detail (by construction detail_id)
        multi = []
        by_piece_detail = Counter(p.detail_id for p in pieces)
        # multiple pieces per detail is OK; orphan is not

        flags = []
        for p in pieces:
            if not p.detail_id:
                flags.append({"piece_id": p.piece_id, "flag": "missing_detail_id"})
            if p.cut_length_mm is not None and p.cut_length_mm <= 0:
                flags.append({"piece_id": p.piece_id, "flag": "non_positive_cut_length"})

        return {
            "model_version": MODEL_VERSION,
            "detail_count": len(details),
            "piece_count": len(pieces),
            "orphan_details": orphan_details[:50],
            "orphan_detail_count": len(orphan_details),
            "orphan_pieces": orphan_pieces[:50],
            "orphan_piece_count": len(orphan_pieces),
            "pieces_per_detail_histogram": dict(Counter(by_piece_detail.values())),
            "flag_count": len(flags),
            "flags": flags[:100],
            "passed": len(orphan_details) == 0 and len(orphan_pieces) == 0,
        }
