"""
Expected engineering impact for the 5 recovery candidates (diagnostic only).
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import MODEL_VERSION, PHASE_ID


def candidate_impact(
    *,
    eligible_traces: List[Dict[str, Any]],
    eligible_policies: List[Dict[str, Any]],
    eligible_contam: List[Dict[str, Any]],
) -> Dict[str, Any]:
    by_key = {p["stable_key"]: p for p in eligible_policies}
    by_c = {c["stable_key"]: c for c in eligible_contam}

    per_policy = {p: [] for p in (
        "A_CURRENT", "B_CHAIN_EVIDENCE", "C_CHAIN_ENDPOINT",
        "D_CHAIN_GEOMETRIC", "E_STRONG_COMBINED",
    )}
    details = []
    ann_ids = set()
    bar_ids = set()
    for t in eligible_traces:
        sk = t["stable_key"]
        pr = (by_key.get(sk) or {}).get("policy_results") or {}
        risk = (by_c.get(sk) or {}).get("cross_beam_contamination_risk")
        for p, v in pr.items():
            if v and risk == "SAFE":
                per_policy[p].append(sk)
        if t.get("target_annotation"):
            ann_ids.add(t["target_annotation"])
        if t.get("associated_bar"):
            bar_ids.add(t["associated_bar"])
        for a in t.get("associated_annotations") or []:
            ann_ids.add(a)
        details.append(
            {
                "beam_id": t.get("beam_id"),
                "leader_id": t.get("leader_id"),
                "stable_key": sk,
                "associated_bar": t.get("associated_bar"),
                "associated_annotations": t.get("associated_annotations"),
                "contamination_risk": risk,
                "policy_results": pr,
            }
        )

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "label": "COUNTERFACTUAL IMPACT — NOT PRODUCTION",
        "potentially_recovered_leaders_by_policy_safe_only": {
            p: len(v) for p, v in per_policy.items()
        },
        "leader_ids_by_policy_safe_only": per_policy,
        "potentially_recovered_annotations_reachable": sorted(ann_ids),
        "potentially_recovered_annotation_count": len(ann_ids),
        "potentially_recovered_bars": sorted(bar_ids),
        "potentially_recovered_bar_count": len(bar_ids),
        "note": (
            "Do not convert to steel-quantity accuracy. "
            "Annotations become reachable only if a future production rule accepts the leader."
        ),
        "candidate_details": details,
    }
