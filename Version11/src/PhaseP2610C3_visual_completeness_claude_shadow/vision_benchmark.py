"""Execute shadow Claude calls for eligible beams. Fail closed."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .claude_client import call_beam_vision
from .config import STATUS_NOT_READY, STATUS_READY, STATUS_LIMITED, STATUS_REVIEW
from .evidence_model import BeamEvidence
from .vision_contract import unusable


def should_call(*, gate_status: str, six_beam_control: bool, include_limitations: bool) -> tuple[bool, str]:
    if gate_status == STATUS_NOT_READY:
        return False, "CLAUDE_CALL_SKIPPED_NOT_READY"
    if six_beam_control and gate_status != STATUS_NOT_READY:
        if gate_status == STATUS_REVIEW:
            return True, "DIAGNOSTIC_REVIEW_ONLY"
        return True, "SIX_BEAM_CONTROL"
    if gate_status == STATUS_READY:
        return True, "ELIGIBLE_VISION_READY"
    if gate_status == STATUS_LIMITED and include_limitations:
        return True, "DIAGNOSTIC_READY_WITH_LIMITATIONS"
    if gate_status == STATUS_REVIEW:
        return False, "CLAUDE_CALL_SKIPPED_REVIEW_ONLY"
    return False, "CLAUDE_CALL_SKIPPED"


def run_one_beam(
    *,
    v10: Path,
    beam: BeamEvidence,
    gate: Dict[str, Any],
    six_beam_control: bool,
    include_limitations: bool,
    client_override: Optional[Callable] = None,
    live: bool = False,
) -> Dict[str, Any]:
    ok, reason = should_call(
        gate_status=str(gate.get("status")),
        six_beam_control=six_beam_control,
        include_limitations=include_limitations,
    )
    rec: Dict[str, Any] = {
        "beam_id": beam.beam_id,
        "gate_status": gate.get("status"),
        "called": False,
        "skip_reason": None,
        "call_reason": reason,
        "cohort_label": reason,
        "audit": None,
        "parsed": None,
        "production_action": "NO_CHANGE",
        "shadow_only": True,
    }
    if not ok or not live:
        rec["called"] = False
        rec["skip_reason"] = reason if not ok else "LIVE_DISABLED"
        if not live and ok:
            rec["skip_reason"] = "LIVE_DISABLED"
            rec["parsed"] = unusable("LIVE_DISABLED")
        else:
            rec["parsed"] = unusable(reason)
        return rec
    ctx = Path(beam.context.path or "")
    det = Path(beam.detail.path or "")
    if not ctx.exists() or not det.exists():
        rec["skip_reason"] = "CLAUDE_CALL_SKIPPED_NOT_READY"
        rec["parsed"] = unusable("missing_selected_png")
        return rec
    result = call_beam_vision(
        version10_root=v10,
        beam_id=beam.beam_id,
        context_path=ctx,
        detail_path=det,
        context_source=str(beam.context.source_phase),
        detail_source=str(beam.detail.source_phase),
        client_override=client_override,
    )
    rec["called"] = True
    rec["audit"] = result.get("audit")
    rec["parsed"] = result.get("parsed")
    rec["raw_text_present"] = bool(result.get("raw_text"))
    return rec


__all__ = ["run_one_beam", "should_call"]
