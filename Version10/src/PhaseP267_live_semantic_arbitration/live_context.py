"""Build live Claude context from P2.6.6 target records without leaking evaluation labels."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseP266_semantic_longitudinal_resolver.semantic_context_builder import strip_eval_fields

_DROP_LIVE = {
    "frozen_vision_longitudinal_observations",
    "semantic",
    "hypothetical",
    "p266_reference",
    "reference_class",
    "evaluation_reference",
    "control_family",
    "eval_stratum",
    "adapter_source",
    "shadow_decision",
    "hypothetical_vision_routing",
    "safe_skip_candidate",
}


def _notation(annotation_context: Any) -> List[Dict[str, Any]]:
    rows = annotation_context if isinstance(annotation_context, list) else []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or row.get("normalized_text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "text": text,
                "quantity": row.get("quantity"),
                "diameter_mm": row.get("diameter_mm"),
            }
        )
    return out


def build_live_context(target: Dict[str, Any]) -> Dict[str, Any]:
    stored = dict(target.get("context") or {})
    for key in list(_DROP_LIVE):
        stored.pop(key, None)
    stored.pop("crop_path", None)
    anns = stored.get("annotation_context") or []
    stored["candidate_notation"] = _notation(anns)
    stored["task"] = (
        "Classify whether the candidate_notation is a distinct missing longitudinal "
        "requirement or a duplicate/repeat of reinforcement already represented."
    )
    return strip_eval_fields(stored)


__all__ = ["build_live_context"]
