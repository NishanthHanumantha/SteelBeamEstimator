"""Engineering confidence scoring for duplicate suppression legitimacy."""

from __future__ import annotations

from typing import Any, Dict, List

from src.duplicate_legitimacy_audit.duplicate_group_loader import DuplicateLegitimacy, LEGITIMATE_CLASSES, RISK_CLASSES


CONFIDENCE_BANDS = (
    (95, 100, "Very High"),
    (80, 95, "High"),
    (60, 80, "Moderate"),
    (40, 60, "Low"),
    (0, 40, "Insufficient"),
)


class DuplicateConfidenceScorer:
    """Score duplicate legitimacy confidence from engineering evidence."""

    def score_group(
        self,
        classification: dict[str, Any],
        group_context: dict[str, Any],
        graphical: dict[str, Any],
        region: dict[str, Any],
        stationing: dict[str, Any],
        leader: dict[str, Any],
    ) -> dict[str, Any]:
        matrix = group_context.get("comparison_matrix") or {}
        legitimacy = DuplicateLegitimacy(classification.get("legitimacy_class"))

        beam_certainty = self._beam_certainty(matrix)
        association_certainty = self._association_certainty(matrix, leader)
        station_certainty = self._station_certainty(stationing, matrix)
        region_certainty = self._region_certainty(region, matrix)
        leader_certainty = self._leader_certainty(leader)
        engineering_consistency = self._engineering_consistency(matrix, graphical)
        evidence_diversity = self._evidence_diversity(
            classification,
            graphical,
            region,
            stationing,
            leader,
        )

        components = {
            "beam_certainty": beam_certainty,
            "association_certainty": association_certainty,
            "station_certainty": station_certainty,
            "region_certainty": region_certainty,
            "leader_certainty": leader_certainty,
            "engineering_consistency": engineering_consistency,
            "evidence_diversity": evidence_diversity,
        }
        weights = {
            "beam_certainty": 0.15,
            "association_certainty": 0.10,
            "station_certainty": 0.20,
            "region_certainty": 0.15,
            "leader_certainty": 0.10,
            "engineering_consistency": 0.20,
            "evidence_diversity": 0.10,
        }
        raw_score = sum(components[key] * weights[key] for key in components)
        if legitimacy in LEGITIMATE_CLASSES and classification.get("should_suppression_occur"):
            raw_score = min(100.0, raw_score + 5.0)
        if legitimacy in RISK_CLASSES:
            raw_score = max(raw_score, 55.0)
        if legitimacy == DuplicateLegitimacy.INSUFFICIENT_EVIDENCE:
            raw_score = min(raw_score, 45.0)
        if legitimacy == DuplicateLegitimacy.UNKNOWN:
            raw_score = min(raw_score, 35.0)

        confidence_score = round(min(100.0, max(0.0, raw_score)), 2)
        band = self._confidence_band(confidence_score)
        return {
            "group_id": classification.get("group_id"),
            "signature": classification.get("signature"),
            "legitimacy_class": legitimacy.value,
            "confidence_score": confidence_score,
            "confidence_band": band,
            "components": {key: round(value, 2) for key, value in components.items()},
        }

    @staticmethod
    def _confidence_band(score: float) -> str:
        for lower, upper, label in CONFIDENCE_BANDS:
            if lower <= score <= upper or (label == "Very High" and score >= 95):
                return label
        return "Insufficient"

    @staticmethod
    def _beam_certainty(matrix: dict[str, Any]) -> float:
        beam = matrix.get("beam") or {}
        if beam.get("uniform"):
            return 95.0
        return 40.0

    @staticmethod
    def _association_certainty(matrix: dict[str, Any], leader: dict[str, Any]) -> float:
        source = matrix.get("association_source") or {}
        score = 90.0 if source.get("uniform") else 55.0
        if leader.get("association_variant"):
            score -= 15.0
        return max(0.0, score)

    @staticmethod
    def _station_certainty(stationing: dict[str, Any], matrix: dict[str, Any]) -> float:
        station = matrix.get("beam_station") or {}
        if station.get("uniform"):
            return 90.0
        spread = float(stationing.get("station_spread") or 0.0)
        if spread <= 250.0:
            return 70.0
        if spread <= 1000.0:
            return 55.0
        return 35.0

    @staticmethod
    def _region_certainty(region: dict[str, Any], matrix: dict[str, Any]) -> float:
        engineering_region = matrix.get("engineering_region") or {}
        if engineering_region.get("uniform") and not region.get("layer_variant"):
            return 90.0
        if region.get("region_variant"):
            return 65.0
        return 50.0

    @staticmethod
    def _leader_certainty(leader: dict[str, Any]) -> float:
        if leader.get("leader_variant"):
            return 75.0
        unique = leader.get("unique_leaders") or []
        if unique == ["NONE"]:
            return 45.0
        return 85.0

    @staticmethod
    def _engineering_consistency(matrix: dict[str, Any], graphical: dict[str, Any]) -> float:
        uniform_fields = sum(1 for item in matrix.values() if item.get("uniform"))
        total_fields = max(len(matrix), 1)
        ratio = uniform_fields / total_fields
        score = 40.0 + ratio * 60.0
        if graphical.get("all_coordinates_equal"):
            score = min(100.0, score + 10.0)
        return score

    @staticmethod
    def _evidence_diversity(
        classification: dict[str, Any],
        graphical: dict[str, Any],
        region: dict[str, Any],
        stationing: dict[str, Any],
        leader: dict[str, Any],
    ) -> float:
        signals = 0
        if graphical.get("any_coordinates_equal") or graphical.get("all_coordinates_equal"):
            signals += 1
        if region.get("region_variant") or region.get("layer_variant"):
            signals += 1
        if stationing.get("station_variant") or stationing.get("support_variant"):
            signals += 1
        if leader.get("leader_variant") or leader.get("association_variant"):
            signals += 1
        if classification.get("engineering_differences"):
            signals += 1
        if classification.get("engineering_similarities"):
            signals += 1
        return min(100.0, 35.0 + signals * 10.0)
