"""Pilot metrics aggregation for P2.5.3."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .config import (
    EVAL_APPROPRIATE_ABSTENTION,
    EVAL_CONFLICT_DETECTED,
    EVAL_EXACT,
    EVAL_GT_UNAVAILABLE,
    EVAL_HALLUCINATION,
    EVAL_INCORRECT,
    EVAL_PARTIAL,
    STATUS_PARTIAL,
    STATUS_RESOLVED,
)

MODEL_VERSION = "10.7.0"


def compute_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(results) or 1
    evals = Counter((r.get("evaluation") or {}).get("evaluation") for r in results)
    api_ok = sum(1 for r in results if (r.get("claude_call") or {}).get("success"))
    valid = sum(1 for r in results if (r.get("validation") or {}).get("valid"))
    resolved = sum(
        1
        for r in results
        if ((r.get("validated_interpretation") or {}).get("interpretation_status") == STATUS_RESOLVED)
    )
    partial_status = sum(
        1
        for r in results
        if ((r.get("validated_interpretation") or {}).get("interpretation_status") == STATUS_PARTIAL)
    )

    exact = evals.get(EVAL_EXACT, 0)
    partial = evals.get(EVAL_PARTIAL, 0)
    incorrect = evals.get(EVAL_INCORRECT, 0)
    halluc = evals.get(EVAL_HALLUCINATION, 0)
    abstain = evals.get(EVAL_APPROPRIATE_ABSTENTION, 0)
    conflict = evals.get(EVAL_CONFLICT_DETECTED, 0)
    gt_cov = sum(1 for r in results if (r.get("ground_truth") or {}).get("available"))

    def pct(x: int) -> float:
        return round(100.0 * x / n, 2)

    # Category: all current frozen set are OCR stirrups
    ocr = [r for r in results if (r.get("ground_truth") or {}).get("ocr_case")]
    stirrup = [
        r
        for r in results
        if (r.get("ground_truth") or {}).get("reinforcement_type") == "STIRRUP"
    ]

    def cat_rate(subset: List[Dict[str, Any]], key: str) -> float:
        if not subset:
            return 0.0
        hit = sum(1 for r in subset if (r.get("evaluation") or {}).get("evaluation") == key)
        return round(100.0 * hit / len(subset), 2)

    tokens_in = 0
    tokens_out = 0
    for r in results:
        usage = (r.get("claude_call") or {}).get("usage") or {}
        if usage.get("input_tokens") is not None:
            tokens_in += int(usage["input_tokens"])
        if usage.get("output_tokens") is not None:
            tokens_out += int(usage["output_tokens"])

    return {
        "CLAUDE_CALL_COUNT": len(results),
        "CLAUDE_SUCCESS_RATE": pct(api_ok),
        "CLAUDE_VALID_RESPONSE_RATE": pct(valid),
        "VISION_RESOLUTION_RATE": pct(resolved),
        "VISION_PARTIAL_STATUS_RATE": pct(partial_status),
        "VISION_EXACT_INTERPRETATION_RATE": pct(exact),
        "VISION_PARTIAL_INTERPRETATION_RATE": pct(partial),
        "VISION_INCORRECT_RATE": pct(incorrect),
        "VISION_HALLUCINATION_RATE": pct(halluc),
        "VISION_APPROPRIATE_ABSTENTION_RATE": pct(abstain),
        "VISION_CONFLICT_DETECTION_RATE": pct(conflict),
        "GROUND_TRUTH_COVERAGE": pct(gt_cov),
        "LOCAL_PLUS_CONTEXT_SUCCESS_RATE": pct(exact + partial),
        "LOCAL_ONLY_SUCCESS_RATE": None,  # not run in primary mode
        "counts": {
            "exact": exact,
            "partial": partial,
            "incorrect": incorrect,
            "hallucination": halluc,
            "appropriate_abstention": abstain,
            "conflict": conflict,
            "gt_unavailable": evals.get(EVAL_GT_UNAVAILABLE, 0),
            "resolved_status": resolved,
            "partial_status": partial_status,
            "api_success": api_ok,
            "valid": valid,
        },
        "category": {
            "ocr_corruption": {
                "n": len(ocr),
                "exact_rate": cat_rate(ocr, EVAL_EXACT),
                "partial_rate": cat_rate(ocr, EVAL_PARTIAL),
                "incorrect_rate": cat_rate(ocr, EVAL_INCORRECT),
                "hallucination_rate": cat_rate(ocr, EVAL_HALLUCINATION),
            },
            "stirrup": {
                "n": len(stirrup),
                "exact_rate": cat_rate(stirrup, EVAL_EXACT),
                "partial_rate": cat_rate(stirrup, EVAL_PARTIAL),
                "incorrect_rate": cat_rate(stirrup, EVAL_INCORRECT),
                "hallucination_rate": cat_rate(stirrup, EVAL_HALLUCINATION),
            },
            "semantic_context": {"n": 0, "note": "none_in_frozen_active_set"},
            "visually_difficult": {
                "n": sum(
                    1
                    for r in results
                    if r.get("beam_id") in ("B82", "B143", "B144", "B175", "B178")
                ),
                "exact_rate": cat_rate(
                    [
                        r
                        for r in results
                        if r.get("beam_id") in ("B82", "B143", "B144", "B175", "B178")
                    ],
                    EVAL_EXACT,
                ),
            },
        },
        "token_usage": {
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
        },
    }


def decide_recommendation(metrics: Dict[str, Any]) -> str:
    """Pilot decision from actual metrics — not automatic READY."""
    if metrics.get("CLAUDE_CALL_COUNT", 0) == 0:
        return "PILOT_BLOCKED"
    if metrics.get("CLAUDE_SUCCESS_RATE", 0) < 50:
        return "PILOT_BLOCKED"
    exact = metrics.get("VISION_EXACT_INTERPRETATION_RATE", 0)
    halluc = metrics.get("VISION_HALLUCINATION_RATE", 0)
    incorrect = metrics.get("VISION_INCORRECT_RATE", 0)
    if exact >= 70 and halluc <= 10 and incorrect <= 20:
        return "READY_FOR_P2.5.4"
    if exact >= 40 or metrics.get("VISION_PARTIAL_INTERPRETATION_RATE", 0) >= 30:
        return "MORE_PILOT_REQUIRED"
    if exact < 20 and halluc >= 30:
        return "VISION_NOT_EFFECTIVE"
    return "MORE_PILOT_REQUIRED"


__all__ = ["compute_metrics", "decide_recommendation"]
