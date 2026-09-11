"""Aggregate six-beam metrics. Missing ground-truth dimensions become NOT_EVALUABLE."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .config import PRIMARY_FAMILIES

_NOT_EVAL = "NOT_EVALUABLE"


def _ratio(num: int, den: int):
    if den <= 0:
        return _NOT_EVAL
    return round(num / den, 4)


def beam_metrics(comparison: Dict[str, Any], associations: List[Dict[str, Any]]) -> Dict[str, Any]:
    exp_n = int(comparison.get("expected_group_count") or 0)
    det_n = int(comparison.get("detected_group_count") or 0)
    correct = int(comparison.get("correctly_interpreted_groups") or 0)
    err = comparison.get("error_counts") or {}
    assoc_ok = sum(1 for a in associations if a.get("association_status") == "correctly_grouped")
    assoc_n = len(associations)
    return {
        "group_count_accuracy": 1.0 if exp_n == det_n and exp_n > 0 else (0.0 if exp_n > 0 else _NOT_EVAL),
        "layer_classification_accuracy": _ratio(correct, exp_n),
        "role_classification_accuracy": _ratio(correct, exp_n),
        "specification_accuracy": _ratio(correct, exp_n),
        "count_accuracy": _NOT_EVAL if (err.get("WRONG_COUNT") is None and exp_n == 0) else _ratio(max(exp_n - int(err.get("WRONG_COUNT") or 0), 0), exp_n),
        "spatial_extent_accuracy": _NOT_EVAL if "WRONG_ZONE" not in err and "WRONG_EXTENT" not in err else _ratio(max(exp_n - int(err.get("WRONG_ZONE") or 0) - int(err.get("WRONG_EXTENT") or 0), 0), exp_n),
        "annotation_association_accuracy": _ratio(assoc_ok, assoc_n),
        "duplicate_group_error_count": int(err.get("SPLIT_SINGLE_GROUP") or 0),
        "merged_distinct_group_count": len(comparison.get("merged_groups") or []),
        "split_same_group_error_count": len(comparison.get("split_groups") or []),
        "unclassified_group_count": int(err.get("UNKNOWN_GROUP") or 0),
        "overall_group_interpretation_accuracy": _ratio(correct, exp_n),
        "missed_groups": len(comparison.get("missing_groups") or []),
        "spurious_groups": len(comparison.get("spurious_groups") or []),
        "wrong_layer_count": int(err.get("WRONG_LAYER") or 0),
        "wrong_role_count": int(err.get("WRONG_ROLE") or 0),
        "wrong_spec_count": int(err.get("WRONG_SPECIFICATION") or 0),
    }


def aggregate_metrics(beam_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    totals = Counter()
    for row in beam_rows:
        cmp = row.get("comparison") or {}
        totals["expected"] += int(cmp.get("expected_group_count") or 0)
        totals["detected"] += int(cmp.get("detected_group_count") or 0)
        totals["correct"] += int(cmp.get("correctly_interpreted_groups") or 0)
        totals["missed"] += len(cmp.get("missing_groups") or [])
        totals["spurious"] += len(cmp.get("spurious_groups") or [])
        totals["merged"] += len(cmp.get("merged_groups") or [])
        totals["split"] += len(cmp.get("split_groups") or [])
        err = cmp.get("error_counts") or {}
        totals["wrong_layer"] += int(err.get("WRONG_LAYER") or 0)
        totals["wrong_role"] += int(err.get("WRONG_ROLE") or 0)
        totals["wrong_spec"] += int(err.get("WRONG_SPECIFICATION") or 0)
        for code, n in err.items():
            totals[f"err_{code}"] += int(n)
    return {
        "total_expected_groups": totals["expected"],
        "total_detected_groups": totals["detected"],
        "correctly_interpreted_groups": totals["correct"],
        "missed_groups": totals["missed"],
        "spurious_groups": totals["spurious"],
        "merged_distinct_groups": totals["merged"],
        "split_groups": totals["split"],
        "wrong_layer_count": totals["wrong_layer"],
        "wrong_role_count": totals["wrong_role"],
        "wrong_spec_count": totals["wrong_spec"],
        "error_taxonomy": {k[4:]: v for k, v in totals.items() if k.startswith("err_")},
        "overall_group_interpretation_accuracy": _ratio(totals["correct"], totals["expected"]),
        "primary_families": list(PRIMARY_FAMILIES),
    }


__all__ = ["aggregate_metrics", "beam_metrics"]
