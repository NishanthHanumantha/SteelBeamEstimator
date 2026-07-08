"""Steel weight impact analysis using production values only."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Set

from src.engineering_recovery_validation.baseline_loader import _is_recovered_bar, _sum_steel


class SteelDeltaAnalyzer:
    """Measure steel contribution from recovered bars."""

    def analyze(self, snapshot: dict[str, Any], baseline_snapshot: dict[str, Any]) -> dict[str, Any]:
        recovery_index = snapshot.get("recovery_index") or {}
        recovered_bar_ids = set(recovery_index.get("recovered_bar_ids") or [])
        registry_by_bar = recovery_index.get("registry_by_bar") or {}

        bars = snapshot.get("bars") or []
        steel_weights = snapshot.get("steel_weights") or []
        steel_by_bar = {str(item.get("bar_id")): item for item in steel_weights if item.get("bar_id")}

        baseline_bars = [bar for bar in bars if not _is_recovered_bar(bar, recovered_bar_ids)]
        recovered_bars = [bar for bar in bars if _is_recovered_bar(bar, recovered_bar_ids)]

        before_summary = _sum_steel([steel_by_bar[str(bar["bar_id"])] for bar in baseline_bars if bar.get("bar_id") in steel_by_bar])
        after_summary = _sum_steel([steel_by_bar[str(bar["bar_id"])] for bar in bars if bar.get("bar_id") in steel_by_bar])
        recovered_summary = _sum_steel(
            [steel_by_bar[str(bar["bar_id"])] for bar in recovered_bars if bar.get("bar_id") in steel_by_bar]
        )

        total_before = before_summary["total_kg"]
        total_after = after_summary["total_kg"]
        recovered_steel = recovered_summary["total_kg"]
        recovered_percent = round((recovered_steel / total_after) * 100, 2) if total_after > 0 else 0.0
        efficiency = round((recovered_steel / max(recovered_steel, 1)) * 100, 2) if recovered_steel > 0 else 0.0
        if total_after == 0 and len(recovered_bars) > 0:
            efficiency = round((len(recovered_bars) / len(bars)) * 100, 2) if bars else 0.0

        contribution_by_beam = self._contribution_by_beam(recovered_bars, steel_by_bar)
        contribution_by_diameter = self._contribution_by_diameter(recovered_bars, steel_by_bar)
        contribution_by_recovery = self._contribution_by_recovery(recovered_bars, steel_by_bar, registry_by_bar)

        return {
            "total_steel_before_kg": total_before,
            "total_steel_after_kg": total_after,
            "recovered_steel_kg": recovered_steel,
            "recovered_percent": recovered_percent,
            "steel_delta_kg": round(total_after - total_before, 3),
            "steel_recovery_efficiency_percent": efficiency,
            "production_note": "Steel weights use production values only; deferred weights reported as zero.",
            "deferred_bars_before": before_summary["deferred_count"],
            "deferred_bars_after": after_summary["deferred_count"],
            "recovered_deferred_bars": recovered_summary["deferred_count"],
            "contribution_by_beam": contribution_by_beam,
            "contribution_by_diameter": contribution_by_diameter,
            "contribution_by_recovery_candidate": contribution_by_recovery,
        }

    @staticmethod
    def _contribution_by_beam(
        recovered_bars: List[dict[str, Any]],
        steel_by_bar: Dict[str, dict[str, Any]],
    ) -> List[dict[str, Any]]:
        beam_totals: Dict[str, float] = {}
        beam_counts: Counter[str] = Counter()
        for bar in recovered_bars:
            beam_id = str(bar.get("beam_id") or "Unknown")
            bar_id = str(bar.get("bar_id") or "")
            weight = steel_by_bar.get(bar_id, {}).get("weight_kg")
            beam_counts[beam_id] += 1
            beam_totals[beam_id] = beam_totals.get(beam_id, 0.0) + (float(weight) if weight is not None else 0.0)
        return [
            {
                "beam_id": beam_id,
                "recovered_bars": beam_counts[beam_id],
                "steel_kg": round(beam_totals.get(beam_id, 0.0), 3),
            }
            for beam_id in sorted(beam_counts)
        ]

    @staticmethod
    def _contribution_by_diameter(
        recovered_bars: List[dict[str, Any]],
        steel_by_bar: Dict[str, dict[str, Any]],
    ) -> List[dict[str, Any]]:
        totals: Dict[int, float] = {}
        counts: Counter[int] = Counter()
        for bar in recovered_bars:
            diameter = int(float(bar.get("diameter_mm") or 0))
            if diameter <= 0:
                continue
            bar_id = str(bar.get("bar_id") or "")
            weight = steel_by_bar.get(bar_id, {}).get("weight_kg")
            counts[diameter] += 1
            totals[diameter] = totals.get(diameter, 0.0) + (float(weight) if weight is not None else 0.0)
        return [
            {
                "diameter_mm": diameter,
                "recovered_bars": counts[diameter],
                "steel_kg": round(totals.get(diameter, 0.0), 3),
            }
            for diameter in sorted(counts)
        ]

    @staticmethod
    def _contribution_by_recovery(
        recovered_bars: List[dict[str, Any]],
        steel_by_bar: Dict[str, dict[str, Any]],
        registry_by_bar: Dict[str, dict[str, Any]],
    ) -> List[dict[str, Any]]:
        rows: List[dict[str, Any]] = []
        for bar in recovered_bars:
            bar_id = str(bar.get("bar_id") or "")
            registry = registry_by_bar.get(bar_id, {})
            weight = steel_by_bar.get(bar_id, {}).get("weight_kg")
            rows.append(
                {
                    "recovery_id": registry.get("recovery_id"),
                    "discovery_id": registry.get("discovery_id"),
                    "bar_id": bar_id,
                    "beam_id": bar.get("beam_id"),
                    "diameter_mm": bar.get("diameter_mm"),
                    "steel_kg": round(float(weight), 3) if weight is not None else 0.0,
                    "weight_status": "DEFERRED" if weight is None else "PRODUCTION",
                }
            )
        return rows
