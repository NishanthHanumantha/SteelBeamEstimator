"""Piece confidence aggregation. MODEL_VERSION: 8.5.0"""
from __future__ import annotations

from typing import Any, Dict, List

MODEL_VERSION = "8.5.0"


class PieceConfidence:
    def distribution(self, pieces: List[Any]) -> Dict[str, Any]:
        if not pieces:
            return {"model_version": MODEL_VERSION, "count": 0}
        vals = [float(p.confidence) for p in pieces]
        buckets = {"0.0-0.5": 0, "0.5-0.7": 0, "0.7-0.85": 0, "0.85-1.0": 0}
        for v in vals:
            if v < 0.5:
                buckets["0.0-0.5"] += 1
            elif v < 0.7:
                buckets["0.5-0.7"] += 1
            elif v < 0.85:
                buckets["0.7-0.85"] += 1
            else:
                buckets["0.85-1.0"] += 1
        return {
            "model_version": MODEL_VERSION,
            "count": len(vals),
            "mean": round(sum(vals) / len(vals), 4),
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
            "buckets": buckets,
        }
