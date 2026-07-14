"""
Phase QA.1 — Module 3: Reinforcement Accuracy Validator
Validate correct beam assignment, grouping, and reinforcement count.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from benchmark_models import KPIRecord, safe_pct
from ground_truth_loader import GroundTruth


def _count_bars_from_model(model: Dict[str, Any]) -> Dict[str, int]:
    """Extract role-based bar counts from L.2 model structure."""
    # Prefer bar_count_by_role dict
    by_role = model.get("bar_count_by_role") or {}
    if any(v > 0 for v in by_role.values()):
        return {k: v for k, v in by_role.items()}

    # Fall back to counting role-specific list lengths
    counts: Dict[str, int] = {}
    for role, field in [
        ("TOP_MAIN",              "top_main_bars"),
        ("BOTTOM_MAIN",           "bottom_main_bars"),
        ("TOP_EXTRA",             "top_extra_bars"),
        ("BOTTOM_EXTRA",          "bottom_extra_bars"),
        ("STIRRUP",               "stirrups"),
        ("SIDE_FACE_REINFORCEMENT","side_face_reinforcement"),
    ]:
        lst = model.get(field, [])
        counts[role] = len(lst) if isinstance(lst, list) else (1 if lst else 0)
    return counts


class ReinforcementAccuracyValidator:
    """Compares expected vs predicted bar counts per beam."""

    def validate(
        self,
        ground_truth: GroundTruth,
        l2_models_by_beam: Dict[str, Any],
        l22_extended_by_beam: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        beam_results: List[Dict[str, Any]] = []
        total_correct = 0
        total_incorrect = 0
        total_missing = 0
        total_extra = 0
        total_expected = 0
        total_detected = 0

        for beam_id in ground_truth.expected_beam_ids:
            gt_entry = ground_truth.expected_bars_for_beam(beam_id)
            if gt_entry is None:
                continue

            expected_total = gt_entry.get("total", 0)
            is_recovered = gt_entry.get("recovered", False)

            # Skip recovered beams from strict count comparison
            if is_recovered:
                beam_results.append({
                    "beam_id": beam_id,
                    "expected_total": expected_total,
                    "detected_total": 0,
                    "role_correct": 0,
                    "missing": 0,
                    "extra": 0,
                    "beam_match": True,  # recovered beams not penalized
                    "recovered": True,
                })
                continue

            # Get model data
            model = None
            if l22_extended_by_beam:
                model = l22_extended_by_beam.get(beam_id)
            if model is None:
                model = l2_models_by_beam.get(beam_id)

            if model is None:
                beam_results.append({
                    "beam_id": beam_id,
                    "expected_total": expected_total,
                    "detected_total": 0,
                    "role_correct": 0,
                    "missing": expected_total,
                    "extra": 0,
                    "beam_match": False,
                    "recovered": False,
                })
                total_missing += expected_total
                total_expected += expected_total
                continue

            by_role = _count_bars_from_model(model)
            detected_total = sum(by_role.values())

            role_correct = 0
            role_missing = 0
            role_extra = 0

            for role in ["TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA",
                         "STIRRUP", "SIDE_FACE_REINFORCEMENT"]:
                exp = gt_entry.get(role, 0)
                det = by_role.get(role, 0)
                matched = min(exp, det)
                role_correct += matched
                role_missing += max(0, exp - det)
                role_extra += max(0, det - exp)

            beam_match = (role_missing == 0 and role_extra == 0)

            beam_results.append({
                "beam_id": beam_id,
                "expected_total": expected_total,
                "detected_total": detected_total,
                "role_correct": role_correct,
                "missing": role_missing,
                "extra": role_extra,
                "beam_match": beam_match,
                "recovered": False,
            })

            total_correct += role_correct
            total_missing += role_missing
            total_extra += role_extra
            total_expected += expected_total
            total_detected += detected_total

        total_incorrect = total_missing + total_extra
        accuracy = safe_pct(total_correct, total_expected)

        kpi = KPIRecord(
            kpi_name="Beam Assignment Accuracy",
            expected=float(total_expected),
            detected=float(total_detected),
            correct=float(total_correct),
            accuracy_pct=accuracy,
            status="OK" if accuracy is not None else "NOT_AVAILABLE",
            notes=f"Missing bars: {total_missing}  Extra bars: {total_extra}  (Recovered beams excluded)",
        )

        return {
            "kpi": kpi,
            "beam_results": beam_results,
            "total_expected": total_expected,
            "total_detected": total_detected,
            "total_correct": total_correct,
            "total_missing": total_missing,
            "total_extra": total_extra,
            "total_incorrect": total_incorrect,
            "accuracy_pct": accuracy,
        }
