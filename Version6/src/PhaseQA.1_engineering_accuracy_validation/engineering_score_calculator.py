"""
Phase QA.1 — Module 9: Engineering Score Calculator
Compute weighted overall engineering score (0–100) and classification.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from benchmark_models import DEFAULT_WEIGHTS, KPIRecord, classify_score


class EngineeringScoreCalculator:
    """Computes weighted engineering score from all KPI records."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self._weights = weights or DEFAULT_WEIGHTS

    def compute(
        self,
        kpi_records: List[KPIRecord],
        extra_kpis: Optional[Dict[str, Optional[float]]] = None,
    ) -> Dict[str, Any]:
        """
        kpi_records  — list of KPIRecord from all validators.
        extra_kpis   — dict with keys matching DEFAULT_WEIGHTS for override.
        Returns dict with weighted_score, classification, kpi_contributions.
        """
        # Build accuracy map from KPIRecord list
        kpi_map: Dict[str, Optional[float]] = {}
        for rec in kpi_records:
            key = self._name_to_key(rec.kpi_name)
            if key:
                kpi_map[key] = rec.accuracy_pct

        if extra_kpis:
            kpi_map.update(extra_kpis)

        contributions: List[Dict[str, Any]] = []
        weighted_sum = 0.0
        total_weight_applied = 0.0

        for kpi_key, weight in self._weights.items():
            accuracy = kpi_map.get(kpi_key)
            if accuracy is None:
                contributions.append({
                    "kpi": kpi_key,
                    "weight_pct": weight,
                    "accuracy_pct": None,
                    "contribution": None,
                    "status": "NOT_AVAILABLE",
                })
            else:
                contribution = accuracy * (weight / 100.0)
                weighted_sum += contribution
                total_weight_applied += weight
                contributions.append({
                    "kpi": kpi_key,
                    "weight_pct": weight,
                    "accuracy_pct": round(accuracy, 4),
                    "contribution": round(contribution, 4),
                    "status": "OK",
                })

        # Normalize to account for missing KPIs
        if 0 < total_weight_applied < 100:
            weighted_score = round(weighted_sum / total_weight_applied * 100, 4)
        elif total_weight_applied >= 100:
            weighted_score = round(weighted_sum, 4)
        else:
            weighted_score = 0.0

        classification = classify_score(weighted_score)
        pass_fail = "PASS" if weighted_score >= 90.0 else ("PARTIAL" if weighted_score >= 75.0 else "FAIL")

        # Overall engineering accuracy (simple mean of available KPIs)
        available = [c["accuracy_pct"] for c in contributions if c["accuracy_pct"] is not None]
        overall_accuracy = round(sum(available) / len(available), 4) if available else 0.0

        return {
            "weighted_score": weighted_score,
            "classification": classification,
            "pass_fail": pass_fail,
            "overall_engineering_accuracy": overall_accuracy,
            "kpi_contributions": contributions,
            "total_weight_applied_pct": round(total_weight_applied, 2),
            "available_kpi_count": len(available),
            "total_kpi_count": len(self._weights),
            "weights_used": self._weights,
        }

    def _name_to_key(self, name: str) -> Optional[str]:
        mapping = {
            "Beam Detection Accuracy": "beam_detection",
            "Beam Assignment Accuracy": "beam_assignment",
            "Geometry Accuracy": "geometry",
            "Feature Accuracy": "feature_extraction",
            "Top/Bottom Classification Accuracy": "top_bottom",
            "Diameter Recognition Accuracy": "diameter",
            "Quantity Recognition Accuracy": "quantity",
            "Pattern Recognition Accuracy": "pattern_recognition",
            "BBS Accuracy": "bbs",
            "Steel Weight Accuracy": "steel_weight",
            "Cut Length Accuracy": "cut_length",
        }
        return mapping.get(name)
