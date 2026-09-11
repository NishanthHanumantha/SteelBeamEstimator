"""Per-beam and aggregate diagnostics."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .config import STATUS_LIMITED, STATUS_NOT_READY, STATUS_READY, STATUS_REVIEW


def gate_population_counts(gates: List[Dict[str, Any]]) -> Dict[str, int]:
    c = Counter(g.get("status") for g in gates)
    return {
        "total": len(gates),
        STATUS_READY: int(c.get(STATUS_READY, 0)),
        STATUS_LIMITED: int(c.get(STATUS_LIMITED, 0)),
        STATUS_REVIEW: int(c.get(STATUS_REVIEW, 0)),
        STATUS_NOT_READY: int(c.get(STATUS_NOT_READY, 0)),
    }


def call_quality_counts(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    attempted = [r for r in results if r.get("called")]
    success = [r for r in attempted if (r.get("audit") or {}).get("success")]
    usable = [r for r in attempted if (r.get("parsed") or {}).get("usable")]
    unusable = [r for r in attempted if not (r.get("parsed") or {}).get("usable")]
    skipped = [r for r in results if not r.get("called")]
    confs = []
    for r in usable:
        for g in (r.get("parsed") or {}).get("reinforcement_groups") or []:
            try:
                confs.append(float(g.get("confidence")))
            except (TypeError, ValueError):
                pass
    return {
        "attempted": len(attempted),
        "api_success": len(success),
        "schema_valid_usable": len(usable),
        "unusable": len(unusable),
        "skipped": len(skipped),
        "average_group_confidence": (sum(confs) / len(confs)) if confs else None,
        "skip_reasons": dict(Counter(r.get("skip_reason") for r in skipped if r.get("skip_reason"))),
    }


__all__ = ["call_quality_counts", "gate_population_counts"]
