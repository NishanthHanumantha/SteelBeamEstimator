"""Detail consistency validator — report only, never mutate. MODEL_VERSION: 8.4.0"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .reinforcement_detail_model import ReinforcementDetail

MODEL_VERSION = "8.4.0"
_VALID_HOOKS = {"UNKNOWN", "135_STANDARD", "90_STANDARD"}


class DetailConsistencyValidator:
    """Validate detailing; ONLY report — never mutate."""

    def validate(self, details: List[ReinforcementDetail]) -> Dict[str, Any]:
        flags: List[Dict[str, Any]] = []
        for d in details:
            d.validation_flags = []
            self._check(d, flags)

        # Hard pass if no critical flags (zero spacing, non-positive when required)
        critical = [
            f for f in flags
            if f.get("flag") in {
                "spacing_zero",
                "impossible_main_support_termination",
                "stirrup_missing_spacing",
            }
        ]
        return {
            "model_version": MODEL_VERSION,
            "detail_count": len(details),
            "flag_count": len(flags),
            "critical_count": len(critical),
            "flags": flags[:300],
            "flag_histogram": dict(Counter(f.get("flag") for f in flags)),
            "passed": len(critical) == 0,
            "note": "Validator reports only; values are never mutated.",
        }

    def _check(self, d: ReinforcementDetail, flags: List[Dict[str, Any]]) -> None:
        def flag(code: str) -> None:
            d.validation_flags.append(code)
            flags.append({"detail_id": d.detail_id, "beam_id": d.beam_id, "flag": code})

        if d.role in ("TOP_MAIN", "BOTTOM_MAIN"):
            if d.curtailment_type in ("LEFT_SUPPORT", "RIGHT_SUPPORT") and not (
                d.left_support_zone or d.right_support_zone
            ):
                flag("impossible_main_support_termination")

        if d.support_region == "SUPPORT_ZONE" or d.curtailment_type in (
            "BOTH_SUPPORTS",
            "LEFT_SUPPORT",
            "RIGHT_SUPPORT",
        ):
            if not (d.left_support_zone or d.right_support_zone):
                flag("support_zone_missing_support_evidence")

        if d.extent == "FULL_SPAN" and d.curtailment_type not in (
            "FULL_SPAN",
            "UNKNOWN",
        ):
            # advisory
            flag("full_span_extent_curtailment_mismatch")

        if d.role == "STIRRUP":
            if d.spacing_mm is None and d.stirrup_zone_count == 0:
                flag("stirrup_missing_spacing")
            if d.spacing_mm is not None and d.spacing_mm <= 0:
                flag("spacing_zero")

        if d.development_length_mm is not None and d.development_length_mm <= 0:
            flag("development_length_non_positive")
        if d.development_source == "UNAVAILABLE":
            flag("development_length_unavailable")

        hook = d.hook_type or "UNKNOWN"
        if hook not in _VALID_HOOKS and not hook.startswith("135"):
            flag("hook_type_unrecognized")
