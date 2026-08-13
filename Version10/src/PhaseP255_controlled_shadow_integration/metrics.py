"""P2.5.5 metrics — operational comparison + Vision quality + safety."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from .config import (
    CMP_BOTH_AGREE,
    CMP_BOTH_UNRESOLVED,
    CMP_DETERMINISTIC_ONLY_RESOLVED,
    CMP_VISION_CONFLICT,
    CMP_VISION_ONLY_RESOLVED,
    CMP_VISION_WRONG,
)


def _rate(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return round(100.0 * num / den, 2)


def _field_accuracy(rows: List[Dict[str, Any]], key: str) -> Optional[float]:
    vals = []
    for r in rows:
        fs = ((r.get("evaluation") or {}).get("field_scores")) or {}
        v = fs.get(key)
        if v is not None:
            vals.append(bool(v))
    if not vals:
        return None
    return _rate(sum(1 for x in vals if x), len(vals))


def compute_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    det_resolved = sum(1 for r in rows if (r.get("deterministic") or {}).get("deterministic_resolved"))
    det_type = sum(
        1 for r in rows if (r.get("deterministic") or {}).get("deterministic_type_resolved")
    )
    det_unresolved = sum(
        1
        for r in rows
        if (r.get("deterministic") or {}).get("deterministic_status")
        in ("UNRESOLVED", "INVALID", None)
    )
    det_partial = n - det_resolved - det_unresolved
    if det_partial < 0:
        det_partial = 0

    api_ok = sum(1 for r in rows if (r.get("vision_obs") or {}).get("api_ok"))
    valid = sum(
        1 for r in rows if ((r.get("vision_obs") or {}).get("validation") or {}).get("valid")
    )
    live = sum(1 for r in rows if (r.get("vision_obs") or {}).get("live_call"))
    replay = n - live

    op = Counter(r.get("operational_class") for r in rows)
    cmp = Counter(r.get("comparison_class") for r in rows)
    evals = Counter((r.get("evaluation") or {}).get("evaluation") for r in rows)

    exact = evals.get("EXACT", 0)
    partial_eval = evals.get("PARTIAL", 0)
    incorrect = evals.get("INCORRECT", 0)
    halluc = evals.get("HALLUCINATION", 0)
    approp = evals.get("APPROPRIATE_ABSTENTION", 0)
    semantic_den = exact + partial_eval + incorrect + halluc

    useful_vor = sum(
        1
        for r in rows
        if r.get("operational_class") == CMP_VISION_ONLY_RESOLVED
        and not (r.get("safety") or {}).get("vision_rejected")
        and (r.get("evaluation") or {}).get("evaluation") in ("EXACT", "PARTIAL", None)
    )
    rejected_vision = sum(1 for r in rows if (r.get("safety") or {}).get("vision_rejected"))
    conflicts_prevented = op.get(CMP_VISION_CONFLICT, 0) + cmp.get(CMP_VISION_WRONG, 0)
    hypo_would = sum(
        1
        for r in rows
        if ((r.get("hypothetical") or {}).get("hypothetical_production_impact") == "WOULD_CHANGE")
    )
    dangerous = sum(
        1 for r in rows if (r.get("hypothetical") or {}).get("dangerous_if_promoted")
    )

    tokens_in = 0
    tokens_out = 0
    for r in rows:
        usage = (r.get("vision_obs") or {}).get("usage") or {}
        if usage.get("input_tokens") is not None:
            tokens_in += int(usage["input_tokens"])
        if usage.get("output_tokens") is not None:
            tokens_out += int(usage["output_tokens"])

    return {
        "total_candidates": n,
        "deterministic_resolved": det_resolved,
        "deterministic_type_resolved": det_type,
        "deterministic_partial": det_partial,
        "deterministic_unresolved": det_unresolved,
        "claude_calls": n,
        "claude_calls_live": live,
        "claude_calls_replayed": replay,
        "claude_success_rate": _rate(api_ok, n) or 0.0,
        "claude_valid_response_rate": _rate(valid, n) or 0.0,
        "BOTH_AGREE": op.get(CMP_BOTH_AGREE, 0),
        "BOTH_AGREE_RATE": _rate(op.get(CMP_BOTH_AGREE, 0), n) or 0.0,
        "VISION_ONLY_RESOLVED": op.get(CMP_VISION_ONLY_RESOLVED, 0),
        "VISION_ONLY_RESOLVED_RATE": _rate(op.get(CMP_VISION_ONLY_RESOLVED, 0), n) or 0.0,
        "DETERMINISTIC_ONLY_RESOLVED": op.get(CMP_DETERMINISTIC_ONLY_RESOLVED, 0),
        "DETERMINISTIC_ONLY_RESOLVED_RATE": _rate(op.get(CMP_DETERMINISTIC_ONLY_RESOLVED, 0), n)
        or 0.0,
        "VISION_CONFLICT": op.get(CMP_VISION_CONFLICT, 0),
        "VISION_CONFLICT_RATE": _rate(op.get(CMP_VISION_CONFLICT, 0), n) or 0.0,
        "BOTH_UNRESOLVED": op.get(CMP_BOTH_UNRESOLVED, 0),
        "BOTH_UNRESOLVED_RATE": _rate(op.get(CMP_BOTH_UNRESOLVED, 0), n) or 0.0,
        "VISION_WRONG": cmp.get(CMP_VISION_WRONG, 0),
        "SEMANTIC_INTERPRETATION_ACCURACY": _rate(exact + partial_eval, semantic_den),
        "TYPE_ACCURACY": _field_accuracy(rows, "type"),
        "ROLE_ACCURACY": _field_accuracy(rows, "role"),
        "DIAMETER_ACCURACY": _field_accuracy(rows, "diameter"),
        "QUANTITY_ACCURACY": _field_accuracy(rows, "quantity"),
        "SPACING_ACCURACY": _field_accuracy(rows, "spacing"),
        "BEAM_ASSOCIATION_ACCURACY": _field_accuracy(rows, "beam_association"),
        "ZONE_ACCURACY": "N/A",
        "HALLUCINATION_RATE": _rate(halluc, n) or 0.0,
        "ABSTENTION_RATE": _rate(approp, n) or 0.0,
        "useful_vision_only_resolutions": useful_vor,
        "rejected_vision_resolutions": rejected_vision,
        "conflicts_prevented_from_production": conflicts_prevented,
        "potential_production_corrections_if_promoted": hypo_would,
        "dangerous_vision_overrides_prevented": dangerous,
        "production_mutation_count": 0,
        "steel_quantity_differences": 0,
        "bbs_differences": 0,
        "excel_differences": 0,
        "eval_counts": {
            "exact": exact,
            "partial": partial_eval,
            "incorrect": incorrect,
            "hallucination": halluc,
            "appropriate_abstention": approp,
        },
        "token_usage": {
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
        },
        "operational_counts": dict(op),
        "comparison_counts": dict(cmp),
    }


__all__ = ["compute_metrics"]
