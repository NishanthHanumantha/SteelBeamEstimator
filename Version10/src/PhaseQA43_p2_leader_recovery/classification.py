"""
Deterministic P2 recovery category classification from QA.4.1 evidence.
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def classify_recovery_category(audit_row: Dict[str, Any]) -> str:
    """Assign exactly one primary recovery category from observed evidence."""
    flags = audit_row.get("evidence_flags") or {}
    env = audit_row.get("envelope_audit") or {}
    leader = audit_row.get("leader_audit") or {}
    spatial = env.get("spatial_relationship")
    reason = str(audit_row.get("original_rejection_reason") or "").lower()
    pot = audit_row.get("recovery_potential")

    if flags.get("neighbour_ambiguity") or leader.get("failure_class") == "LEADER_TARGET_NEIGHBOUR":
        return "LEADER_NEIGHBOUR_AMBIGUITY"
    if flags.get("inside_other_beam_envelope") or env.get("inside_other_beam_envelopes"):
        return "LEADER_INSIDE_OTHER_BEAM"
    if spatial == "FAR_OUTSIDE":
        return "LEADER_FAR_OUTSIDE"
    if spatial == "BOUNDARY":
        return "LEADER_BOUNDARY"
    if spatial == "NEAR_OUTSIDE":
        return "LEADER_NEAR_OUTSIDE"
    if "tip_outside" in reason or leader.get("failure_class") == "LEADER_TIP_OUTSIDE":
        return "LEADER_OUTSIDE_PRODUCTION_ENVELOPE"
    if "filtered" in reason:
        return "LEADER_FILTERED_BEFORE_SCORING"
    if flags.get("target_beam_context") or leader.get("points_toward_target_beam"):
        return "LEADER_TARGET_CONTEXT"
    if pot == "HIGH":
        return "LEADER_NEAR_OUTSIDE"
    return "LEADER_NEVER_CANDIDATE"


def classify_potential_bucket(audit_row: Dict[str, Any]) -> str:
    pot = audit_row.get("recovery_potential")
    if pot in ("HIGH", "MEDIUM", "LOW"):
        return pot
    return "UNKNOWN"
