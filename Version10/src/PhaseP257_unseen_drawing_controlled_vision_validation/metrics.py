"""P2.5.7 incremental-value, safety, stirrup/role/OCR, and cost metrics."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP256_controlled_field_level_vision_experiment.config import FIELDS

from .config import (
    EVAL_EXACT,
    EVAL_UNRESOLVED,
    EVAL_WRONG,
    INC_ADDS_CORRECT,
    INC_CONFIRMS,
    INC_CONFLICTS_CORRECT_DET,
    INC_CORRECTS_WRONG_DET,
    INC_WRONG_ON_CORRECT_DET,
)

INPUT_USD_PER_MTOK = 3.0
OUTPUT_USD_PER_MTOK = 15.0

_KPI_FIELDS = tuple(f for f in FIELDS if f != "zone")


def _rate(n: int, d: int) -> Optional[float]:
    if d <= 0:
        return None
    return round(n / d, 6)


def _ocr(text: str) -> bool:
    return "\\X" in (text or "") or "\x00" in (text or "")


def _is_stirrup(row: Dict[str, Any]) -> bool:
    gt = row.get("ground_truth") or {}
    det = row.get("deterministic") or {}
    text = str((row.get("candidate") or {}).get("raw_text") or "")
    if gt.get("semantic_type") == "STIRRUP":
        return True
    if det.get("deterministic_type") == "STIRRUP":
        return True
    return "@" in text and "Y" in text.upper() and ("L" in text.upper() or "C/C" in text.upper())


def compute_cost_metrics(
    *,
    vision_rows: List[Dict[str, Any]],
    true_incremental_field_count: int,
    eligible_count: int,
) -> Dict[str, Any]:
    live = 0
    failed = 0
    inp = 0
    out = 0
    for r in vision_rows:
        obs = r.get("vision_obs") or {}
        if not obs.get("live_call"):
            continue
        live += 1
        if not obs.get("api_ok"):
            failed += 1
        usage = obs.get("usage") or {}
        inp += int(usage.get("input_tokens") or obs.get("input_tokens") or 0)
        out += int(usage.get("output_tokens") or obs.get("output_tokens") or 0)
    total = inp + out
    cost = (inp / 1_000_000.0) * INPUT_USD_PER_MTOK + (out / 1_000_000.0) * OUTPUT_USD_PER_MTOK
    vis_fields = 0
    for r in vision_rows:
        vis = ((r.get("vision_obs") or {}).get("validated_interpretation"))
        if vis:
            vis_fields += 1
    return {
        "live_claude_calls": live,
        "failed_calls": failed,
        "input_tokens": inp,
        "output_tokens": out,
        "total_tokens": total,
        "estimated_cost_usd": round(cost, 6),
        "cost_note": (
            "Approx Claude Sonnet list rates $3/MTok in + $15/MTok out; "
            "actual Anthropic billing may differ"
        ),
        "cost_per_candidate": round(cost / eligible_count, 6) if eligible_count else None,
        "cost_per_Vision_field_candidate": round(cost / vis_fields, 6) if vis_fields else None,
        "cost_per_TRUE_INCREMENTAL_FIELD": (
            round(cost / true_incremental_field_count, 6) if true_incremental_field_count else None
        ),
        "true_incremental_field_count": true_incremental_field_count,
    }


def compute_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_fields = 0
    scored_fields = 0
    unscored_fields = 0
    invoked_scored = 0
    det_gap_invoked = 0  # invoked + scored + det UNKNOWN/WRONG
    true_inc = 0
    confirms = 0
    conflicts_correct = 0
    corrects_wrong = 0
    wrong_on_correct = 0
    dangerous = 0
    vision_field_candidates = 0
    det_exact = 0
    vis_exact = 0
    hypo_exact = 0
    vis_scored = 0
    hypo_scored = 0

    by_field: Dict[str, Dict[str, Any]] = {
        f: {
            "scored": 0,
            "vision_scored": 0,
            "deterministic_exact": 0,
            "vision_exact": 0,
            "hypothetical_exact": 0,
            "incremental_corrections": 0,
            "dangerous_conflicts": 0,
            "det_gap": 0,
            "true_incremental": 0,
        }
        for f in _KPI_FIELDS
    }

    for row in rows:
        invoked = bool(row.get("invoke_claude"))
        tw = row.get("three_way") or {}
        vis = ((row.get("vision_obs") or {}).get("validated_interpretation"))
        for field in _KPI_FIELDS:
            rec = tw.get(field) or {}
            total_fields += 1
            if not rec.get("scored"):
                unscored_fields += 1
                continue
            scored_fields += 1
            bf = by_field[field]
            bf["scored"] += 1
            d_eval = rec.get("deterministic_eval")
            v_eval = rec.get("vision_eval")
            h_eval = rec.get("hypothetical_eval")
            inc = rec.get("incremental")
            if d_eval == EVAL_EXACT:
                det_exact += 1
                bf["deterministic_exact"] += 1
            if invoked:
                invoked_scored += 1
                vis_scored += 1
                bf["vision_scored"] += 1
                hypo_scored += 1
                if v_eval == EVAL_EXACT:
                    vis_exact += 1
                    bf["vision_exact"] += 1
                if h_eval == EVAL_EXACT:
                    hypo_exact += 1
                    bf["hypothetical_exact"] += 1
                if rec.get("vision_value") not in (None, "", "UNKNOWN", [], "UNCERTAIN"):
                    if field == "spacing" and not rec.get("vision_value"):
                        pass
                    else:
                        vision_field_candidates += 1
                if d_eval in (EVAL_UNRESOLVED, EVAL_WRONG):
                    det_gap_invoked += 1
                    bf["det_gap"] += 1
                    if v_eval == EVAL_EXACT:
                        true_inc += 1
                        bf["true_incremental"] += 1
                if inc == INC_CONFIRMS:
                    confirms += 1
                elif inc == INC_CONFLICTS_CORRECT_DET:
                    conflicts_correct += 1
                elif inc == INC_CORRECTS_WRONG_DET:
                    corrects_wrong += 1
                    bf["incremental_corrections"] += 1
                elif inc == INC_ADDS_CORRECT:
                    bf["incremental_corrections"] += 1
                elif inc == INC_WRONG_ON_CORRECT_DET:
                    wrong_on_correct += 1
                if rec.get("dangerous_candidate"):
                    dangerous += 1
                    bf["dangerous_conflicts"] += 1
            else:
                # Hypothetical combined uses deterministic when Vision is not invoked.
                hypo_scored += 1
                if d_eval == EVAL_EXACT:
                    hypo_exact += 1
                    bf["hypothetical_exact"] += 1

    field_metrics = {}
    for f, rec in by_field.items():
        field_metrics[f] = {
            **rec,
            "deterministic_accuracy": _rate(rec["deterministic_exact"], rec["scored"]),
            "vision_accuracy": _rate(rec["vision_exact"], rec["vision_scored"]),
            "combined_hypothetical_accuracy": _rate(rec["hypothetical_exact"], rec["scored"]),
        }

    det_only_acc = _rate(det_exact, scored_fields)
    # Combined accuracy over all scored fields (skipped candidates keep deterministic).
    combined_acc = _rate(hypo_exact, hypo_scored)
    vis_acc = _rate(vis_exact, vis_scored)

    stirrup = _thin_subset([r for r in rows if _is_stirrup(r)], label="stirrup")
    ocr = _thin_subset(
        [r for r in rows if _ocr(str((r.get("candidate") or {}).get("raw_text") or ""))],
        label="ocr",
    )
    role = _role_metrics(rows)

    gt_coverage = _rate(scored_fields, total_fields)

    return {
        "total_candidate_fields": total_fields,
        "fields_with_reliable_GT": scored_fields,
        "fields_without_reliable_GT": unscored_fields,
        "GT_coverage": gt_coverage,
        "TRUE_VISION_INCREMENTAL_VALUE_RATE": _rate(true_inc, det_gap_invoked),
        "true_incremental_field_count": true_inc,
        "deterministic_gap_invoked_count": det_gap_invoked,
        "VISION_CORRECTION_RATE": _rate(corrects_wrong, invoked_scored),
        "VISION_CONFIRMATION_RATE": _rate(confirms, invoked_scored),
        "VISION_CONFLICT_RATE": _rate(conflicts_correct + wrong_on_correct, invoked_scored),
        "VISION_WRONG_ON_CORRECT_DETERMINISTIC_RATE": _rate(wrong_on_correct, invoked_scored),
        "dangerous_vision_override_count": dangerous,
        "dangerous_vision_override_rate": _rate(dangerous, max(vision_field_candidates, 1) if vision_field_candidates else 0)
        if vision_field_candidates
        else _rate(dangerous, 0),
        "vision_field_candidate_count": vision_field_candidates,
        "DETERMINISTIC_BASELINE_ACCURACY": det_only_acc,
        "DETERMINISTIC_ONLY_ACCURACY": det_only_acc,
        "VISION_FIELD_ACCURACY": vis_acc,
        "HYPOTHETICAL_COMBINED_ACCURACY": combined_acc,
        "COMBINED_SHADOW_FIELD_ACCURACY": combined_acc,
        "IMPROVEMENT_DELTA": (
            round((combined_acc or 0) - (det_only_acc or 0), 6)
            if det_only_acc is not None and combined_acc is not None
            else None
        ),
        "by_field": field_metrics,
        "stirrup": stirrup,
        "role": role,
        "ocr": ocr,
        "accepted_shadow_field_count": sum(
            len(r.get("accepted_shadow_fields") or []) for r in rows
        ),
        "rejected_shadow_field_count": sum(
            len(r.get("rejected_shadow_fields") or []) for r in rows
        ),
        "conflict_field_count": sum(len(r.get("conflict_fields") or []) for r in rows),
        "production_mutation_count": 0,
        "steel_quantity_difference": 0,
        "bbs_difference": 0,
        "excel_difference": 0,
        "counts": {
            "VISION_ADDS_CORRECT_FIELD": true_inc,
            "VISION_CONFIRMS_DETERMINISTIC": confirms,
            "VISION_CONFLICTS_WITH_CORRECT_DETERMINISTIC": conflicts_correct,
            "VISION_CORRECTS_WRONG_DETERMINISTIC": corrects_wrong,
            "VISION_WRONG_ON_CORRECT_DETERMINISTIC": wrong_on_correct,
        },
    }


def _role_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    roles = ("TOP_BAR", "BOTTOM_BAR", "SIDE_FACE", "STIRRUP")
    out: Dict[str, Any] = {}
    for role in roles:
        det_known = vis_known = gt_n = vis_correct = vis_wrong = det_ok_vis_wrong = det_unk_vis_ok = 0
        for row in rows:
            rec = (row.get("three_way") or {}).get("reinforcement_role") or {}
            gt = (row.get("ground_truth") or {}).get("role")
            det = (row.get("deterministic") or {}).get("deterministic_role")
            vis = ((row.get("vision_obs") or {}).get("validated_interpretation") or {}).get("role")
            if gt != role and det != role and vis != role:
                continue
            if gt == role:
                gt_n += 1
            if det not in (None, "", "UNKNOWN"):
                det_known += 1
            if vis not in (None, "", "UNKNOWN"):
                vis_known += 1
            if rec.get("scored"):
                if rec.get("vision_eval") == EVAL_EXACT:
                    vis_correct += 1
                if rec.get("vision_eval") == EVAL_WRONG:
                    vis_wrong += 1
                if rec.get("deterministic_eval") == EVAL_EXACT and rec.get("vision_eval") == EVAL_WRONG:
                    det_ok_vis_wrong += 1
                if rec.get("deterministic_unknown_vision_correct"):
                    det_unk_vis_ok += 1
        out[role] = {
            "ground_truth_count": gt_n,
            "deterministic_known": det_known,
            "vision_known": vis_known,
            "vision_correct_recovery": vis_correct,
            "vision_wrong_recovery": vis_wrong,
            "deterministic_correct_vision_wrong": det_ok_vis_wrong,
            "deterministic_unknown_vision_correct": det_unk_vis_ok,
        }
    return out


def _thin_subset(rows: List[Dict[str, Any]], *, label: str) -> Dict[str, Any]:
    scored = 0
    det_exact = 0
    vis_exact = 0
    vis_scored = 0
    true_inc = 0
    gap = 0
    vis_wrong = 0
    for row in rows:
        invoked = bool(row.get("invoke_claude"))
        tw = row.get("three_way") or {}
        for field in _KPI_FIELDS:
            rec = tw.get(field) or {}
            if not rec.get("scored"):
                continue
            scored += 1
            if rec.get("deterministic_eval") == EVAL_EXACT:
                det_exact += 1
            if invoked:
                vis_scored += 1
                if rec.get("vision_eval") == EVAL_EXACT:
                    vis_exact += 1
                if rec.get("deterministic_eval") in (EVAL_UNRESOLVED, EVAL_WRONG):
                    gap += 1
                    if rec.get("vision_eval") == EVAL_EXACT:
                        true_inc += 1
                if rec.get("vision_eval") == EVAL_WRONG:
                    vis_wrong += 1
    return {
        "label": label,
        "candidates": len(rows),
        "scored_fields": scored,
        "deterministic_accuracy": _rate(det_exact, scored),
        "vision_accuracy": _rate(vis_exact, vis_scored),
        "TRUE_VISION_INCREMENTAL_VALUE_RATE": _rate(true_inc, gap),
        "vision_only_correct_recovery": true_inc,
        "vision_wrong_recovery": vis_wrong,
    }


__all__ = ["compute_cost_metrics", "compute_metrics"]
