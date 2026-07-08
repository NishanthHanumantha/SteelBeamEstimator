"""Integrate recovered bars into the production readiness registry."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement_calculation.reinforcement_exporter import ReinforcementExporter


class ReadinessRegistryBuilder:
    """Export readiness registry using existing production exporter."""

    @staticmethod
    def build(bars: List[dict[str, Any]], groups: List[dict[str, Any]]) -> dict[str, Any]:
        payload = ReinforcementExporter.export_readiness(bars, groups)
        ready_count = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state") == "READY"
        )
        deferred_count = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state") == "DEFERRED"
        )
        blocked_count = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state") == "BLOCKED"
        )
        return {
            **payload,
            "ready_bars": ready_count,
            "deferred_bars": deferred_count,
            "blocked_bars": blocked_count,
        }
