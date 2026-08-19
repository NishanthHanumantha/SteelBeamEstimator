"""Offline evaluation of shadow arbitration. Evaluation-only; not imported by the arbitrator."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseP266_semantic_longitudinal_resolver.control_cases import SEPARABILITY_TRIPLE

from .config import (
    ALLOWED_FINAL,
    ARB_DET_OVERRIDES,
    CONFLICT_NONE,
    CONFLICT_SEM_DUP_PHYS_DIST,
    PRODUCTION_ACTION,
    SHADOW_ONLY,
)


def _row(records: List[Dict[str, Any]], set_key: str, beam_id: str) -> Dict[str, Any]:
    for rec in records:
        if rec.get("set_key") == set_key and rec.get("beam_id") == beam_id:
            return rec
    return {}


def evaluate_controls(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    cases = {}
    for set_key, beam_id in SEPARABILITY_TRIPLE:
        rec = _row(records, set_key, beam_id)
        cases[f"{set_key}/{beam_id}"] = {
            "deterministic": rec.get("deterministic_result"),
            "semantic": rec.get("semantic_result"),
            "resolved_layer": rec.get("resolved_layer"),
            "conflict_type": rec.get("conflict_type"),
            "arbitration_result": rec.get("arbitration_result"),
            "confidence": rec.get("confidence"),
            "production_action": rec.get("production_action"),
            "shadow_only": rec.get("shadow_only"),
            "winning_evidence_source": rec.get("winning_evidence_source"),
            "reason_codes": rec.get("reason_codes"),
        }
    b128 = cases.get("Fifth/B128") or {}
    b141 = cases.get("Fourth/B141") or {}
    b128_ok = (
        b128.get("conflict_type") == CONFLICT_SEM_DUP_PHYS_DIST
        and b128.get("arbitration_result") == ARB_DET_OVERRIDES
        and b128.get("production_action") == PRODUCTION_ACTION
        and b128.get("shadow_only") is True
    )
    b141_ok = (
        b141.get("production_action") == PRODUCTION_ACTION
        and b141.get("shadow_only") is True
        and b141.get("conflict_type") != CONFLICT_SEM_DUP_PHYS_DIST
    )
    return {
        "cases": cases,
        "b128_physical_distinct_protected": b128_ok,
        "b141_not_overclassified": b141_ok,
    }


def classify_phase(
    *,
    controls: Dict[str, Any],
    fingerprints_ok: bool,
    production_mutation: int,
    tests_ok: bool,
    all_shadow: bool,
    all_no_change: bool,
) -> Dict[str, str]:
    if not tests_ok:
        return {
            "decision": "IMPLEMENTATION_FAILED",
            "strength": "FAILED",
            "note": "P2.6.8 unit tests failed.",
        }
    if production_mutation or not fingerprints_ok:
        return {
            "decision": "UNSAFE_SHADOW_DIAGNOSTIC",
            "strength": "PRODUCTION_MUTATION",
            "note": "Fingerprint or production mutation detected.",
        }
    if not all_shadow or not all_no_change:
        return {
            "decision": "UNSAFE_SHADOW_DIAGNOSTIC",
            "strength": "PRODUCTION_LEAK",
            "note": "A shadow result was not NO_CHANGE / shadow_only.",
        }
    if not controls.get("b128_physical_distinct_protected"):
        return {
            "decision": "UNSAFE_SHADOW_DIAGNOSTIC",
            "strength": "TRUE_RECOVERY_UNPROTECTED",
            "note": "Fifth/B128 was not classified as semantic-duplicate vs physical-distinct with deterministic override.",
        }
    if not controls.get("b141_not_overclassified"):
        return {
            "decision": "UNSAFE_SHADOW_DIAGNOSTIC",
            "strength": "OVERCLASSIFIED_EQUIVALENCE",
            "note": "Fourth/B141 was over-classified as the B128 conflict mode.",
        }
    return {
        "decision": "SAFE_SHADOW_DIAGNOSTIC",
        "strength": "DIAGNOSTIC",
        "note": "Evidence-conflict arbitration explained the P2.6.7 DISTINCT vs DUPLICATE disagreement without production mutation.",
    }


def production_invariants(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "all_shadow_only": all(r.get("shadow_only") is True for r in records) if records else False,
        "all_no_change": all(r.get("production_action") == PRODUCTION_ACTION for r in records) if records else False,
        "any_production_routing_changed": any(r.get("production_routing_changed") for r in records),
        "count": len(records),
    }


__all__ = ["ALLOWED_FINAL", "classify_phase", "evaluate_controls", "production_invariants"]
