"""P2.6.10-B evaluation: completeness readiness and phase status."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import PRODUCTION_ACTION, TARGET_BEAMS


def classify_readiness(records: List[Dict[str, Any]]) -> str:
    if len(records) != TARGET_BEAMS:
        return "FAILED"
    comps = [(r.get("completeness") or {}) for r in records]
    if not all(c.get("complete") for c in comps):
        tops = [c.get("top_reinforcement_visible") for c in comps]
        if any(t == "NO" for t in tops):
            return "INCOMPLETE"
        return "PARTIAL"
    return "READY"


def classify_phase(
    *,
    tests_ok: bool,
    fingerprints_ok: bool,
    six_beams: bool,
    crops_complete: bool,
    readiness: str,
) -> Dict[str, str]:
    if not tests_ok:
        return {"decision": "IMPLEMENTATION_FAILED", "strength": "FAILED", "readiness": "FAILED"}
    if not fingerprints_ok:
        return {"decision": "BENCHMARK_FAILED", "strength": "PRODUCTION_MUTATION", "readiness": "FAILED"}
    if not six_beams or not crops_complete:
        return {"decision": "BENCHMARK_FAILED", "strength": "INCOMPLETE", "readiness": "FAILED"}
    if readiness == "FAILED":
        return {"decision": "SAFE_SHADOW_BENCHMARK", "strength": "DIAGNOSTIC", "readiness": "FAILED"}
    return {
        "decision": "SAFE_SHADOW_BENCHMARK",
        "strength": "DIAGNOSTIC",
        "readiness": readiness,
        "note": "Adaptive detail-crop benchmark completed without production mutation. No Claude Vision.",
    }


def production_invariants(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "all_shadow_only": all(r.get("shadow_only") is True for r in records) if records else False,
        "all_no_change": all(r.get("production_action") == PRODUCTION_ACTION for r in records) if records else False,
        "any_production_routing_changed": any(r.get("production_routing_changed") for r in records),
        "count": len(records),
        "live_vision_invoked": False,
    }


__all__ = ["classify_phase", "classify_readiness", "production_invariants"]
