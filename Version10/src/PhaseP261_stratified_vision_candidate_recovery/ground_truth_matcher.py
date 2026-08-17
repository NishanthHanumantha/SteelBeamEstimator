"""
Offline GT evaluation for P2.6.1. Multi-set. Evaluation only.

MUST NOT be imported by sampler / Vision observation.
Primary TRUE_RECOVERY uses P2.6 family+diameter matching.
A stricter family+diameter+quantity metric is reported separately.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP26_vision_candidate_recovery.deterministic_comparator import (
    apply_comparison as p26_apply_comparison,
)
from PhaseP26_vision_candidate_recovery.ground_truth_matcher import (
    _dia,
    _norm_id,
    evaluate_candidate as p26_evaluate_candidate,
    gt_family,
)

from .config import (
    DET_AMBIGUOUS,
    GT_AMBIGUOUS,
    GT_TRUE_RECOVERY,
    SET_KEYS,
)
from .eval_artefacts import estimator_excel_path
from .set_artefacts import drawing_set_name, production_paths

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


def _set_key_from_name(name: str) -> str:
    s = str(name or "")
    for key in SET_KEYS:
        if key.lower() in s.lower():
            return key
    return s.replace(" Set Drawings", "").strip() or "Unknown"


def universe_key(set_key: str, beam_id: str) -> str:
    return f"{set_key}::{_norm_id(beam_id)}"


def load_gt_universe(version10_root: Path) -> Dict[str, Any]:
    _bootstrap_qa2a(version10_root)
    from bar_matcher import BarMatcher  # type: ignore
    from workbook_normalizer import WorkbookNormalizer  # type: ignore

    norm = WorkbookNormalizer()
    matcher = BarMatcher()
    gt_bars: Dict[str, List[Dict[str, Any]]] = {}
    missed: Dict[str, List[Dict[str, Any]]] = {}
    paths_used: Dict[str, Dict[str, str]] = {}

    for set_key in SET_KEYS:
        paths = production_paths(version10_root, set_key)
        est_path = estimator_excel_path(version10_root, set_key)
        model_path = paths.get("model_excel")
        if not Path(est_path).exists():
            continue
        if model_path is None or not Path(model_path).exists():
            continue
        est = norm.normalize(Path(est_path), "estimator")
        model = norm.normalize(Path(model_path), "model")
        est_by = {_norm_id(b.beam_id): b for b in (est.beams or [])}
        mod_by = {_norm_id(b.beam_id): b for b in (model.beams or [])}
        paths_used[set_key] = {"estimator": str(est_path), "model": str(model_path)}
        drawing = drawing_set_name(set_key)
        for bid, eb in est_by.items():
            uk = universe_key(set_key, bid)
            gt_rows = []
            for bar in eb.bars or []:
                gt_rows.append(
                    {
                        "beam_id": bid,
                        "set_key": set_key,
                        "bar_role": bar.bar_role,
                        "family": gt_family(bar.bar_role),
                        "diameter": _dia(bar.diameter),
                        "quantity": bar.quantity,
                        "used": False,
                    }
                )
            gt_bars[uk] = gt_rows
            mb = mod_by.get(bid)
            missed_rows: List[Dict[str, Any]] = []
            if mb is None:
                missed_rows = [dict(x) for x in gt_rows]
            else:
                result = matcher.match_beam_bars(drawing, eb, mb)
                for row in result.get("rows") or []:
                    if row.get("status") == "MISSING" and row.get("bar_role"):
                        missed_rows.append(
                            {
                                "beam_id": bid,
                                "set_key": set_key,
                                "bar_role": row.get("bar_role"),
                                "family": gt_family(row.get("bar_role")),
                                "diameter": _dia(row.get("diameter")),
                                "quantity": row.get("estimator_qty") or row.get("quantity"),
                                "used": False,
                            }
                        )
            missed[uk] = missed_rows

    return {
        "gt_bars": gt_bars,
        "missed_bars": missed,
        "paths": paths_used,
        "gt_used_at_runtime": False,
    }


def apply_comparison(candidates: List[Dict[str, Any]], *, r13_model: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = p26_apply_comparison(candidates, r13_model=r13_model)
    for rec in out:
        assoc = str(rec.get("beam_association") or "UNCERTAIN")
        if assoc in ("OTHER_BEAM", "UNCERTAIN"):
            rec["deterministic_match_status"] = DET_AMBIGUOUS
            rec["deterministic_match_reason"] = f"ASSOCIATION_{assoc}"
        rec["decision"] = "SHADOW_CANDIDATE"
    return out


def evaluate_candidate(candidate: Dict[str, Any], *, universe: Dict[str, Any]) -> Dict[str, Any]:
    set_key = _set_key_from_name(candidate.get("source_set") or "")
    bid = _norm_id(candidate.get("beam_id") or "")
    uk = universe_key(set_key, bid)
    scoped = {
        "missed_bars": {bid: list((universe.get("missed_bars") or {}).get(uk) or [])},
        "gt_bars": {bid: list((universe.get("gt_bars") or {}).get(uk) or [])},
    }
    rec = p26_evaluate_candidate(candidate, universe=scoped)
    (universe.get("missed_bars") or {})[uk] = scoped["missed_bars"].get(bid) or []
    (universe.get("gt_bars") or {})[uk] = scoped["gt_bars"].get(bid) or []

    assoc = str(candidate.get("beam_association") or "UNCERTAIN")
    if assoc in ("OTHER_BEAM", "UNCERTAIN") and rec.get("gt_match_status") == GT_TRUE_RECOVERY:
        rec["gt_match_status"] = GT_AMBIGUOUS
        rec["gt_match_reason"] = "INVALID_OR_UNCERTAIN_ASSOCIATION"
        rec["p26_compatible_true_recovery"] = False
        rec["strict_true_recovery"] = False
        rec["gt_supported"] = False
        rec["gt_used_at_runtime"] = False
        rec["universe_key"] = uk
        return rec

    strict = False
    if rec.get("gt_match_status") == GT_TRUE_RECOVERY:
        qty = candidate.get("quantity")
        for g in scoped["missed_bars"].get(bid) or []:
            if not g.get("used"):
                continue
            try:
                if qty is not None and g.get("quantity") is not None:
                    if abs(float(qty) - float(g["quantity"])) <= max(
                        0.5, 0.05 * max(float(qty), float(g["quantity"]))
                    ):
                        strict = True
                        break
            except (TypeError, ValueError):
                continue
        # Stirrups with no quantity remain P2.6-compatible (family+diameter) only.
        # Presence of legs/spacing is not a stricter GT match.

    rec["strict_true_recovery"] = bool(strict)
    rec["p26_compatible_true_recovery"] = rec.get("gt_match_status") == GT_TRUE_RECOVERY
    rec["gt_used_at_runtime"] = False
    rec["universe_key"] = uk
    return rec


def evaluate_candidates(candidates: List[Dict[str, Any]], *, universe: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [evaluate_candidate(c, universe=universe) for c in candidates]


def missed_count_for_keys(universe: Dict[str, Any], keys: List[str]) -> int:
    missed = universe.get("missed_bars") or {}
    return sum(len(missed.get(k) or []) for k in keys)


__all__ = [
    "apply_comparison",
    "evaluate_candidate",
    "evaluate_candidates",
    "load_gt_universe",
    "missed_count_for_keys",
    "universe_key",
]
