"""P2.5.6 field-level metrics."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from .config import FIELDS, ST_BOTH_AGREE, ST_VISION_CONFLICT, ST_VISION_FIELD_CANDIDATE


def _rate(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return round(100.0 * num / den, 2)


def compute_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    per_field: Dict[str, Dict[str, Any]] = {}
    vision_only_candidates = 0
    validated_candidates = 0
    rejected_fields = 0
    conflict_fields = 0
    invalid_fields = 0
    accepted_total = 0

    for field in FIELDS:
        det_known = 0
        det_unknown = 0
        vis_known = 0
        vis_unknown = 0
        states: Counter = Counter()
        for r in rows:
            rec = ((r.get("field_result") or {}).get("field_comparisons") or {}).get(field) or {}
            if rec.get("deterministic_known"):
                det_known += 1
            else:
                det_unknown += 1
            if rec.get("vision_known"):
                vis_known += 1
            else:
                vis_unknown += 1
            states[rec.get("field_status") or "UNRESOLVED"] += 1
            if rec.get("field_status") == ST_VISION_FIELD_CANDIDATE:
                vision_only_candidates += 1
                if rec.get("validation_ok") and rec.get("accepted"):
                    validated_candidates += 1
            if rec.get("field_status") == ST_VISION_CONFLICT:
                conflict_fields += 1
            if rec.get("field_status") == "VISION_REJECTED":
                rejected_fields += 1
            if rec.get("vision_known") and rec.get("validation_ok") is False:
                invalid_fields += 1
        per_field[field] = {
            "deterministic_known_count": det_known,
            "deterministic_unknown_count": det_unknown,
            "vision_known_count": vis_known,
            "vision_unknown_count": vis_unknown,
            "BOTH_AGREE": states.get(ST_BOTH_AGREE, 0),
            "VISION_ONLY_CANDIDATE": states.get(ST_VISION_FIELD_CANDIDATE, 0),
            "DETERMINISTIC_ONLY": states.get("VISION_UNRESOLVED", 0) + states.get("DETERMINISTIC_ONLY", 0),
            "CONFLICT": states.get(ST_VISION_CONFLICT, 0),
            "UNRESOLVED": states.get("UNRESOLVED", 0),
            "NOT_APPLICABLE": states.get("NOT_APPLICABLE", 0),
            "VISION_REJECTED": states.get("VISION_REJECTED", 0),
            "states": dict(states),
        }

    for r in rows:
        accepted_total += len((r.get("field_result") or {}).get("accepted_shadow_fields") or [])

    live = sum(1 for r in rows if (r.get("vision_obs") or {}).get("live_call"))
    api_ok = sum(1 for r in rows if (r.get("vision_obs") or {}).get("api_ok"))
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
        "claude_calls": n,
        "claude_calls_live": live,
        "claude_calls_replayed": n - live,
        "claude_success_rate": _rate(api_ok, n) or 0.0,
        "by_field": per_field,
        "accepted_vision_field_candidates": accepted_total,
        "rejected_vision_fields": rejected_fields,
        "conflicting_vision_fields": conflict_fields,
        "validated_vision_fields": validated_candidates,
        "invalid_vision_fields": invalid_fields,
        "total_vision_derived_candidate_fields": vision_only_candidates,
        "validated_candidate_fields": validated_candidates,
        "rejected_candidate_fields": rejected_fields,
        "conflict_fields": conflict_fields,
        "potentially_useful_fields": accepted_total,
        "SAFE_FIELD_CANDIDATE_RATE": _rate(validated_candidates, vision_only_candidates),
        "FIELD_CONFLICT_RATE": _rate(conflict_fields, n * len(FIELDS)),
        "FIELD_REJECTION_RATE": _rate(rejected_fields, n * len(FIELDS)),
        "FIELD_VALIDATION_PASS_RATE": _rate(validated_candidates, vision_only_candidates),
        "production_mutation_count": 0,
        "steel_quantity_differences": 0,
        "bbs_differences": 0,
        "excel_differences": 0,
        "token_usage": {
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
        },
    }


__all__ = ["compute_metrics"]
