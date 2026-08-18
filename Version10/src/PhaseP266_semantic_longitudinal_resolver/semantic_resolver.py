"""P2.6.6 semantic resolver. Shadow evaluator only."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import (
    ADAPTER_SOURCE,
    CONFIDENCE_SKIP_THRESHOLD,
    SEM_AMBIGUOUS,
    SEM_DUPLICATE,
    SEM_UNSUPPORTED,
)
from .hypothetical import hypothetical_from_semantic, is_safe_skip_candidate
from .semantic_context_builder import build_semantic_context
from .semantic_replay import adapt_frozen_observations
from .semantic_schema import empty_unsupported, normalize_semantic_payload


def _downgrade_if_unsafe(semantic: Dict[str, Any]) -> Dict[str, Any]:
    """Do not keep DUPLICATE when evidence is too weak for any skip interpretation."""
    if semantic.get("decision") != SEM_DUPLICATE:
        return semantic
    if semantic.get("conflict_present"):
        payload = {
            "decision": SEM_AMBIGUOUS,
            "confidence": semantic.get("confidence"),
            "annotation_interpretation": semantic.get("annotation_interpretation"),
            "target_layer": semantic.get("target_layer"),
            "existing_representation_assessment": "UNCERTAIN",
            "semantic_reason_codes": list(
                dict.fromkeys(
                    list(semantic.get("semantic_reason_codes") or []) + ["DETERMINISTIC_VISION_CONFLICT"]
                )
            ),
            "visual_evidence": semantic.get("visual_evidence") or [],
            "deterministic_context_consistent": False,
            "spatial_context_consistent": bool(semantic.get("spatial_context_consistent")),
            "conflict_present": True,
        }
        out = normalize_semantic_payload(payload)
        for key in ("source", "adapter_observation_count", "adapter_match_statuses"):
            if key in semantic:
                out[key] = semantic[key]
        return out
    return semantic


def resolve_semantic(
    *,
    p265_decision: Dict[str, Any],
    frozen_candidates: List[Dict[str, Any]],
    model: Optional[Dict[str, Any]] = None,
    live_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context = build_semantic_context(
        p265_decision=p265_decision,
        frozen_candidates=frozen_candidates,
        model=model,
    )
    if live_payload:
        try:
            semantic = normalize_semantic_payload(live_payload)
            semantic["source"] = live_payload.get("source") or "P266_LIVE_OR_CACHE"
        except Exception:
            semantic = empty_unsupported(reason="IMAGE_INSUFFICIENT", notes="live payload failed schema")
            semantic["source"] = "P266_LIVE_SCHEMA_FAIL"
    else:
        semantic = adapt_frozen_observations(context=context, frozen_candidates=frozen_candidates)
        semantic = _downgrade_if_unsafe(semantic)

    hypo = hypothetical_from_semantic(
        observed_decision=str(p265_decision.get("observed_decision") or p265_decision.get("decision") or ""),
        coverage=str(p265_decision.get("longitudinal_coverage") or ""),
        semantic=semantic,
        reason_codes=p265_decision.get("reason_codes") or [],
    )
    return {
        "context": context,
        "semantic": semantic,
        "hypothetical": hypo,
        "observed_decision": p265_decision.get("observed_decision") or p265_decision.get("decision"),
        "production_routing_changed": False,
        "safe_skip_candidate": hypo.get("safe_skip_candidate"),
        "confidence_threshold": CONFIDENCE_SKIP_THRESHOLD,
        "adapter_source": semantic.get("source") or ADAPTER_SOURCE,
    }


__all__ = ["is_safe_skip_candidate", "resolve_semantic"]
