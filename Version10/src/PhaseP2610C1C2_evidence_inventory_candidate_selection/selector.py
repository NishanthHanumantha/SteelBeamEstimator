"""Preference-preserving selector. B.1 retained unless material evidence. No beam-ID rules."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import (
    MATERIAL_SCORE_MARGIN,
    MAX_COVERAGE_REGRESSION,
    MIN_FOREGROUND_GAIN,
    PREFERRED_SOURCE,
)


def _preferred(cands: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for c in cands:
        if c.get("source_phase") == PREFERRED_SOURCE and c.get("artefact_id") == "canonical":
            return c
    for c in cands:
        if c.get("source_phase") == PREFERRED_SOURCE:
            return c
    return None


def _challengers(cands: List[Dict[str, Any]], baseline: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    seen = set()
    bsha = (baseline or {}).get("sha256")
    for c in cands:
        if c.get("source_phase") == PREFERRED_SOURCE and c.get("artefact_id") == "canonical":
            continue
        if c.get("candidate_status") in ("MISSING", "DUPLICATE_OF_PREFERRED"):
            continue
        if not c.get("exists"):
            continue
        sha = c.get("sha256")
        if sha and sha == bsha:
            continue
        if sha and sha in seen:
            continue
        if sha:
            seen.add(sha)
        out.append(c)
    return out


def _materially_better(baseline: Dict[str, Any], challenger: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    reasons: List[str] = []
    evidence = {
        "baseline_score": baseline.get("score"),
        "challenger_score": challenger.get("score"),
        "score_margin": MATERIAL_SCORE_MARGIN,
        "foreground_gain": round(float(challenger.get("foreground_ratio") or 0.0) - float(baseline.get("foreground_ratio") or 0.0), 5),
        "coverage_x_delta": round(float(challenger.get("coverage_x") or 0.0) - float(baseline.get("coverage_x") or 0.0), 5),
    }
    if challenger.get("critical_failure"):
        return False, ["CHALLENGER_CRITICAL_FAILURE"], evidence
    if baseline.get("critical_failure") and not challenger.get("critical_failure"):
        return True, ["CLEARS_BASELINE_CRITICAL_FAILURE"], evidence
    if baseline.get("critical_failure"):
        return False, ["CHALLENGER_STILL_CRITICAL"], evidence
    score_ok = float(challenger.get("score") or -1.0) >= float(baseline.get("score") or 0.0) + MATERIAL_SCORE_MARGIN
    fg_ok = evidence["foreground_gain"] >= MIN_FOREGROUND_GAIN
    cov_ok = evidence["coverage_x_delta"] >= -MAX_COVERAGE_REGRESSION
    if not cov_ok:
        return False, ["COVERAGE_REGRESSION_GUARDRAIL"], evidence
    if score_ok and fg_ok:
        reasons.append("MATERIAL_SCORE_AND_FOREGROUND_GAIN")
        return True, reasons, evidence
    if score_ok and not fg_ok:
        return False, ["SCORE_DELTA_NOT_MATERIAL_WITHOUT_FOREGROUND_GAIN"], evidence
    return False, ["NO_MATERIAL_IMPROVEMENT"], evidence


def select_for_type(cands: List[Dict[str, Any]]) -> Dict[str, Any]:
    baseline = _preferred(cands)
    challengers = _challengers(cands, baseline)
    rejections: List[Dict[str, Any]] = []
    if baseline is None or not baseline.get("exists"):
        viable = [c for c in challengers if not c.get("critical_failure")]
        pool = viable or challengers
        if not pool:
            return {
                "selected": None,
                "selection_status": "UNRESOLVED_MISSING",
                "selection_reason_codes": ["NO_AVAILABLE_CANDIDATE"],
                "decision": "UNRESOLVED",
                "rejections": rejections,
            }
        best = max(pool, key=lambda c: float(c.get("score") or -1.0))
        return {
            "selected": best,
            "selection_status": "FALLBACK_NO_PREFERRED",
            "selection_reason_codes": ["PREFERRED_MISSING", "SELECTED_BEST_AVAILABLE"],
            "decision": "REPLACE",
            "baseline": None,
            "challenger": best.get("source_phase"),
            "rejections": rejections,
        }
    if not baseline.get("critical_failure") and not challengers:
        return {
            "selected": baseline,
            "selection_status": "RETAIN_PREFERRED",
            "selection_reason_codes": ["PREFERRED_BASELINE", "NO_DISTINCT_CHALLENGER"],
            "decision": "RETAIN",
            "baseline": PREFERRED_SOURCE,
            "rejections": rejections,
        }
    best_ok = None
    best_ok_reasons: List[str] = []
    best_ok_ev: Dict[str, Any] = {}
    for ch in challengers:
        ok, reasons, ev = _materially_better(baseline, ch)
        if not ok:
            rejections.append({
                "candidate": ch.get("source_phase"),
                "path": ch.get("path"),
                "rejection_reason": reasons,
                "baseline": PREFERRED_SOURCE,
                "critical_failure": ch.get("critical_failure"),
                "material_improvement": False,
                "evidence": ev,
            })
            continue
        if best_ok is None or float(ch.get("score") or -1) > float(best_ok.get("score") or -1):
            best_ok = ch
            best_ok_reasons = reasons
            best_ok_ev = ev
    if best_ok is None:
        status = "RETAIN_PREFERRED"
        codes = ["PREFERRED_BASELINE"]
        if baseline.get("critical_failure"):
            status = "RETAIN_PREFERRED_STILL_CRITICAL"
            codes = ["PREFERRED_BASELINE", "NO_NONCRITICAL_CHALLENGER"]
        elif challengers:
            codes.append("CHALLENGERS_REJECTED")
        return {
            "selected": baseline,
            "selection_status": status,
            "selection_reason_codes": codes,
            "decision": "RETAIN",
            "baseline": PREFERRED_SOURCE,
            "rejections": rejections,
        }
    return {
        "selected": best_ok,
        "selection_status": "REPLACE_PREFERRED",
        "selection_reason_codes": best_ok_reasons,
        "decision": "REPLACE",
        "baseline": PREFERRED_SOURCE,
        "challenger": best_ok.get("source_phase"),
        "material_improvement": best_ok_ev,
        "baseline_evidence": {
            "primary_status": baseline.get("primary_status"),
            "score": baseline.get("score"),
            "critical_failure": baseline.get("critical_failure"),
            "foreground_ratio": baseline.get("foreground_ratio"),
        },
        "challenger_evidence": {
            "primary_status": best_ok.get("primary_status"),
            "score": best_ok.get("score"),
            "critical_failure": best_ok.get("critical_failure"),
            "foreground_ratio": best_ok.get("foreground_ratio"),
        },
        "rejections": rejections,
    }


def select_beam(inventory: Dict[str, Any]) -> Dict[str, Any]:
    ctx = select_for_type(list(inventory.get("context_candidates") or []))
    det = select_for_type(list(inventory.get("detail_candidates") or []))
    return {"beam_id": inventory.get("beam_id"), "context": ctx, "detail": det}


__all__ = ["select_beam", "select_for_type"]
