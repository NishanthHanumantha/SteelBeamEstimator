"""Quantify engineering losses between pipeline stages."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from src.engineering_analysis.coverage_collector import category_for_role, round_pct


class EngineeringLossAnalyzer:
    """Identify and categorize losses between every major pipeline transition."""

    TRANSITIONS: tuple[tuple[str, str, str], ...] = (
        ("normalized_bars", "ready_for_calculation", "Calculation Readiness"),
        ("ready_for_calculation", "calculated_bars", "Engineering Calculations"),
        ("calculated_bars", "bbs_rows_written", "BBS Generation"),
        ("bbs_rows_written", "beam_schedule_rows", "Beam Schedule Aggregation"),
        ("beam_schedule_rows", "excel_rows_written", "Excel Export"),
    )

    def analyze(self, snapshot: dict[str, Any], pipeline: dict[str, Any]) -> dict[str, Any]:
        counts = pipeline.get("stage_counts") or {}
        bars = snapshot.get("bars") or []
        losses: List[dict[str, Any]] = []

        ready_ids = set(snapshot.get("ready_bar_ids") or [])
        calculated_ids = set(snapshot.get("calculated_bar_ids") or [])
        bbs_ids = set(snapshot.get("bbs_bar_ids") or [])
        schedule_ids = set(snapshot.get("schedule_bar_ids") or [])

        transition_reasons = {
            ("normalized_bars", "ready_for_calculation"): self._loss_reasons_not_ready(bars, ready_ids),
            ("ready_for_calculation", "calculated_bars"): self._loss_reasons_not_calculated(bars, ready_ids, calculated_ids),
            ("calculated_bars", "bbs_rows_written"): [{"reason": "BBS export skipped or deferred", "count": max(len(calculated_ids) - len(bbs_ids), 0)}],
            ("bbs_rows_written", "beam_schedule_rows"): [{"reason": "Schedule aggregation incomplete", "count": max(len(bbs_ids) - len(schedule_ids), 0)}],
            ("beam_schedule_rows", "excel_rows_written"): [{"reason": "Excel export skipped", "count": max(counts.get("beam_schedule_rows", 0) - counts.get("excel_rows_written", 0), 0)}],
        }

        for from_stage, to_stage, label in self.TRANSITIONS:
            from_count = counts.get(from_stage, 0)
            to_count = counts.get(to_stage, 0)
            lost = max(from_count - to_count, 0)
            reasons = [item for item in transition_reasons.get((from_stage, to_stage), []) if item["count"] > 0]
            if lost > 0 and not reasons:
                reasons = [{"reason": "Unknown engineering rule", "count": lost}]
            losses.append(
                {
                    "transition": label,
                    "from_stage": from_stage,
                    "to_stage": to_stage,
                    "from_count": from_count,
                    "to_count": to_count,
                    "lost": lost,
                    "loss_percent": round_pct(lost, from_count) if from_count else 0.0,
                    "reasons": reasons,
                }
            )

        return {
            "transitions": losses,
            "total_lost_to_excel": max(counts.get("normalized_bars", 0) - counts.get("excel_rows_written", 0), 0),
        }

    def _loss_reasons_not_ready(
        self,
        bars: List[dict[str, Any]],
        ready_ids: set[str],
    ) -> List[dict[str, Any]]:
        reasons: Counter[str] = Counter()
        for bar in bars:
            bar_id = str(bar.get("bar_id"))
            if bar_id in ready_ids:
                continue
            readiness = bar.get("calculation_readiness") or {}
            reason = str(readiness.get("defer_reason") or readiness.get("calculation_state") or "Unknown")
            reasons[self._normalize_reason(reason)] += 1
        return [{"reason": reason, "count": count} for reason, count in reasons.most_common()]

    def _loss_reasons_not_calculated(
        self,
        bars: List[dict[str, Any]],
        ready_ids: set[str],
        calculated_ids: set[str],
    ) -> List[dict[str, Any]]:
        reasons: Counter[str] = Counter()
        for bar in bars:
            bar_id = str(bar.get("bar_id"))
            if bar_id not in ready_ids or bar_id in calculated_ids:
                continue
            readiness = bar.get("calculation_readiness") or {}
            reason = str(readiness.get("defer_reason") or "Development length unresolved")
            reasons[self._normalize_reason(reason)] += 1
        if not reasons:
            missing = len(ready_ids - calculated_ids)
            if missing:
                reasons["Development length unresolved"] = missing
        return [{"reason": reason, "count": count} for reason, count in reasons.most_common()]

    @staticmethod
    def _normalize_reason(value: str) -> str:
        lowered = value.lower()
        if "partial calculation context" in lowered:
            return "Missing specification"
        if "geometry" in lowered:
            return "Missing geometry"
        if "development length" in lowered:
            return "Development length unresolved"
        if "defer" in lowered or "blocked" in lowered:
            return value.rstrip(".")
        return value or "Unknown engineering rule"
