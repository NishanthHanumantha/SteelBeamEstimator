"""Steel weight summary — Phase I.11."""

from __future__ import annotations

from collections import Counter
from typing import Any, List

from src.engineering_calculations.steel_weight.steel_weight_types import CREATED_PHASE, SteelWeightState


class SteelWeightSummary:
    """Build project-level steel weight summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        weight_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        calculated = [
            item for item in weight_records
            if item.get("status") == SteelWeightState.CALCULATED.value
        ]
        weights = [
            float(item.get("weight_kg") or 0.0)
            for item in calculated
            if item.get("weight_kg") is not None
        ]
        beam_dist = Counter(
            str(item.get("beam_id"))
            for item in calculated
            if item.get("beam_id")
        )
        beam_weight = Counter()
        for item in calculated:
            beam_id = str(item.get("beam_id", ""))
            if beam_id:
                beam_weight[beam_id] += float(item.get("weight_kg") or 0.0)

        diameter_dist = Counter(
            str(item.get("diameter"))
            for item in calculated
            if item.get("diameter") is not None
        )
        diameter_weight = Counter()
        for item in calculated:
            diameter = str(item.get("diameter", ""))
            if diameter:
                diameter_weight[diameter] += float(item.get("weight_kg") or 0.0)

        role_dist = Counter(
            str(item.get("role"))
            for item in calculated
            if item.get("role")
        )
        role_weight = Counter()
        for item in calculated:
            role = str(item.get("role", ""))
            if role:
                role_weight[role] += float(item.get("weight_kg") or 0.0)

        shape_dist = Counter(
            str(item.get("shape_code"))
            for item in calculated
            if item.get("shape_code")
        )
        shape_weight = Counter()
        for item in calculated:
            shape = str(item.get("shape_code", ""))
            if shape:
                shape_weight[shape] += float(item.get("weight_kg") or 0.0)

        fab_state_dist = Counter(
            str(item.get("fabrication_state"))
            for item in calculated
            if item.get("fabrication_state")
        )
        fab_mark_dist = Counter(
            str(item.get("fabrication_mark"))
            for item in calculated
            if item.get("fabrication_mark")
        )

        largest = max(calculated, key=lambda item: float(item.get("weight_kg") or 0.0), default=None)

        return {
            "phase": "Phase I.11",
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "weight_records": len(weight_records),
            "calculated": len(calculated),
            "deferred": sum(
                1 for item in weight_records
                if item.get("status") == SteelWeightState.DEFERRED.value
            ),
            "blocked": sum(
                1 for item in weight_records
                if item.get("status") == SteelWeightState.BLOCKED.value
            ),
            "failed": sum(
                1 for item in weight_records
                if item.get("status") == SteelWeightState.FAILED.value
            ),
            "total_steel_weight_kg": round(sum(weights), 3),
            "weight_by_beam": {key: round(value, 3) for key, value in sorted(beam_weight.items())},
            "weight_by_diameter": {
                key: round(value, 3)
                for key, value in sorted(diameter_weight.items(), key=lambda kv: float(kv[0]))
            },
            "weight_by_role": {key: round(value, 3) for key, value in sorted(role_weight.items())},
            "weight_by_shape": {key: round(value, 3) for key, value in sorted(shape_weight.items())},
            "weight_by_fabrication_state": {
                key: round(
                    sum(
                        float(item.get("weight_kg") or 0.0)
                        for item in calculated
                        if str(item.get("fabrication_state", "")) == key
                    ),
                    3,
                )
                for key in fab_state_dist
            },
            "weight_by_fabrication_mark": {
                key: round(
                    sum(
                        float(item.get("weight_kg") or 0.0)
                        for item in calculated
                        if str(item.get("fabrication_mark", "")) == key
                    ),
                    3,
                )
                for key in fab_mark_dist
            },
            "beam_distribution": dict(beam_dist),
            "diameter_distribution": dict(
                sorted(diameter_dist.items(), key=lambda kv: float(kv[0]))
            ),
            "role_distribution": dict(role_dist),
            "shape_distribution": dict(shape_dist),
            "fabrication_state_distribution": dict(fab_state_dist),
            "fabrication_mark_distribution": dict(fab_mark_dist),
            "largest_bar": largest,
            "average_bar_weight_kg": round(sum(weights) / len(weights), 3) if weights else 0.0,
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
