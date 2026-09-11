"""
Engineering consistency + confidence engines.
MODEL_VERSION: 8.3.2

Consistency flags issues — never silently changes values.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .engineering_intent_model import (
    EXTENT_FULL_SPAN,
    EXTENT_LEFT_SUPPORT,
    EXTENT_RIGHT_SUPPORT,
    EXTENT_SUPPORT_ZONE,
    ROLE_BOTTOM_MAIN,
    ROLE_STIRRUP,
    ROLE_TOP_MAIN,
    EngineeringIntent,
)

MODEL_VERSION = "8.3.2"


class EngineeringConsistencyEngine:
    """Validate Role × Diameter × Extent consistency; flag only."""

    def validate(self, intents: List[EngineeringIntent]) -> Dict[str, Any]:
        flags: List[Dict[str, Any]] = []
        by_beam: Dict[str, List[EngineeringIntent]] = {}
        for it in intents:
            by_beam.setdefault(it.beam_id, []).append(it)
            it.consistency_flags = []

            if it.role == ROLE_TOP_MAIN and it.layer not in ("TOP", ""):
                msg = "TOP_MAIN_not_on_top_layer"
                it.consistency_flags.append(msg)
                flags.append({"intent_id": it.intent_id, "flag": msg})

            if it.role == ROLE_BOTTOM_MAIN and it.layer not in ("BOTTOM", ""):
                msg = "BOTTOM_MAIN_not_on_bottom_layer"
                it.consistency_flags.append(msg)
                flags.append({"intent_id": it.intent_id, "flag": msg})

            if it.role in (ROLE_TOP_MAIN, ROLE_BOTTOM_MAIN):
                if it.extent in (EXTENT_LEFT_SUPPORT, EXTENT_RIGHT_SUPPORT):
                    msg = "main_role_with_single_support_extent"
                    it.consistency_flags.append(msg)
                    flags.append({"intent_id": it.intent_id, "flag": msg})

            if it.role == ROLE_STIRRUP and it.spacing_mm is None:
                msg = "stirrup_missing_spacing"
                it.consistency_flags.append(msg)
                flags.append({"intent_id": it.intent_id, "flag": msg})

            if it.diameter_mm <= 0:
                msg = "non_positive_diameter"
                it.consistency_flags.append(msg)
                flags.append({"intent_id": it.intent_id, "flag": msg})

        # Per-beam: exactly one TOP_MAIN / BOTTOM_MAIN preferred (by unique label)
        for bid, items in by_beam.items():
            top_mains = {i.bar_label for i in items if i.role == ROLE_TOP_MAIN}
            bot_mains = {i.bar_label for i in items if i.role == ROLE_BOTTOM_MAIN}
            if len(top_mains) > 1:
                flags.append({
                    "beam_id": bid,
                    "flag": "multiple_top_main_identities",
                    "labels": sorted(top_mains),
                })
            if len(bot_mains) > 1:
                flags.append({
                    "beam_id": bid,
                    "flag": "multiple_bottom_main_identities",
                    "labels": sorted(bot_mains),
                })

        return {
            "model_version": MODEL_VERSION,
            "intent_count": len(intents),
            "flag_count": len(flags),
            "flags": flags[:200],
            "flag_histogram": dict(Counter(f.get("flag") for f in flags)),
            "passed": True,  # advisory flags never fail the engine hard-gate
            "note": "Consistency flags are advisory; values are never silently changed.",
        }


class EngineeringIntentConfidenceEngine:
    """Aggregate role/diameter/extent confidence into overall intent confidence."""

    def apply(self, intent: EngineeringIntent) -> EngineeringIntent:
        # Weighted geometric blend
        r, d, e = intent.role_confidence, intent.diameter_confidence, intent.extent_confidence
        overall = 0.45 * r + 0.35 * d + 0.20 * e
        if intent.consistency_flags:
            overall *= max(0.5, 1.0 - 0.05 * len(intent.consistency_flags))
        intent.intent_confidence = round(overall, 4)
        intent.engineering_confidence = intent.intent_confidence
        return intent

    def distribution(self, intents: List[EngineeringIntent]) -> Dict[str, Any]:
        if not intents:
            return {"model_version": MODEL_VERSION, "count": 0}
        vals = [i.intent_confidence for i in intents]
        buckets = {"0.0-0.5": 0, "0.5-0.7": 0, "0.7-0.85": 0, "0.85-1.0": 0}
        for v in vals:
            if v < 0.5:
                buckets["0.0-0.5"] += 1
            elif v < 0.7:
                buckets["0.5-0.7"] += 1
            elif v < 0.85:
                buckets["0.7-0.85"] += 1
            else:
                buckets["0.85-1.0"] += 1
        return {
            "model_version": MODEL_VERSION,
            "count": len(vals),
            "mean": round(sum(vals) / len(vals), 4),
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
            "buckets": buckets,
            "role_mean": round(
                sum(i.role_confidence for i in intents) / len(intents), 4
            ),
            "diameter_mean": round(
                sum(i.diameter_confidence for i in intents) / len(intents), 4
            ),
            "extent_mean": round(
                sum(i.extent_confidence for i in intents) / len(intents), 4
            ),
        }
