"""Per-beam before/after engineering impact analysis."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.engineering_recovery_validation.baseline_loader import _is_recovered_bar, _sum_steel


class BeamDeltaAnalyzer:
    """Generate per-beam comparison reports."""

    def analyze(self, snapshot: dict[str, Any], baseline_snapshot: dict[str, Any]) -> dict[str, Any]:
        recovery_index = snapshot.get("recovery_index") or {}
        recovered_bar_ids = set(recovery_index.get("recovered_bar_ids") or [])
        recovered_object_ids = set(recovery_index.get("recovered_object_ids") or [])

        bars = snapshot.get("bars") or []
        objects = snapshot.get("objects") or []
        steel_weights = snapshot.get("steel_weights") or []
        steel_by_bar = {str(item.get("bar_id")): item for item in steel_weights if item.get("bar_id")}

        beam_ids = sorted(
            {
                str(item.get("beam_id") or item.get("beam") or "")
                for item in bars + objects
                if item.get("beam_id") or item.get("beam")
            }
        )

        beam_reports: List[dict[str, Any]] = []
        for beam_id in beam_ids:
            beam_bars = [bar for bar in bars if str(bar.get("beam_id")) == beam_id]
            baseline_bars = [bar for bar in beam_bars if not _is_recovered_bar(bar, recovered_bar_ids)]
            recovered_bars = [bar for bar in beam_bars if _is_recovered_bar(bar, recovered_bar_ids)]

            beam_objects = [
                obj
                for obj in objects
                if str(obj.get("beam_id") or obj.get("beam_mark") or "") == beam_id
            ]
            baseline_objects = [
                obj
                for obj in beam_objects
                if str(obj.get("engineering_object_id") or obj.get("object_id") or "") not in recovered_object_ids
            ]

            before_steel = _sum_steel([steel_by_bar[str(bar["bar_id"])] for bar in baseline_bars if bar.get("bar_id") in steel_by_bar])
            after_steel = _sum_steel([steel_by_bar[str(bar["bar_id"])] for bar in beam_bars if bar.get("bar_id") in steel_by_bar])

            improvement = {
                "engineering_objects_delta": len(beam_objects) - len(baseline_objects),
                "bars_delta": len(beam_bars) - len(baseline_bars),
                "steel_kg_delta": round(after_steel["total_kg"] - before_steel["total_kg"], 3),
                "recovered_bars_added": len(recovered_bars),
            }

            beam_reports.append(
                {
                    "beam_id": beam_id,
                    "engineering_objects": {
                        "before": len(baseline_objects),
                        "after": len(beam_objects),
                        "delta": improvement["engineering_objects_delta"],
                    },
                    "bars": {
                        "before": len(baseline_bars),
                        "after": len(beam_bars),
                        "delta": improvement["bars_delta"],
                    },
                    "steel_kg": {
                        "before": before_steel["total_kg"],
                        "after": after_steel["total_kg"],
                        "delta": improvement["steel_kg_delta"],
                    },
                    "recovered_bar_ids": [bar.get("bar_id") for bar in recovered_bars],
                    "improvement": improvement,
                }
            )

        improved_beams = [item for item in beam_reports if item["improvement"]["bars_delta"] > 0]
        return {
            "beam_count": len(beam_reports),
            "beams_with_improvement": len(improved_beams),
            "beams": beam_reports,
            "top_improved_beams": sorted(
                improved_beams,
                key=lambda item: (
                    item["improvement"]["bars_delta"],
                    item["improvement"]["engineering_objects_delta"],
                ),
                reverse=True,
            )[:5],
        }
