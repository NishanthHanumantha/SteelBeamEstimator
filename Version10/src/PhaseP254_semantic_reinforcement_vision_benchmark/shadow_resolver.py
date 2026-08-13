"""ShadowResolverResult — pilot evidence only. Not a production reinforcement object."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import MODEL_VERSION, PHASE_ID, SCHEMA_VERSION

# Explicit: this type must not be imported by production engineering modules.
SHADOW_OBJECT_KIND = "ShadowResolverResult"
PRODUCTION_WRITE = False


def build_shadow_result(
    *,
    candidate: Dict[str, Any],
    claude_interpretation: Optional[Dict[str, Any]],
    validation: Dict[str, Any],
    conflicts: Dict[str, Any],
    evaluation: Dict[str, Any],
    comparison: Dict[str, Any],
    evidence_fingerprint: str,
    prompt_fingerprint: str,
    usage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "object_kind": SHADOW_OBJECT_KIND,
        "production_write": PRODUCTION_WRITE,
        "engineering_authority": "DETERMINISTIC_ENGINE",
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "beam_id": candidate.get("beam_id"),
        "annotation_id": candidate.get("annotation_id"),
        "claude_interpretation": claude_interpretation,
        "validation": {
            "valid": validation.get("valid"),
            "errors": validation.get("errors") or [],
            "warnings": validation.get("warnings") or [],
        },
        "conflict_flags": conflicts,
        "benchmark_result": evaluation,
        "baseline_comparison": comparison,
        "confidence": (claude_interpretation or {}).get("confidence"),
        "provenance": candidate.get("provenance_ids") or {},
        "evidence_fingerprint": evidence_fingerprint,
        "prompt_fingerprint": prompt_fingerprint,
        "token_usage": usage,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def assert_shadow_not_production(obj: Dict[str, Any]) -> bool:
    return (
        obj.get("object_kind") == SHADOW_OBJECT_KIND
        and obj.get("production_write") is False
        and obj.get("engineering_authority") == "DETERMINISTIC_ENGINE"
    )


__all__ = [
    "SHADOW_OBJECT_KIND",
    "assert_shadow_not_production",
    "build_shadow_result",
]
