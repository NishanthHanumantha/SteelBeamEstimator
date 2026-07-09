"""Reinforcement category and diameter coverage analysis."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from src.engineering_analysis.coverage_collector import (
    REINFORCEMENT_CATEGORIES,
    STANDARD_DIAMETERS_MM,
    category_for_role,
    round_pct,
)


class ReinforcementCoverageAnalyzer:
    """Analyse reinforcement completeness by category, role, and diameter."""

    def analyze(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        bars = snapshot.get("bars") or []
        beam_schedules = snapshot.get("beam_schedules") or []
        calculated_bar_ids = set(snapshot.get("calculated_bar_ids") or [])
        ready_bar_ids = set(snapshot.get("ready_bar_ids") or [])
        schedule_bar_ids = set(snapshot.get("schedule_bar_ids") or [])

        category_summary = self._category_summary(
            bars,
            calculated_bar_ids,
            ready_bar_ids,
            schedule_bar_ids,
        )
        beam_category_report = self._beam_category_report(bars, snapshot.get("beam_ids") or [])
        bar_type_coverage = self._bar_type_coverage(
            bars,
            calculated_bar_ids,
            schedule_bar_ids,
        )
        diameter_coverage = self._diameter_coverage(
            bars,
            beam_schedules,
            calculated_bar_ids,
            schedule_bar_ids,
        )
        return {
            "categories": category_summary,
            "beam_category_report": beam_category_report,
            "bar_type_coverage": bar_type_coverage,
            "diameter_engineering_coverage": diameter_coverage,
        }

    def _category_summary(
        self,
        bars: List[dict[str, Any]],
        calculated_bar_ids: set[str],
        ready_bar_ids: set[str],
        schedule_bar_ids: set[str],
    ) -> List[dict[str, Any]]:
        found = Counter()
        present = Counter()
        missing = Counter()
        unknown = Counter()
        calculated = Counter()
        written = Counter()

        for category in REINFORCEMENT_CATEGORIES:
            missing[category] = 0
            unknown[category] = 0

        beams_with_category: Dict[str, set[str]] = defaultdict(set)
        for bar in bars:
            category = category_for_role(bar.get("role"))
            bar_id = str(bar.get("bar_id"))
            beam_id = str(bar.get("beam_id"))
            found[category] += 1
            beams_with_category[beam_id].add(category)
            if str(bar.get("status", "")).upper() == "UNKNOWN":
                unknown[category] += 1
            else:
                present[category] += 1
            if bar_id in calculated_bar_ids or bar_id in ready_bar_ids:
                calculated[category] += 1
            if bar_id in schedule_bar_ids:
                written[category] += 1

        summary: List[dict[str, Any]] = []
        for category in REINFORCEMENT_CATEGORIES:
            found_count = found.get(category, 0)
            summary.append(
                {
                    "category": category,
                    "found": found_count,
                    "present": present.get(category, 0),
                    "missing": missing.get(category, 0),
                    "unknown": unknown.get(category, 0),
                    "calculated": calculated.get(category, 0),
                    "written": written.get(category, 0),
                    "coverage_percent": round_pct(present.get(category, 0), found_count)
                    if found_count
                    else 0.0,
                }
            )
        return summary

    def _beam_category_report(
        self,
        bars: List[dict[str, Any]],
        beam_ids: List[str],
    ) -> Dict[str, dict[str, str]]:
        beam_roles: Dict[str, set[str]] = defaultdict(set)
        for bar in bars:
            beam_id = str(bar.get("beam_id"))
            beam_roles[beam_id].add(category_for_role(bar.get("role")))

        report: Dict[str, dict[str, str]] = {}
        for beam_id in beam_ids:
            present_categories = beam_roles.get(beam_id, set())
            category_status = {}
            for category in REINFORCEMENT_CATEGORIES:
                if category in present_categories:
                    category_status[category] = "present"
                else:
                    category_status[category] = "missing"
            report[beam_id] = category_status
        return report

    def _bar_type_coverage(
        self,
        bars: List[dict[str, Any]],
        calculated_bar_ids: set[str],
        schedule_bar_ids: set[str],
    ) -> List[dict[str, Any]]:
        grouped: Dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for bar in bars:
            category = category_for_role(bar.get("role"))
            bar_id = str(bar.get("bar_id"))
            grouped[category]["found"] += 1
            grouped[category]["generated"] += 1
            if bar_id in calculated_bar_ids:
                grouped[category]["calculated"] += 1
            if bar_id in schedule_bar_ids:
                grouped[category]["written"] += 1

        rows: List[dict[str, Any]] = []
        for category in REINFORCEMENT_CATEGORIES:
            counts = grouped.get(category, {})
            found = counts.get("found", 0)
            rows.append(
                {
                    "category": category,
                    "found": found,
                    "generated": counts.get("generated", 0),
                    "calculated": counts.get("calculated", 0),
                    "written": counts.get("written", 0),
                    "coverage_percent": round_pct(counts.get("written", 0), found) if found else 0.0,
                }
            )
        return rows

    def _diameter_coverage(
        self,
        bars: List[dict[str, Any]],
        beam_schedules: List[dict[str, Any]],
        calculated_bar_ids: set[str],
        schedule_bar_ids: set[str],
    ) -> List[dict[str, Any]]:
        found_by_diameter: Counter[int] = Counter()
        calculated_by_diameter: Counter[int] = Counter()
        written_by_diameter: Counter[int] = Counter()
        weight_by_diameter: Counter[float] = Counter()

        for bar in bars:
            diameter = self._normalize_diameter(bar.get("diameter_mm"))
            if diameter is None:
                continue
            bar_id = str(bar.get("bar_id"))
            found_by_diameter[diameter] += 1
            if bar_id in calculated_bar_ids:
                calculated_by_diameter[diameter] += 1

        for schedule in beam_schedules:
            for row in schedule.get("rows") or []:
                diameter = self._normalize_diameter(row.get("diameter_mm"))
                if diameter is None:
                    continue
                written_by_diameter[diameter] += 1
                weight = row.get("steel_weight_kg")
                if isinstance(weight, (int, float)):
                    weight_by_diameter[diameter] += float(weight)

        rows: List[dict[str, Any]] = []
        for diameter in STANDARD_DIAMETERS_MM:
            found = found_by_diameter.get(diameter, 0)
            calculated = calculated_by_diameter.get(diameter, 0)
            written = written_by_diameter.get(diameter, 0)
            rows.append(
                {
                    "diameter_mm": diameter,
                    "found": found,
                    "calculated": calculated,
                    "written": written,
                    "steel_weight_kg": round(weight_by_diameter.get(diameter, 0.0), 3),
                    "coverage_percent": round_pct(written, found) if found else 0.0,
                }
            )
        return rows

    @staticmethod
    def _normalize_diameter(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None
