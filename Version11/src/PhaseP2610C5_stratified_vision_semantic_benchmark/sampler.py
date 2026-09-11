"""Deterministic stratified sample. Cap 10. No beam-ID special cases."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Set

from .config import MAX_SAMPLE_SIZE, STATUS_NOT_READY, STRATA, TARGET_SAMPLE_SIZE
from .strata import classify_strata, eligibility_rank, strata_set


def eligible_candidates(
    records: Sequence[Dict[str, Any]],
    *,
    exclude_ids: Sequence[str],
    allow_not_ready: bool = False,
) -> List[Dict[str, Any]]:
    excluded = set(exclude_ids or [])
    out: List[Dict[str, Any]] = []
    for rec in records:
        if rec.get("beam_id") in excluded:
            continue
        if not rec.get("evidence_valid"):
            continue
        if rec.get("c3_visual_gate_status") == STATUS_NOT_READY and not allow_not_ready:
            continue
        row = dict(rec)
        row["strata"] = classify_strata(row)
        out.append(row)
    return out


def _pick_key(rec: Dict[str, Any], uncovered: Set[str]) -> tuple:
    cover = len(strata_set(rec) & uncovered)
    return (
        eligibility_rank(rec),
        -cover,
        -len(strata_set(rec)),
        str(rec.get("beam_id") or ""),
    )


def _fill_key(rec: Dict[str, Any], selected: Sequence[Dict[str, Any]]) -> tuple:
    used_combos = {tuple(r.get("strata") or []) for r in selected}
    combo = tuple(rec.get("strata") or classify_strata(rec))
    union: Set[str] = set()
    for r in selected:
        union |= strata_set(r)
    mixed_n = sum(1 for r in selected if r.get("mixed_source"))
    return (
        0 if combo not in used_combos else 1,
        eligibility_rank(rec),
        0 if rec.get("mixed_source") and mixed_n == 0 else 1,
        -len(strata_set(rec) - union),
        -len(strata_set(rec)),
        str(rec.get("beam_id") or ""),
    )


def select_sample(
    records: Sequence[Dict[str, Any]],
    *,
    exclude_ids: Sequence[str],
    target_size: int = TARGET_SAMPLE_SIZE,
) -> Dict[str, Any]:
    if target_size > MAX_SAMPLE_SIZE:
        return {
            "ok": False,
            "reason": "FAIL_CLOSED_SAMPLE_CAP",
            "selected": [],
            "notes": [f"requested {target_size} exceeds MAX_SAMPLE_SIZE {MAX_SAMPLE_SIZE}"],
        }
    notes: List[str] = []
    pool = eligible_candidates(records, exclude_ids=exclude_ids, allow_not_ready=False)
    if len(pool) < target_size:
        extra = eligible_candidates(records, exclude_ids=exclude_ids, allow_not_ready=True)
        if len(extra) > len(pool):
            notes.append("NOT_READY_EXCEPTION_INSUFFICIENT_ELIGIBLE")
            pool = extra
    if exclude_ids and len(pool) < target_size:
        notes.append("PRIOR_CONTROL_EXCLUSION_RELAXED")
        pool = eligible_candidates(records, exclude_ids=[], allow_not_ready=False)
        if len(pool) < target_size:
            pool = eligible_candidates(records, exclude_ids=[], allow_not_ready=True)
            notes.append("NOT_READY_EXCEPTION_INSUFFICIENT_ELIGIBLE")
    elif exclude_ids:
        notes.append("PRIOR_CONTROL_EXCLUDED_GENERIC")

    selected: List[Dict[str, Any]] = []
    uncovered: Set[str] = set(STRATA)
    remaining = list(pool)
    for stratum in STRATA:
        if len(selected) >= target_size:
            break
        if stratum not in uncovered:
            continue
        cand = [r for r in remaining if stratum in strata_set(r)]
        if not cand:
            continue
        pick = min(cand, key=lambda r: _pick_key(r, uncovered))
        selected.append(pick)
        remaining = [r for r in remaining if r.get("beam_id") != pick.get("beam_id")]
        uncovered -= strata_set(pick)

    while len(selected) < target_size and remaining:
        pick = min(remaining, key=lambda r: _fill_key(r, selected))
        selected.append(pick)
        remaining = [r for r in remaining if r.get("beam_id") != pick.get("beam_id")]
        uncovered -= strata_set(pick)

    if len(selected) > MAX_SAMPLE_SIZE:
        return {
            "ok": False,
            "reason": "FAIL_CLOSED_SAMPLE_CAP",
            "selected": [],
            "notes": notes + ["selected exceeded cap"],
        }
    ids = [r.get("beam_id") for r in selected]
    why = []
    covered: Set[str] = set()
    for rec in selected:
        rec_strata = classify_strata(rec)
        rec["strata"] = rec_strata
        rec["selection_reason"] = {
            "strata": rec_strata,
            "gate_status": rec.get("c3_visual_gate_status"),
            "new_strata": sorted(set(rec_strata) - covered),
            "mixed_source": rec.get("mixed_source"),
            "deterministic_group_count": rec.get("deterministic_group_count"),
        }
        covered |= set(rec_strata)
        why.append({"beam_id": rec.get("beam_id"), **rec["selection_reason"]})
    return {
        "ok": True,
        "reason": None,
        "selected": selected,
        "selected_ids": ids,
        "size": len(selected),
        "notes": notes,
        "strata_coverage": sorted(covered),
        "uncovered_strata": sorted(set(STRATA) - covered),
        "why": why,
        "excluded_prior_control": list(exclude_ids or []),
        "eligible_pool_size": len(pool),
    }


__all__ = ["eligible_candidates", "select_sample"]
