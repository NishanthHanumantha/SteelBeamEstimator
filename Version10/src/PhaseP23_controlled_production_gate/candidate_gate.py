"""
P2.3 production candidate gate — fail-closed, Policy E only.
MODEL_VERSION: 10.5.5

Reuses P2.2 decisions; does not re-implement Policy E boolean logic.
Re-checks anti-contamination flags fail-closed before admitting a candidate.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import MODEL_VERSION, PHASE_ID, PRODUCTION_POLICY


def _fail_closed_ok(c: Dict[str, Any]) -> Tuple[bool, str]:
    if c.get("enhanced_policy") != PRODUCTION_POLICY:
        return False, "policy_not_E_STRONG_COMBINED"
    if c.get("enhanced_decision") != "ACCEPT_CANDIDATE":
        return False, "not_ACCEPT_CANDIDATE"
    if c.get("neighbour_ambiguity"):
        return False, "neighbour_ambiguity"
    if c.get("inside_other_beam_envelope"):
        return False, "inside_other_beam_envelope"
    if not c.get("chain_continuity"):
        return False, "missing_chain_continuity"
    if not c.get("bar_proximity"):
        return False, "missing_bar_proximity"
    if not c.get("target_beam_context"):
        return False, "missing_target_beam_context"
    if not (c.get("endpoint_near_envelope") or c.get("longitudinal_overlap")):
        return False, "missing_endpoint_or_longitudinal"
    # Explicitly reject Policy D production path
    pr = c.get("policy_results") or {}
    if pr.get("D_CHAIN_GEOMETRIC") and not pr.get(PRODUCTION_POLICY):
        return False, "policy_D_only_not_production"
    return True, "ok"


def load_p22_candidates(p22_root) -> Dict[str, Any]:
    from pathlib import Path
    import json

    p22_root = Path(p22_root)
    prod = json.loads(
        (p22_root / "ProductionCandidates.json").read_text(encoding="utf-8")
    )
    decisions = json.loads(
        (p22_root / "LeaderChainDecisions.json").read_text(encoding="utf-8")
    )
    return {"production_candidates": prod, "decisions": decisions}


def select_controlled_candidates(
    *,
    p22_production: Dict[str, Any],
    p22_decisions: Dict[str, Any],
    recovery_enabled: bool,
) -> Dict[str, Any]:
    """
    Select candidates for controlled effective ownership.

    Only P2.2 E_STRONG_COMBINED + ACCEPT_CANDIDATE with fail-closed checks.
    """
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    # Prefer ProductionCandidates list; fall back to decisions with ACCEPT_CANDIDATE
    raw = list((p22_production or {}).get("candidates") or [])
    if not raw:
        raw = [
            d
            for d in ((p22_decisions or {}).get("decisions") or [])
            if d.get("enhanced_decision") == "ACCEPT_CANDIDATE"
        ]

    for c in sorted(
        raw,
        key=lambda r: (
            str(r.get("beam_id") or ""),
            str(r.get("leader_id") or ""),
            str(r.get("stable_key") or ""),
        ),
    ):
        row = dict(c)
        if not recovery_enabled:
            row["gate_accepted"] = False
            row["gate_reason"] = "LEADER_CHAIN_RECOVERY_ENABLED=FALSE"
            rejected.append(row)
            continue
        ok, reason = _fail_closed_ok(c)
        row["gate_accepted"] = ok
        row["gate_reason"] = reason
        row["source"] = "P2.2"
        row["recovery_policy"] = PRODUCTION_POLICY
        if ok:
            accepted.append(row)
        else:
            rejected.append(row)

    # Also catalogue all non-E decisions as rejected for audit
    seen = {r.get("stable_key") for r in accepted + rejected}
    for d in (p22_decisions or {}).get("decisions") or []:
        sk = d.get("stable_key")
        if sk in seen:
            continue
        if d.get("enhanced_decision") == "ACCEPT_CANDIDATE":
            continue
        rejected.append(
            {
                **d,
                "gate_accepted": False,
                "gate_reason": "not_ACCEPT_CANDIDATE_or_not_policy_E",
                "source": "P2.2",
                "recovery_policy": d.get("enhanced_policy"),
            }
        )

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "leader_chain_recovery_policy": PRODUCTION_POLICY,
        "leader_chain_recovery_enabled": recovery_enabled,
        "accepted": accepted,
        "rejected": rejected,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted_keys": [a.get("stable_key") for a in accepted],
    }
