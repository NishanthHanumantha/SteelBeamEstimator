"""Repeatability metrics. Evaluation only."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import SEM_AMBIGUOUS, SEM_DISTINCT, SEM_DUPLICATE


def _pair_key(row: Dict[str, Any]) -> Tuple[Any, Any]:
    return row.get("set_key"), row.get("beam_id")


def _dec(obs: Optional[Dict[str, Any]]) -> Optional[str]:
    if not obs or not obs.get("ok"):
        return None
    payload = obs.get("payload") or {}
    return payload.get("decision")


def _conf(obs: Optional[Dict[str, Any]]) -> Optional[float]:
    if not obs or not obs.get("ok"):
        return None
    payload = obs.get("payload") or {}
    try:
        return float(payload.get("confidence"))
    except (TypeError, ValueError):
        return None


def compute_repeatability(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    paired = 0
    agree = 0
    layer_agree = 0
    layer_n = 0
    rep_agree = 0
    rep_n = 0
    conf_deltas: List[float] = []
    transitions = {
        "DISTINCT_DUPLICATE": 0,
        "DUPLICATE_DISTINCT": 0,
        "DISTINCT_AMBIGUOUS": 0,
        "DUPLICATE_AMBIGUOUS": 0,
        "AMBIGUOUS_DISTINCT": 0,
        "AMBIGUOUS_DUPLICATE": 0,
        "other": 0,
    }
    amb_transition = 0
    for rec in records:
        a = _dec(rec.get("primary"))
        b = _dec(rec.get("repeat"))
        if a is None or b is None:
            continue
        paired += 1
        if a == b:
            agree += 1
        elif a == SEM_DISTINCT and b == SEM_DUPLICATE:
            transitions["DISTINCT_DUPLICATE"] += 1
        elif a == SEM_DUPLICATE and b == SEM_DISTINCT:
            transitions["DUPLICATE_DISTINCT"] += 1
        elif a == SEM_DISTINCT and b == SEM_AMBIGUOUS:
            transitions["DISTINCT_AMBIGUOUS"] += 1
            amb_transition += 1
        elif a == SEM_DUPLICATE and b == SEM_AMBIGUOUS:
            transitions["DUPLICATE_AMBIGUOUS"] += 1
            amb_transition += 1
        elif a == SEM_AMBIGUOUS and b == SEM_DISTINCT:
            transitions["AMBIGUOUS_DISTINCT"] += 1
            amb_transition += 1
        elif a == SEM_AMBIGUOUS and b == SEM_DUPLICATE:
            transitions["AMBIGUOUS_DUPLICATE"] += 1
            amb_transition += 1
        else:
            transitions["other"] += 1
        pa = (rec.get("primary") or {}).get("payload") or {}
        pb = (rec.get("repeat") or {}).get("payload") or {}
        if pa.get("target_layer") and pb.get("target_layer"):
            layer_n += 1
            if pa.get("target_layer") == pb.get("target_layer"):
                layer_agree += 1
        if pa.get("existing_representation_assessment") and pb.get("existing_representation_assessment"):
            rep_n += 1
            if pa.get("existing_representation_assessment") == pb.get("existing_representation_assessment"):
                rep_agree += 1
        ca, cb = _conf(rec.get("primary")), _conf(rec.get("repeat"))
        if ca is not None and cb is not None:
            conf_deltas.append(abs(ca - cb))
    rate = (agree / paired) if paired else None
    return {
        "valid_paired_cases": paired,
        "exact_semantic_decision_agreement": agree,
        "semantic_repeatability_rate": rate,
        "layer_agreement_rate": (layer_agree / layer_n) if layer_n else None,
        "representation_assessment_agreement_rate": (rep_agree / rep_n) if rep_n else None,
        "mean_confidence_delta": (sum(conf_deltas) / len(conf_deltas)) if conf_deltas else None,
        "ambiguity_transition_rate": (amb_transition / paired) if paired else None,
        "DISTINCT_to_DUPLICATE": transitions["DISTINCT_DUPLICATE"],
        "DUPLICATE_to_DISTINCT": transitions["DUPLICATE_DISTINCT"],
        "DISTINCT_to_AMBIGUOUS": transitions["DISTINCT_AMBIGUOUS"],
        "DUPLICATE_to_AMBIGUOUS": transitions["DUPLICATE_AMBIGUOUS"],
        "AMBIGUOUS_to_DISTINCT": transitions["AMBIGUOUS_DISTINCT"],
        "AMBIGUOUS_to_DUPLICATE": transitions["AMBIGUOUS_DUPLICATE"],
        "other_transitions": transitions["other"],
    }


def critical_repeatability(records: List[Dict[str, Any]], keys: List[Tuple[str, str]]) -> Dict[str, Any]:
    by = {_pair_key(r): r for r in records}
    n = 0
    agree = 0
    rows = []
    for key in keys:
        rec = by.get(key) or {}
        a = _dec(rec.get("primary"))
        b = _dec(rec.get("repeat"))
        ok = a is not None and b is not None
        if ok:
            n += 1
            if a == b:
                agree += 1
        rows.append(
            {
                "set_key": key[0],
                "beam_id": key[1],
                "primary": a,
                "repeat": b,
                "agree": bool(ok and a == b),
            }
        )
    return {
        "valid_paired_cases": n,
        "agreement": agree,
        "critical_case_repeatability": (agree / n) if n else None,
        "rows": rows,
    }


__all__ = ["compute_repeatability", "critical_repeatability"]
