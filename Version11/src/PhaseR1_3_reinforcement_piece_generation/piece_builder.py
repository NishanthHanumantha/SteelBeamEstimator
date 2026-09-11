"""
PieceBuilder / engine facade.
MODEL_VERSION: 8.5.0
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .piece_confidence import PieceConfidence
from .piece_generator import PieceGenerator
from .piece_model import ReinforcementPiece
from .piece_traceability import PieceTraceability
from .piece_validator import PieceValidator

MODEL_VERSION = "8.5.0"


class PieceBuilder:
    """Public API: Details → Pieces with validation payload."""

    def __init__(
        self,
        v7_root: pathlib.Path,
        engineering_context: Optional[Dict[str, Any]] = None,
    ):
        self._v7 = v7_root
        self._ctx = engineering_context or {}
        self._geometry = self._load_geometry()
        self._generator = PieceGenerator(self._ctx)
        self._validator = PieceValidator()
        self._confidence = PieceConfidence()
        self._trace = PieceTraceability()

    def build(
        self, details: List[Any]
    ) -> Tuple[List[ReinforcementPiece], Dict[str, Any]]:
        pieces = self._generator.generate_for_details(details, self._geometry)
        validation = self._validator.validate(details, pieces)
        conf = self._confidence.distribution(pieces)
        trace = self._trace.build(pieces)
        type_hist = dict(Counter(p.piece_type for p in pieces))
        payload = {
            "model_version": MODEL_VERSION,
            "detail_count": len(details),
            "piece_count": len(pieces),
            "piece_types": type_hist,
            "validation": validation,
            "confidence": conf,
            "traceability": trace,
            "geometry_summary": {
                "with_cut_length": sum(1 for p in pieces if p.cut_length_mm is not None),
                "without_cut_length": sum(1 for p in pieces if p.cut_length_mm is None),
                "beams_with_geometry": len(self._geometry),
            },
            "development_summary": {
                "with_ld": sum(1 for p in pieces if p.development_length_mm is not None),
                "without_ld": sum(1 for p in pieces if p.development_length_mm is None),
            },
        }
        return pieces, payload

    def build_by_beam(
        self, details_by_beam: Dict[str, List[Any]]
    ) -> Tuple[Dict[str, List[ReinforcementPiece]], Dict[str, Any]]:
        flat: List[Any] = []
        for dets in details_by_beam.values():
            flat.extend(dets)
        pieces, payload = self.build(flat)
        by_beam: Dict[str, List[ReinforcementPiece]] = {}
        for p in pieces:
            by_beam.setdefault(p.beam_id, []).append(p)
        return by_beam, payload

    def _load_geometry(self) -> Dict[str, Any]:
        path = (
            self._v7
            / "data/output/PhaseR1_2A_geometry_accuracy"
            / "validated_beam_geometry.json"
        )
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("geometries") or {}
