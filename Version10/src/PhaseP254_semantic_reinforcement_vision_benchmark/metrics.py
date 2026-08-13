"""P2.5.4 metrics — skip fields where ground truth is unavailable."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from .config import (
    CMP_BOTH_AGREE,
    CMP_VISION_CONFLICT,
    CMP_VISION_ONLY_RESOLVED,
    EVAL_APPROPRIATE_ABSTENTION,
    EVAL_EXACT,
    EVAL_HALLUCINATION,
    EVAL_INCORRECT,
    EVAL_PARTIAL,
    STATUS_INSUFFICIENT,
    STATUS_PARTIAL,
    STATUS_RESOLVED,
    TARGET_BEAM_ASSOCIATION_ACCURACY,
    TARGET_HALLUCINATION_MAX,
    TARGET_ROLE_ACCURACY,
    TARGET_SEMANTIC_ACCURACY,
    TARGET_TYPE_ACCURACY,
)

MODEL_VERSION = "10.8.0"


def _rate(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return round(100.0 * num / den, 2)


def _field_accuracy(results: List[Dict[str, Any]], key: str) -> Optional[float]:
    vals = []
    for r in results:
        fs = (r.get("evaluation") or {}).get("field_scores") or {}
        v = fs.get(key)
        if v is not None:
            vals.append(bool(v))
    if not vals:
        return None
    return _rate(sum(1 for x in vals if x), len(vals))


def compute_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(results)
    evals = Counter((r.get("evaluation") or {}).get("evaluation") for r in results)
    api_ok = sum(1 for r in results if (r.get("claude_call") or {}).get("success"))
    valid = sum(1 for r in results if (r.get("validation") or {}).get("valid"))
    resolved = sum(
        1
        for r in results
        if ((r.get("validated_interpretation") or {}).get("interpretation_status") == STATUS_RESOLVED)
    )
    partial = sum(
        1
        for r in results
        if ((r.get("validated_interpretation") or {}).get("interpretation_status") == STATUS_PARTIAL)
    )
    abstain = sum(
        1
        for r in results
        if ((r.get("validated_interpretation") or {}).get("interpretation_status") == STATUS_INSUFFICIENT)
    )
    cmp = Counter((r.get("comparison") or {}).get("class") for r in results)
    gt_ok = sum(1 for r in results if (r.get("ground_truth") or {}).get("available"))

    exact = evals.get(EVAL_EXACT, 0)
    partial_eval = evals.get(EVAL_PARTIAL, 0)
    incorrect = evals.get(EVAL_INCORRECT, 0)
    halluc = evals.get(EVAL_HALLUCINATION, 0)
    approp = evals.get(EVAL_APPROPRIATE_ABSTENTION, 0)

    semantic_den = exact + partial_eval + incorrect + halluc
    semantic_acc = _rate(exact + partial_eval, semantic_den)

    tokens_in = 0
    tokens_out = 0
    for r in results:
        usage = (r.get("claude_call") or {}).get("usage") or {}
        if usage.get("input_tokens") is not None:
            tokens_in += int(usage["input_tokens"])
        if usage.get("output_tokens") is not None:
            tokens_out += int(usage["output_tokens"])

    def cat_metrics(tag: str) -> Dict[str, Any]:
        subset = [
            r
            for r in results
            if tag in (r.get("semantic_class_tags") or []) or r.get("semantic_class") == tag
        ]
        if not subset:
            return {"n": 0, "note": "none_in_benchmark"}
        e = Counter((r.get("evaluation") or {}).get("evaluation") for r in subset)
        den = (
            e.get(EVAL_EXACT, 0)
            + e.get(EVAL_PARTIAL, 0)
            + e.get(EVAL_INCORRECT, 0)
            + e.get(EVAL_HALLUCINATION, 0)
        )
        return {
            "n": len(subset),
            "exact": e.get(EVAL_EXACT, 0),
            "partial": e.get(EVAL_PARTIAL, 0),
            "incorrect": e.get(EVAL_INCORRECT, 0),
            "hallucination": e.get(EVAL_HALLUCINATION, 0),
            "semantic_accuracy": _rate(e.get(EVAL_EXACT, 0) + e.get(EVAL_PARTIAL, 0), den),
            "type_accuracy": _field_accuracy(subset, "type"),
            "role_accuracy": _field_accuracy(subset, "role"),
        }

    return {
        "CLAUDE_CALL_COUNT": n,
        "CLAUDE_SUCCESS_RATE": _rate(api_ok, n) or 0.0,
        "CLAUDE_VALID_RESPONSE_RATE": _rate(valid, n) or 0.0,
        "GROUND_TRUTH_COVERAGE": _rate(gt_ok, n) or 0.0,
        "SEMANTIC_INTERPRETATION_ACCURACY": semantic_acc,
        "TYPE_ACCURACY": _field_accuracy(results, "type"),
        "ROLE_ACCURACY": _field_accuracy(results, "role"),
        "DIAMETER_ACCURACY": _field_accuracy(results, "diameter"),
        "QUANTITY_ACCURACY": _field_accuracy(results, "quantity"),
        "SPACING_ACCURACY": _field_accuracy(results, "spacing"),
        "BEAM_ASSOCIATION_ACCURACY": _field_accuracy(results, "beam_association"),
        "ZONE_ACCURACY": _field_accuracy(results, "zone"),
        "HALLUCINATION_RATE": _rate(halluc, n) or 0.0,
        "APPROPRIATE_ABSTENTION_RATE": _rate(approp, n) or 0.0,
        "VISION_ONLY_RESOLUTION_RATE": _rate(cmp.get(CMP_VISION_ONLY_RESOLVED, 0), n) or 0.0,
        "BOTH_AGREE_RATE": _rate(cmp.get(CMP_BOTH_AGREE, 0), n) or 0.0,
        "VISION_CONFLICT_RATE": _rate(cmp.get(CMP_VISION_CONFLICT, 0), n) or 0.0,
        "counts": {
            "resolved_status": resolved,
            "partial_status": partial,
            "abstained_status": abstain,
            "exact": exact,
            "partial": partial_eval,
            "incorrect": incorrect,
            "hallucination": halluc,
            "appropriate_abstention": approp,
            "api_success": api_ok,
            "valid": valid,
            "vision_only_resolved": cmp.get(CMP_VISION_ONLY_RESOLVED, 0),
            "both_agree": cmp.get(CMP_BOTH_AGREE, 0),
            "vision_conflict": cmp.get(CMP_VISION_CONFLICT, 0),
            "comparison": dict(cmp),
        },
        "category": {
            "LONGITUDINAL": cat_metrics("LONGITUDINAL"),
            "STIRRUP": cat_metrics("STIRRUP"),
            "SIDE_FACE": cat_metrics("SIDE_FACE"),
            "SUPPORT_TOP": cat_metrics("SUPPORT_TOP"),
            "MULTI_ANNOTATION": cat_metrics("MULTI_ANNOTATION"),
            "BEAM_ASSOCIATION": cat_metrics("BEAM_ASSOCIATION"),
            "DIFFICULT_VISUAL": cat_metrics("DIFFICULT_VISUAL"),
            "OCR_CONTROL": cat_metrics("OCR_CONTROL"),
        },
        "token_usage": {
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
        },
        "LOCAL_PLUS_CONTEXT_SUCCESS_RATE": _rate(exact + partial_eval, n),
        "LOCAL_ONLY_SUCCESS_RATE": None,
    }


def decide_recommendation(metrics: Dict[str, Any], *, firewall_ok: bool, regression_ok: bool) -> str:
    if metrics.get("CLAUDE_CALL_COUNT", 0) == 0:
        return "PILOT_BLOCKED"
    if metrics.get("CLAUDE_SUCCESS_RATE", 0) < 50:
        return "PILOT_BLOCKED"
    if not firewall_ok or not regression_ok:
        return "PILOT_BLOCKED"
    sem = metrics.get("SEMANTIC_INTERPRETATION_ACCURACY")
    typ = metrics.get("TYPE_ACCURACY")
    role = metrics.get("ROLE_ACCURACY")
    assoc = metrics.get("BEAM_ASSOCIATION_ACCURACY")
    halluc = metrics.get("HALLUCINATION_RATE") or 0
    vor = metrics.get("VISION_ONLY_RESOLUTION_RATE") or 0
    if sem is None:
        return "MORE_PILOT_REQUIRED"
    if halluc >= 30 and (sem or 0) < 20:
        return "VISION_NOT_EFFECTIVE"
    meets = (
        (sem or 0) >= TARGET_SEMANTIC_ACCURACY
        and (typ or 0) >= TARGET_TYPE_ACCURACY
        and (role is None or role >= TARGET_ROLE_ACCURACY)
        and (assoc is None or assoc >= TARGET_BEAM_ASSOCIATION_ACCURACY)
        and halluc <= TARGET_HALLUCINATION_MAX
        and vor > 0
    )
    if meets:
        return "READY_FOR_SHADOW_INTEGRATION"
    return "MORE_PILOT_REQUIRED"


__all__ = ["compute_metrics", "decide_recommendation"]
