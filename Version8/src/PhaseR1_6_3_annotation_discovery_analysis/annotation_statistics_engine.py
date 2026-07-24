"""
Project-level annotation statistics and pattern observations.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence

from beam_analysis_model import BeamAnalysisRecord, MODEL_VERSION


def _avg(values: Sequence[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return round(mean(nums), 3)


class AnnotationStatisticsEngine:
    def build(
        self,
        records: List[BeamAnalysisRecord],
        detected_ids: set,
        missing_ids: set,
        dashboard012: Dict[str, Any],
    ) -> Dict[str, Any]:
        n = len(records)
        det = len(detected_ids)
        miss = len(missing_ids)
        coverage = round((det / n) * 100.0, 2) if n else 0.0
        orientations = Counter(r.inventory.orientation for r in records)
        drawings = Counter(r.inventory.drawing_name or "UNKNOWN" for r in records)
        layers = Counter()
        for r in records:
            for layer in r.drawing_evidence.layer_names:
                layers[layer] += 1

        return {
            "model_version": MODEL_VERSION,
            "total_beams": n,
            "detected_beams": det,
            "missing_beams": miss,
            "coverage_pct": coverage,
            "pass_pct": round((det / n) * 100.0, 2) if n else 0.0,
            "fail_pct": round((miss / n) * 100.0, 2) if n else 0.0,
            "rule012_dashboard_ref": {
                "coverage_pct": dashboard012.get("coverage_pct"),
                "total_beams": dashboard012.get("total_beams"),
                "total_stirrup_families": dashboard012.get("total_stirrup_families"),
                "missing_beams": dashboard012.get("missing_beams"),
            },
            "average_annotation_count": _avg([r.drawing_evidence.annotation_count for r in records]),
            "average_text_count": None,
            "average_mtext_count": None,
            "average_blocks": None,
            "average_leaders": _avg([r.drawing_evidence.leader_count_near_beam for r in records]),
            "average_annotation_distance": _avg([r.drawing_evidence.nearest_annotation_distance for r in records]),
            "orientation_distribution": dict(orientations),
            "drawing_distribution": dict(drawings),
            "layer_distribution": dict(layers),
            "notes": [
                "text_entity_count / mtext_count / block_reference_count are Unknown — "
                "not separated in available pipeline artefacts.",
            ],
        }


class PatternAnalysisEngine:
    """Emit observations only; never invent causation."""

    def analyze(self, comparison: Dict[str, Any], records: List[BeamAnalysisRecord], detected_ids: set, missing_ids: set) -> Dict[str, Any]:
        observations: List[str] = []
        det = comparison.get("detected") or {}
        miss = comparison.get("missing") or {}
        delta = comparison.get("delta_detected_minus_missing") or {}

        def obs_avg(label: str, key: str) -> None:
            da, ma = det.get(key), miss.get(key)
            if da is None or ma is None:
                observations.append(f"Observation: {label} unavailable for comparison (artefact gap).")
                return
            observations.append(
                f"Observation: average {label} — detected={da}, missing={ma}, delta(detected-missing)={delta.get(key)}."
            )

        obs_avg("annotation count", "average_annotation_count")
        obs_avg("nearby texts", "average_nearby_texts")
        obs_avg("leader count", "average_leader_count")
        obs_avg("nearest annotation distance", "average_text_distance")
        obs_avg("beam length_mm", "average_beam_length_mm")

        det_drawings = set((det.get("drawing_counts") or {}).keys())
        miss_drawings = set((miss.get("drawing_counts") or {}).keys())
        observations.append(
            f"Observation: detected beams appear on drawings {sorted(det_drawings)}; "
            f"missing beams appear on drawings {sorted(miss_drawings)}."
        )

        det_orient = det.get("orientation_counts") or {}
        miss_orient = miss.get("orientation_counts") or {}
        observations.append(
            f"Observation: orientation counts — detected={det_orient}, missing={miss_orient}."
        )

        # Layer presence
        det_layers = sorted({L for r in records if r.inventory.beam_id in detected_ids for L in r.drawing_evidence.layer_names})
        miss_layers = sorted({L for r in records if r.inventory.beam_id in missing_ids for L in r.drawing_evidence.layer_names})
        if det_layers:
            observations.append(f"Observation: detected beams have nearby leader layers {det_layers}.")
        if miss_layers:
            observations.append(f"Observation: missing beams have nearby leader layers {miss_layers}.")
        if det_layers and miss_layers and set(det_layers) & set(miss_layers):
            observations.append("Observation: detected and missing beams share at least one nearby leader layer.")

        # Deterministic pattern gate: require large, consistent separation on primary metrics
        clear_signals = 0
        for key in ("average_annotation_count", "average_leader_count", "average_text_distance", "average_beam_length_mm"):
            da, ma = det.get(key), miss.get(key)
            if da is None or ma is None or ma == 0:
                continue
            rel = abs(float(da) - float(ma)) / max(abs(float(ma)), 1e-9)
            if rel >= 0.35:
                clear_signals += 1

        if clear_signals == 0:
            pattern_conclusion = "No deterministic engineering pattern identified."
        else:
            pattern_conclusion = (
                "Some numeric differences exist between detected and missing groups; "
                "however, this phase does not assert causation. "
                "Engineering review is required to determine whether any difference is meaningful."
            )

        return {
            "model_version": MODEL_VERSION,
            "observations": observations,
            "pattern_conclusion": pattern_conclusion,
            "clear_signal_metric_count": clear_signals,
            "disclaimer": "Observations only. No engineering conclusions fabricated.",
        }
