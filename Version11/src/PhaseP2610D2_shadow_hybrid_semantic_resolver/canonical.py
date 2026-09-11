"""Project D.1 field records into the D.2 canonical provenance schema."""
from __future__ import annotations

from typing import Any, Dict, Optional

from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.config import (
    AUTH_DET_ENG,
    REASON_ACCEPTED,
    REASON_DET_AUTHORITY,
    REASON_DET_ONLY,
    REASON_VISION_ONLY,
)

from .config import (
    REASON_DET_AUTH,
    REASON_DET_ONLY as D2_DET_ONLY,
    REASON_FALLBACK,
    REASON_UNRESOLVED,
    REASON_VISION_ONLY as D2_VISION_ONLY,
    REASON_VISION_VALID,
    SRC_DET,
    SRC_UNRESOLVED,
    SRC_VISION,
)

_EMPTY = (None, "", "UNKNOWN")


def _present(v: Any) -> bool:
    return v not in _EMPTY


def canonical_field(rec: Dict[str, Any], *, origin: str, confidence: Optional[float] = None) -> Dict[str, Any]:
    vis = rec.get("vision_value")
    det = rec.get("deterministic_value")
    resolved = rec.get("resolved_value")
    reason = rec.get("reason")
    fallback = False
    if reason == REASON_ACCEPTED:
        source = SRC_VISION
        res_reason = D2_VISION_ONLY if origin == REASON_VISION_ONLY else REASON_VISION_VALID
    elif reason == REASON_DET_AUTHORITY:
        source = SRC_DET if _present(resolved) else SRC_UNRESOLVED
        res_reason = REASON_DET_AUTH if _present(resolved) else REASON_UNRESOLVED
    elif origin == REASON_DET_ONLY:
        source = SRC_DET if _present(resolved) else SRC_UNRESOLVED
        res_reason = D2_DET_ONLY if _present(resolved) else REASON_UNRESOLVED
    elif _present(resolved) and rec.get("authority_used") not in (None, "VISION_PREFERRED"):
        source = SRC_DET
        res_reason = REASON_FALLBACK
        fallback = True
    elif _present(resolved):
        source = SRC_DET
        res_reason = REASON_FALLBACK
        fallback = True
    else:
        source = SRC_UNRESOLVED
        res_reason = REASON_UNRESOLVED
        fallback = not _present(vis)
    return {
        "value": resolved if source != SRC_UNRESOLVED else None,
        "source": source,
        "confidence": confidence if source == SRC_VISION else rec.get("confidence"),
        "fallback_used": fallback,
        "vision_value": vis,
        "deterministic_value": det,
        "conflict_detected": bool(rec.get("conflict_recorded")),
        "resolution_reason": res_reason,
        "validation_reason": (rec.get("validation") or {}).get("reason"),
    }


def engineering_refs(det: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    det = det or {}
    cut = det.get("cut_length_mm")
    return {
        "geometry_reference": "DETERMINISTIC_AUTHORITY",
        "cut_length_reference": cut if cut is not None else "UNAVAILABLE",
        "development_length_reference": "DETERMINISTIC_AUTHORITY",
        "anchorage_reference": "DETERMINISTIC_AUTHORITY",
        "hook_reference": "DETERMINISTIC_AUTHORITY",
        "source": SRC_DET,
        "authority": AUTH_DET_ENG,
    }


__all__ = ["canonical_field", "engineering_refs"]
