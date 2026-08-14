"""P2.5.9 promotion strategies. Runtime path must not read estimator/GT steel."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP256_controlled_field_level_vision_experiment.field_validator import (
    validate_vision_field,
    vision_present,
)
from PhaseP258_controlled_vision_field_repair.config import (
    DEC_BLOCK,
    DEC_INELIGIBLE,
    DEC_PROMOTE,
    DET_CONFIRMED,
    DET_PARTIAL,
    DET_UNKNOWN,
    FORBIDDEN_FIELDS,
    WHITELIST_FIELDS,
)
from PhaseP258_controlled_vision_field_repair.det_status import classify_deterministic_status
from PhaseP258_controlled_vision_field_repair.promotion_gate import evaluate_audit
from PhaseP258_controlled_vision_field_repair.promotion_rules import is_whitelisted, load_promotion_rules
from PhaseP258_controlled_vision_field_repair.repair_contract import build_repair_candidate

from .beam_safety import assert_no_ground_truth, evaluate_conservative_partial
from .config import (
    MODEL_VERSION,
    OUT_ACCEPT_PARTIAL,
    OUT_ACCEPT_UNKNOWN,
    OUT_BLOCKED,
    OUT_BLOCKED_CONFIRMED,
    OUT_HOLD_PARTIAL,
    OUT_INELIGIBLE,
    OUT_REJECT_PARTIAL,
    PHASE_ID,
    REASON_ARB_ACCEPTED,
    REASON_CONFIRMED,
    REASON_PARTIAL_NEEDS_ARB,
    REASON_UNKNOWN_VALID,
    STRATEGY_CONSERVATIVE_PARTIAL,
    STRATEGY_P258_CURRENT,
    STRATEGY_UNKNOWN_ONLY,
)
from .policy import load_arbitration_config

_EVAL_FIELDS = (
    "diameter",
    "legs",
    "spacing",
    "reinforcement_role",
    "semantic_type",
    "quantity",
    "zone",
)


def _extract_values(audit: Dict[str, Any], field: str) -> tuple[Any, Any, Any, str]:
    """Read deterministic + Vision values. Does not read three_way GT/eval."""
    det = audit.get("deterministic_result") or {}
    vis = audit.get("vision_result") or {}
    det_type = det.get("semantic_type") or audit.get("deterministic_type")
    det_val = None
    vis_val = None
    if field == "diameter":
        det_val = det.get("diameter_value_mm")
        vis_val = vis.get("diameter_mm")
    elif field == "legs":
        det_val = det.get("leg_count")
        vis_val = vis.get("legs")
    elif field == "spacing":
        det_val = list(det.get("spacing_values_mm") or [])
        vis_val = list(vis.get("spacing_mm") or [])
    elif field == "reinforcement_role":
        det_val = det.get("reinforcement_role")
        vis_val = vis.get("role")
    elif field == "semantic_type":
        det_val = det.get("semantic_type")
        vis_val = vis.get("semantic_type")
    elif field == "quantity":
        det_val = det.get("quantity_value")
        vis_val = vis.get("quantity")
    elif field == "zone":
        vis_val = vis.get("zone")
    return det_val, vis_val, vis, str(det_type or "")


def _candidate(
    *,
    audit: Dict[str, Any],
    field: str,
    det_val: Any,
    vis_val: Any,
    det_status: str,
    vis_ok: bool,
    decision: str,
    level: str,
    reason: str,
    outcome: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rec = build_repair_candidate(
        candidate_id=str(audit.get("candidate_id")),
        beam_id=str(audit.get("beam_id")),
        annotation_id=str(audit.get("annotation_id")),
        annotation_text=str(audit.get("annotation_text") or ""),
        field_name=field,
        deterministic_value=det_val,
        deterministic_status=det_status,
        vision_value=vis_val,
        vision_status="VALID" if vis_ok else "INVALID",
        trigger_reason=list(audit.get("shadow_trigger_reason") or []),
        validation_status="PASS" if vis_ok else "FAIL",
        validation_rules_passed=bool(vis_ok),
        ground_truth_value=None,
        ground_truth_status="NOT_USED_IN_ARBITRATION",
        promotion_class=level,
        promotion_decision=decision,
        source_model=audit.get("model"),
        prompt_version=str(audit.get("prompt_version") or ""),
        schema_version=str(audit.get("schema_version") or ""),
        evidence_fingerprint=audit.get("evidence_fingerprint"),
        reason=reason,
    )
    rec["phase_id"] = PHASE_ID
    rec["model_version"] = MODEL_VERSION
    rec["arbitration_outcome"] = outcome
    rec["reason_codes"] = [reason]
    if extra:
        rec.update(extra)
    return rec


def arbitrate_field(
    *,
    audit: Dict[str, Any],
    field: str,
    strategy: str,
    beam_ctx: Optional[Dict[str, Any]] = None,
    rules: Optional[Dict[str, Any]] = None,
    arb_cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Strategy B/C runtime arbitration. Does not read GT or estimator steel."""
    assert_no_ground_truth(beam_ctx)
    rules = rules or load_promotion_rules()
    arb_cfg = arb_cfg or load_arbitration_config()
    text = str(audit.get("annotation_text") or "")
    det_val, vis_val, vis, det_type = _extract_values(audit, field)
    det_status = classify_deterministic_status(
        field=field,
        deterministic_value=det_val,
        annotation_text=text,
        deterministic_type=det_type,
    )
    vis_known = vision_present(vis_val, field=field)
    vis_ok = False
    vis_err = ["VISION_MISSING"]
    if vis_known:
        checked = validate_vision_field(
            field=field,
            value=vis_val,
            annotation_text=text,
            effective_type=det_type or str((vis or {}).get("semantic_type") or ""),
        )
        vis_ok = bool(checked.get("ok"))
        vis_err = list(checked.get("errors") or [])

    if audit.get("invoke_claude") is False or not vis:
        return _candidate(
            audit=audit, field=field, det_val=det_val, vis_val=vis_val,
            det_status=det_status, vis_ok=False, decision=DEC_BLOCK,
            level=OUT_BLOCKED, reason="NO_VISION_RESULT", outcome=OUT_BLOCKED,
        )
    if field in FORBIDDEN_FIELDS or field == "zone":
        return _candidate(
            audit=audit, field=field, det_val=det_val, vis_val=vis_val,
            det_status=det_status, vis_ok=vis_ok, decision=DEC_INELIGIBLE,
            level=OUT_INELIGIBLE, reason="FORBIDDEN_FIELD", outcome=OUT_INELIGIBLE,
        )
    if not is_whitelisted(semantic_type=det_type, field=field, rules=rules):
        return _candidate(
            audit=audit, field=field, det_val=det_val, vis_val=vis_val,
            det_status=det_status, vis_ok=vis_ok, decision=DEC_INELIGIBLE,
            level=OUT_INELIGIBLE, reason="NOT_WHITELISTED", outcome=OUT_INELIGIBLE,
        )
    if field in WHITELIST_FIELDS and det_type != "STIRRUP":
        return _candidate(
            audit=audit, field=field, det_val=det_val, vis_val=vis_val,
            det_status=det_status, vis_ok=vis_ok, decision=DEC_BLOCK,
            level=OUT_BLOCKED, reason="TYPE_NOT_STIRRUP", outcome=OUT_BLOCKED,
        )
    if det_status == DET_CONFIRMED:
        return _candidate(
            audit=audit, field=field, det_val=det_val, vis_val=vis_val,
            det_status=det_status, vis_ok=vis_ok, decision=DEC_BLOCK,
            level=OUT_BLOCKED_CONFIRMED, reason=REASON_CONFIRMED,
            outcome=OUT_BLOCKED_CONFIRMED,
        )
    if not vis_known:
        return _candidate(
            audit=audit, field=field, det_val=det_val, vis_val=vis_val,
            det_status=det_status, vis_ok=False, decision=DEC_BLOCK,
            level=OUT_BLOCKED, reason="VISION_VALUE_MISSING", outcome=OUT_BLOCKED,
        )
    if not vis_ok:
        return _candidate(
            audit=audit, field=field, det_val=det_val, vis_val=vis_val,
            det_status=det_status, vis_ok=False, decision=DEC_BLOCK,
            level=OUT_BLOCKED, reason=(vis_err[0] if vis_err else "VISION_INVALID"),
            outcome=OUT_BLOCKED,
        )

    if det_status == DET_UNKNOWN:
        if not arb_cfg.get("allow_unknown_recovery", True):
            return _candidate(
                audit=audit, field=field, det_val=det_val, vis_val=vis_val,
                det_status=det_status, vis_ok=True, decision=DEC_BLOCK,
                level=OUT_BLOCKED, reason="UNKNOWN_RECOVERY_DISABLED", outcome=OUT_BLOCKED,
            )
        return _candidate(
            audit=audit, field=field, det_val=det_val, vis_val=vis_val,
            det_status=det_status, vis_ok=True, decision=DEC_PROMOTE,
            level=DEC_PROMOTE, reason=REASON_UNKNOWN_VALID,
            outcome=OUT_ACCEPT_UNKNOWN,
        )

    if det_status == DET_PARTIAL:
        if strategy == STRATEGY_UNKNOWN_ONLY:
            return _candidate(
                audit=audit, field=field, det_val=det_val, vis_val=vis_val,
                det_status=det_status, vis_ok=True, decision=DEC_BLOCK,
                level=OUT_HOLD_PARTIAL, reason=REASON_PARTIAL_NEEDS_ARB,
                outcome=OUT_HOLD_PARTIAL,
            )
        if strategy == STRATEGY_CONSERVATIVE_PARTIAL:
            gate = evaluate_conservative_partial(
                field=field, det_val=det_val, vis_val=vis_val, beam_ctx=beam_ctx, cfg=arb_cfg,
            )
            if gate.get("accept"):
                rec = _candidate(
                    audit=audit, field=field, det_val=det_val, vis_val=vis_val,
                    det_status=det_status, vis_ok=True, decision=DEC_PROMOTE,
                    level=DEC_PROMOTE, reason=REASON_ARB_ACCEPTED,
                    outcome=OUT_ACCEPT_PARTIAL,
                    extra={"arbitration_signals": gate.get("signals")},
                )
                rec["reason_codes"] = list(gate.get("reason_codes") or [REASON_ARB_ACCEPTED])
                rec["reason"] = rec["reason_codes"][0]
                return rec
            rec = _candidate(
                audit=audit, field=field, det_val=det_val, vis_val=vis_val,
                det_status=det_status, vis_ok=True, decision=DEC_BLOCK,
                level=OUT_REJECT_PARTIAL, reason=(gate["reason_codes"][0] if gate.get("reason_codes") else REASON_PARTIAL_NEEDS_ARB),
                outcome=OUT_REJECT_PARTIAL,
                extra={"arbitration_signals": gate.get("signals")},
            )
            rec["reason_codes"] = list(gate.get("reason_codes") or [])
            return rec
        return _candidate(
            audit=audit, field=field, det_val=det_val, vis_val=vis_val,
            det_status=det_status, vis_ok=True, decision=DEC_BLOCK,
            level=OUT_HOLD_PARTIAL, reason=REASON_PARTIAL_NEEDS_ARB,
            outcome=OUT_HOLD_PARTIAL,
        )

    return _candidate(
        audit=audit, field=field, det_val=det_val, vis_val=vis_val,
        det_status=det_status, vis_ok=vis_ok, decision=DEC_BLOCK,
        level=OUT_BLOCKED, reason="NO_REPAIR_PATH", outcome=OUT_BLOCKED,
    )


def evaluate_strategy(
    *,
    audits: List[Dict[str, Any]],
    strategy: str,
    beam_contexts: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    rules = load_promotion_rules()
    if strategy == STRATEGY_P258_CURRENT:
        out: List[Dict[str, Any]] = []
        for audit in audits:
            for rec in evaluate_audit(audit, rules=rules):
                row = dict(rec)
                row["strategy"] = strategy
                det_s = rec.get("deterministic_status")
                if rec.get("promotion_decision") == DEC_PROMOTE and det_s == DET_UNKNOWN:
                    row["arbitration_outcome"] = OUT_ACCEPT_UNKNOWN
                elif rec.get("promotion_decision") == DEC_PROMOTE and det_s == DET_PARTIAL:
                    row["arbitration_outcome"] = "P258_PARTIAL_PROMOTED"
                elif rec.get("reason") == REASON_CONFIRMED:
                    row["arbitration_outcome"] = OUT_BLOCKED_CONFIRMED
                else:
                    row["arbitration_outcome"] = rec.get("promotion_decision")
                row["reason_codes"] = [rec.get("reason")]
                out.append(row)
        return out

    ctxs = beam_contexts or {}
    arb_cfg = load_arbitration_config()
    out = []
    for audit in audits:
        bid = str(audit.get("beam_id") or "")
        ctx = ctxs.get(bid)
        assert_no_ground_truth(ctx)
        for field in _EVAL_FIELDS:
            rec = arbitrate_field(
                audit=audit, field=field, strategy=strategy, beam_ctx=ctx,
                rules=rules, arb_cfg=arb_cfg,
            )
            rec["strategy"] = strategy
            out.append(rec)
    return out


def promoted_only(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in rows if r.get("promotion_decision") == DEC_PROMOTE]


__all__ = ["arbitrate_field", "evaluate_strategy", "promoted_only"]
