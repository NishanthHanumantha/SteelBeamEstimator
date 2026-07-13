"""Validate semantic completeness of the BeamReinforcementModel."""

from __future__ import annotations

from typing import Any, Dict, List

from beam_reinforcement_model import (
    BeamReinforcementModel,
    ROLE_TOP_MAIN, ROLE_BOTTOM_MAIN, ROLE_STIRRUP,
    ROLE_UNKNOWN,
)

BENCHMARK_BEAMS = {"B1", "B2", "B8", "B9", "B10"}


class SemanticValidator:
    """Per-beam semantic validation."""

    def validate_model(self, model: BeamReinforcementModel) -> Dict[str, Any]:
        checks = []

        def _c(name: str, passed: bool, detail: str = "") -> None:
            checks.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})

        all_bars = model.all_bars()
        total = len(all_bars)

        _c("Has at least one bar", total > 0, f"Total bars: {total}")
        _c(
            "No UNKNOWN role bars",
            all(b.semantic_role != ROLE_UNKNOWN for b in all_bars),
            f"Unknown count: {sum(1 for b in all_bars if b.semantic_role == ROLE_UNKNOWN)}",
        )
        _c(
            "TOP_MAIN or TOP_EXTRA present",
            bool(model.top_main_bars or model.top_extra_bars),
            f"TOP_MAIN: {len(model.top_main_bars)}, TOP_EXTRA: {len(model.top_extra_bars)}",
        )
        _c(
            "STIRRUP present",
            bool(model.stirrups),
            f"Stirrups: {len(model.stirrups)}",
        )
        _c(
            "Every bar has classification evidence",
            all(bool(b.classification_evidence) for b in all_bars),
        )
        _c(
            "Total classified matches model count",
            model.total_classified_bars == total,
        )

        # Benchmark-specific checks
        if model.is_benchmark_beam:
            _c(
                "Benchmark: BOTTOM_MAIN present",
                bool(model.bottom_main_bars),
                f"Bottom main count: {len(model.bottom_main_bars)}",
            )
            _c(
                "Benchmark: reference-anchored bars present",
                any(b.is_reference_anchored for b in all_bars),
            )

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "beam_id": model.beam_id,
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }
