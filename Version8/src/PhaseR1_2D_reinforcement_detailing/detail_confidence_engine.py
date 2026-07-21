"""Detail confidence engine. MODEL_VERSION: 8.4.0"""
from __future__ import annotations

from typing import Any, Dict, List

from .reinforcement_detail_model import ReinforcementDetail

MODEL_VERSION = "8.4.0"


class DetailConfidenceEngine:
    """Deterministic confidence 0..1 with explanation."""

    def apply(
        self,
        detail: ReinforcementDetail,
        parts: Dict[str, float],
    ) -> ReinforcementDetail:
        intent_c = float(parts.get("intent", detail.intent_confidence) or 0.5)
        support_c = float(parts.get("support", 0.5))
        cont_c = float(parts.get("continuity", 0.5))
        curt_c = float(parts.get("curtailment", 0.5))
        ld_c = float(parts.get("development", 0.5))
        stir_c = float(parts.get("stirrup", 0.7))
        side_c = float(parts.get("side_face", 0.7))

        if detail.role == "STIRRUP":
            overall = (
                0.25 * intent_c
                + 0.35 * stir_c
                + 0.15 * support_c
                + 0.15 * ld_c
                + 0.10 * cont_c
            )
        else:
            overall = (
                0.30 * intent_c
                + 0.20 * support_c
                + 0.15 * cont_c
                + 0.15 * curt_c
                + 0.15 * ld_c
                + 0.05 * side_c
            )

        if detail.validation_flags:
            overall *= max(0.5, 1.0 - 0.04 * len(detail.validation_flags))

        detail.confidence = round(min(1.0, max(0.0, overall)), 4)
        detail.evidence.append(f"confidence={detail.confidence}")
        detail.evidence.append(
            f"parts:intent={intent_c},support={support_c},cont={cont_c},"
            f"curt={curt_c},ld={ld_c},stir={stir_c}"
        )
        return detail

    def distribution(self, details: List[ReinforcementDetail]) -> Dict[str, Any]:
        if not details:
            return {"model_version": MODEL_VERSION, "count": 0}
        vals = [d.confidence for d in details]
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
        }
