"""Visual completeness / eligibility for Fifth Set shared renders. No beam-ID rules."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP2610C3_visual_completeness_claude_shadow.vision_benchmark import should_call

from .config import (
    MIN_RENDER_BYTES,
    STATUS_LIMITED,
    STATUS_NOT_READY,
    STATUS_READY,
    STATUS_REVIEW,
)


def evaluate_render(path: str, *, bytes_size: int = 0, sha256: str = None) -> Dict[str, Any]:
    p = Path(path) if path else None
    reasons: List[str] = []
    exists = bool(p and p.exists() and p.is_file())
    size = int(bytes_size or (p.stat().st_size if exists else 0))
    if not exists:
        return {
            "status": STATUS_NOT_READY,
            "reason_codes": ["RENDER_MISSING", "CRITICAL_VISUAL_FAILURE"],
            "sufficient_for_target_interpretation": False,
            "image_exists": False,
        }
    if size < MIN_RENDER_BYTES:
        return {
            "status": STATUS_NOT_READY,
            "reason_codes": ["LOW_INFORMATION_RENDER", "CRITICAL_VISUAL_FAILURE"],
            "sufficient_for_target_interpretation": False,
            "image_exists": True,
        }
    reasons.append("SUFFICIENT_TARGET_EVIDENCE")
    return {
        "status": STATUS_READY,
        "reason_codes": reasons,
        "sufficient_for_target_interpretation": True,
        "image_exists": True,
        "sha256": sha256,
        "bytes": size,
    }


def classify_eligibility(gate_status: str) -> Dict[str, Any]:
    ok, reason = should_call(
        gate_status=str(gate_status or STATUS_NOT_READY),
        six_beam_control=False,
        include_limitations=True,
    )
    return {
        "eligible": bool(ok),
        "call_reason": reason,
        "blocked": str(gate_status) in (STATUS_NOT_READY, STATUS_REVIEW) or not ok,
    }


def evaluate_population(visual: Dict[str, Any]) -> Dict[str, Any]:
    by_id: Dict[str, Dict[str, Any]] = {}
    counts = {
        STATUS_READY: 0,
        STATUS_LIMITED: 0,
        STATUS_NOT_READY: 0,
        STATUS_REVIEW: 0,
        "VISION_ELIGIBLE": 0,
        "VISION_BLOCKED_NOT_READY": 0,
        "visual_source_available": 0,
    }
    for bid, src in sorted((visual.get("by_id") or {}).items()):
        if src.get("available"):
            counts["visual_source_available"] += 1
            gate = evaluate_render(src.get("path") or "", bytes_size=int(src.get("bytes") or 0), sha256=src.get("sha256"))
        else:
            gate = {
                "status": STATUS_NOT_READY,
                "reason_codes": [src.get("reason") or "RENDER_MISSING", "CRITICAL_VISUAL_FAILURE"],
                "sufficient_for_target_interpretation": False,
                "image_exists": False,
            }
        elig = classify_eligibility(str(gate.get("status")))
        status = str(gate.get("status"))
        counts[status] = counts.get(status, 0) + 1
        if elig.get("eligible"):
            counts["VISION_ELIGIBLE"] += 1
        else:
            counts["VISION_BLOCKED_NOT_READY"] += 1
        by_id[str(bid)] = {
            "beam_id": str(bid),
            "gate": gate,
            "eligibility": elig,
            "visual": src,
        }
    return {"counts": counts, "by_id": by_id}


__all__ = ["classify_eligibility", "evaluate_population", "evaluate_render"]
