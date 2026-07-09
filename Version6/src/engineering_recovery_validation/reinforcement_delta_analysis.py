"""Reinforcement category and diameter delta analysis."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Set

from src.engineering_analysis.coverage_collector import REINFORCEMENT_CATEGORIES, ROLE_TO_CATEGORY, STANDARD_DIAMETERS_MM
from src.engineering_recovery_validation.baseline_loader import _is_recovered_bar


def _role_category(bar: dict[str, Any]) -> str:
    role = str(bar.get("role") or "UNKNOWN").upper()
    return ROLE_TO_CATEGORY.get(role, "Other")


class ReinforcementDeltaAnalyzer:
    """Compare reinforcement categories before and after recovery."""

    def analyze(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        recovery_index = snapshot.get("recovery_index") or {}
        recovered_bar_ids = set(recovery_index.get("recovered_bar_ids") or [])
        bars = snapshot.get("bars") or []

        baseline_bars = [bar for bar in bars if not _is_recovered_bar(bar, recovered_bar_ids)]
        category_before = Counter(_role_category(bar) for bar in baseline_bars)
        category_after = Counter(_role_category(bar) for bar in bars)

        categories: List[dict[str, Any]] = []
        for category in REINFORCEMENT_CATEGORIES:
            before = category_before.get(category, 0)
            after = category_after.get(category, 0)
            categories.append(
                {
                    "category": category,
                    "before": before,
                    "after": after,
                    "delta": after - before,
                }
            )

        diameter_analysis = self._diameter_delta(baseline_bars, bars, recovered_bar_ids)
        return {
            "categories": categories,
            "category_summary": {
                item["category"]: {"before": item["before"], "after": item["after"], "delta": item["delta"]}
                for item in categories
                if item["delta"] != 0 or item["after"] > 0
            },
            "diameter_delta": diameter_analysis,
        }

    def _diameter_delta(
        self,
        baseline_bars: List[dict[str, Any]],
        all_bars: List[dict[str, Any]],
        recovered_bar_ids: Set[str],
    ) -> dict[str, Any]:
        def count_by_diameter(items: List[dict[str, Any]]) -> Counter[int]:
            counter: Counter[int] = Counter()
            for bar in items:
                diameter = bar.get("diameter_mm")
                if diameter in (None, 0, 0.0):
                    continue
                counter[int(float(diameter))] += 1
            return counter

        before_counts = count_by_diameter(baseline_bars)
        after_counts = count_by_diameter(all_bars)
        recovered_counts = count_by_diameter(
            [bar for bar in all_bars if _is_recovered_bar(bar, recovered_bar_ids)]
        )

        diameters: List[dict[str, Any]] = []
        for diameter in STANDARD_DIAMETERS_MM:
            before = before_counts.get(diameter, 0)
            after = after_counts.get(diameter, 0)
            recovered = recovered_counts.get(diameter, 0)
            delta = after - before
            contribution_percent = round((recovered / delta) * 100, 2) if delta > 0 else 0.0
            diameters.append(
                {
                    "diameter_mm": diameter,
                    "before": before,
                    "after": after,
                    "delta": delta,
                    "recovered_bars": recovered,
                    "contribution_percent": contribution_percent,
                    "steel_kg_delta": 0.0,
                }
            )

        return {
            "standard_diameters_mm": list(STANDARD_DIAMETERS_MM),
            "diameters": diameters,
            "non_standard_before": dict(before_counts),
            "non_standard_after": dict(after_counts),
        }

    def build_diameter_export(self, reinforcement_delta: dict[str, Any]) -> dict[str, Any]:
        diameter_delta = reinforcement_delta.get("diameter_delta") or {}
        return {
            "diameter_count": len(diameter_delta.get("diameters") or []),
            "diameters": diameter_delta.get("diameters") or [],
            "summary": {
                item["diameter_mm"]: {
                    "before": item["before"],
                    "after": item["after"],
                    "delta": item["delta"],
                    "contribution_percent": item["contribution_percent"],
                }
                for item in diameter_delta.get("diameters") or []
                if item.get("delta") != 0
            },
        }
