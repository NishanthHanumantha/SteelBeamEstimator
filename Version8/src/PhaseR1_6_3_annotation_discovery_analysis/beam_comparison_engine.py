"""
Compare detected vs missing beams — observations only.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Optional, Sequence

from beam_analysis_model import BeamAnalysisRecord, MODEL_VERSION


def _avg(values: Sequence[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return round(mean(nums), 3)


class BeamComparisonEngine:
    def compare(self, records: List[BeamAnalysisRecord], detected_ids: set, missing_ids: set) -> Dict[str, Any]:
        det = [r for r in records if r.inventory.beam_id in detected_ids]
        miss = [r for r in records if r.inventory.beam_id in missing_ids]

        def metrics(group: List[BeamAnalysisRecord]) -> Dict[str, Any]:
            return {
                "beam_count": len(group),
                "average_annotation_count": _avg([r.drawing_evidence.annotation_count for r in group]),
                "average_nearby_texts": _avg([len(r.drawing_evidence.nearby_annotation_texts) for r in group]),
                "average_leader_count": _avg([r.drawing_evidence.leader_count_near_beam for r in group]),
                "average_block_references": None,  # not available in artefacts
                "average_text_distance": _avg([r.drawing_evidence.nearest_annotation_distance for r in group]),
                "average_beam_length_mm": _avg([r.inventory.beam_length_mm for r in group]),
                "average_beam_width_mm": _avg([r.inventory.beam_width_mm for r in group]),
                "average_beam_depth_mm": _avg([r.inventory.beam_depth_mm for r in group]),
                "average_relationship_count": _avg([r.drawing_evidence.relationship_count for r in group]),
                "average_section_reference_count": _avg([len(r.drawing_evidence.section_references) for r in group]),
                "orientation_counts": self._count(group, lambda r: r.inventory.orientation),
                "drawing_counts": self._count(group, lambda r: r.inventory.drawing_name or "UNKNOWN"),
            }

        return {
            "model_version": MODEL_VERSION,
            "disclaimer": "Comparison statistics only. No causation is asserted.",
            "detected": metrics(det),
            "missing": metrics(miss),
            "delta_detected_minus_missing": self._deltas(metrics(det), metrics(miss)),
        }

    @staticmethod
    def _count(group: List[BeamAnalysisRecord], fn) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for r in group:
            key = str(fn(r) or "UNKNOWN")
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items()))

    @staticmethod
    def _deltas(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, va in a.items():
            vb = b.get(k)
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                out[k] = round(float(va) - float(vb), 3)
            else:
                out[k] = None
        return out
