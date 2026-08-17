"""
Offline GT evaluation for P2.6.

MUST NOT be imported by runtime selection / Vision observation.
GT and estimator workbooks are evaluation-only.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PhaseP257_unseen_drawing_controlled_vision_validation.regression import (
    fifth_set_production_paths,
)

from .config import (
    DET_ALREADY,
    GT_AMBIGUOUS,
    GT_DUPLICATE,
    GT_MATCH,
    GT_TRUE_RECOVERY,
    GT_UNSUPPORTED,
    PRIMARY_DRAWING_SET,
)
from .deterministic_comparator import role_family

_QA2A_BOOTSTRAPPED = False


def _bootstrap_qa2a(version10_root: Path) -> None:
    global _QA2A_BOOTSTRAPPED
    if _QA2A_BOOTSTRAPPED:
        return
    v10 = Path(version10_root)
    qa2a = v10 / "src" / "PhaseQA.2A_ground_truth_benchmark"
    r14 = v10 / "src" / "PhaseR1_4_production_accuracy_benchmark"
    for p in (str(qa2a), str(r14)):
        if p not in sys.path:
            sys.path.insert(0, p)
    _QA2A_BOOTSTRAPPED = True


def _norm_id(raw: str) -> str:
    return str(raw or "").strip().upper().replace(" ", "").replace("_", "")


def _dia(v: Any) -> Optional[int]:
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def vision_family(role: Any) -> str:
    fam = role_family(role)
    if fam == "SIDE":
        return "SIDE"
    return fam


def gt_family(role: Any) -> str:
    r = str(role or "").upper()
    if r.startswith("TOP"):
        return "TOP"
    if r.startswith("BOTTOM"):
        return "BOTTOM"
    if "STIRRUP" in r or "HOOK" in r:
        return "STIRRUP"
    if "SIDE" in r or r in ("SFR",):
        return "SIDE"
    if "SPACER" in r:
        return "SPACER"
    return role_family(r)


def load_gt_universe(version10_root: Path) -> Dict[str, Any]:
    """Load estimator GT bars and model-detected bars. Evaluation only."""
    _bootstrap_qa2a(version10_root)
    from bar_matcher import BarMatcher  # type: ignore
    from workbook_normalizer import WorkbookNormalizer  # type: ignore

    paths = fifth_set_production_paths(version10_root)
    est_path = paths.get("fifth_estimator_excel")
    model_path = paths.get("fifth_model_excel")
    if est_path is None or not Path(est_path).exists():
        raise FileNotFoundError("Fifth Set estimator workbook not found (evaluation-only)")
    if model_path is None or not Path(model_path).exists():
        raise FileNotFoundError("Fifth Set model workbook not found (evaluation-only)")

    norm = WorkbookNormalizer()
    est = norm.normalize(Path(est_path), "estimator")
    model = norm.normalize(Path(model_path), "model")
    matcher = BarMatcher()

    est_by = {_norm_id(b.beam_id): b for b in (est.beams or [])}
    mod_by = {_norm_id(b.beam_id): b for b in (model.beams or [])}

    missed: Dict[str, List[Dict[str, Any]]] = {}
    all_gt: Dict[str, List[Dict[str, Any]]] = {}
    for bid, eb in est_by.items():
        mb = mod_by.get(bid)
        gt_rows = []
        for bar in eb.bars or []:
            gt_rows.append(
                {
                    "beam_id": bid,
                    "bar_role": bar.bar_role,
                    "family": gt_family(bar.bar_role),
                    "diameter": _dia(bar.diameter),
                    "quantity": bar.quantity,
                    "used": False,
                }
            )
        all_gt[bid] = gt_rows
        missed_rows: List[Dict[str, Any]] = []
        if mb is None:
            for row in gt_rows:
                missed_rows.append(dict(row))
        else:
            result = matcher.match_beam_bars(PRIMARY_DRAWING_SET, eb, mb)
            for row in result.get("rows") or []:
                if row.get("status") == "MISSING" and row.get("bar_role"):
                    missed_rows.append(
                        {
                            "beam_id": bid,
                            "bar_role": row.get("bar_role"),
                            "family": gt_family(row.get("bar_role")),
                            "diameter": _dia(row.get("diameter")),
                            "quantity": row.get("estimator_qty") or row.get("quantity"),
                            "used": False,
                        }
                    )
        missed[bid] = missed_rows

    return {
        "estimator_path": str(est_path),
        "model_path": str(model_path),
        "gt_bars": all_gt,
        "missed_bars": missed,
        "gt_used_at_runtime": False,
    }


def _best_unused(
    cand: Dict[str, Any],
    pool: List[Dict[str, Any]],
) -> Tuple[Optional[int], str]:
    fam = vision_family(cand.get("role"))
    dia = _dia(cand.get("diameter_mm"))
    qty = cand.get("quantity")
    best_i = None
    best_score = -1.0
    for i, g in enumerate(pool):
        if g.get("used"):
            continue
        fam_ok = fam != "UNKNOWN" and g.get("family") == fam
        dia_ok = dia is not None and g.get("diameter") is not None and dia == g["diameter"]
        qty_ok = False
        try:
            if qty is not None and g.get("quantity") is not None:
                qty_ok = abs(float(qty) - float(g["quantity"])) <= max(0.5, 0.05 * max(float(qty), float(g["quantity"])))
        except (TypeError, ValueError):
            qty_ok = False
        if fam_ok and dia_ok and qty_ok:
            score = 3.0
        elif fam_ok and dia_ok:
            score = 2.0
        elif fam_ok and dia is None:
            score = 0.8
        elif dia_ok and fam == "UNKNOWN":
            score = 0.6
        else:
            continue
        if score > best_score:
            best_score = score
            best_i = i
    if best_i is None:
        return None, "NONE"
    if best_score >= 2.0:
        return best_i, "FAMILY_DIAMETER"
    if best_score >= 0.8:
        return best_i, "WEAK"
    return None, "NONE"


def evaluate_candidate(
    candidate: Dict[str, Any],
    *,
    universe: Dict[str, Any],
) -> Dict[str, Any]:
    bid = _norm_id(candidate.get("beam_id") or "")
    missed_live = (universe.get("missed_bars") or {}).setdefault(bid, [])
    gt_live = (universe.get("gt_bars") or {}).setdefault(bid, [])
    assoc = str(candidate.get("beam_association") or "UNCERTAIN")
    det = str(candidate.get("deterministic_match_status") or "")
    miss_i, miss_how = _best_unused(candidate, missed_live)
    gt_i, gt_how = _best_unused(candidate, gt_live)

    association_failure = assoc == "OTHER_BEAM"
    weak = miss_how == "WEAK" or gt_how == "WEAK"

    if association_failure:
        status = GT_AMBIGUOUS
        reason = "ASSOCIATION_FAILURE"
    elif miss_how == "FAMILY_DIAMETER" and det != DET_ALREADY:
        status = GT_TRUE_RECOVERY
        reason = "MATCHES_MISSED_GT"
        missed_live[miss_i]["used"] = True
        if gt_i is not None:
            gt_live[gt_i]["used"] = True
    elif det == DET_ALREADY:
        status = GT_DUPLICATE
        reason = "ALREADY_DETECTED_DETERMINISTIC"
        if gt_i is not None and gt_how == "FAMILY_DIAMETER":
            gt_live[gt_i]["used"] = True
    elif gt_how == "FAMILY_DIAMETER":
        status = GT_MATCH
        reason = "MATCHES_GT_NOT_CLASSIFIED_MISSING"
        gt_live[gt_i]["used"] = True
    elif assoc == "UNCERTAIN" or weak:
        status = GT_AMBIGUOUS
        reason = "UNCERTAIN_OR_WEAK_EVIDENCE"
    else:
        status = GT_UNSUPPORTED
        reason = "NO_GT_SUPPORT"

    gt_supported = status in (GT_TRUE_RECOVERY, GT_MATCH) or (
        status == GT_DUPLICATE and gt_how == "FAMILY_DIAMETER"
    )
    rec = dict(candidate)
    rec["gt_match_status"] = status
    rec["gt_match_reason"] = reason
    rec["gt_supported"] = gt_supported
    rec["association_failure"] = association_failure
    rec["gt_used_at_runtime"] = False
    return rec


def evaluate_candidates(
    candidates: List[Dict[str, Any]],
    *,
    universe: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return [evaluate_candidate(c, universe=universe) for c in candidates]


def missed_count_for_beams(universe: Dict[str, Any], beam_ids: List[str]) -> int:
    n = 0
    missed = universe.get("missed_bars") or {}
    for bid in beam_ids:
        n += len(missed.get(_norm_id(bid)) or [])
    return n


__all__ = [
    "evaluate_candidate",
    "evaluate_candidates",
    "load_gt_universe",
    "missed_count_for_beams",
]
