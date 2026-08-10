"""
P2 leader recovery eligibility — evidence gates only.
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Set

from .classification import classify_potential_bucket, classify_recovery_category
from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID, LeaderRecoveryConfig


def evaluate_eligibility(
    audit_row: Dict[str, Any],
    *,
    config: LeaderRecoveryConfig = DEFAULT_CONFIG,
    owned_elsewhere_ids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    owned_elsewhere_ids = owned_elsewhere_ids or set()
    flags = dict(audit_row.get("evidence_flags") or {})
    env = audit_row.get("envelope_audit") or {}
    leader = audit_row.get("leader_audit") or {}
    # Merge leader evidence into flags when present
    for k in (
        "leader_chain_continuity",
        "leader_to_bar_proximity",
        "near_production_envelope",
        "target_beam_context",
        "neighbour_ambiguity",
    ):
        if k in (leader.get("evidence_flags") or {}) and k not in flags:
            flags[k] = leader["evidence_flags"][k]
    if leader.get("points_toward_target_beam") and not flags.get("target_beam_context"):
        flags["target_beam_context"] = True

    spatial = env.get("spatial_relationship")
    tip_dist = leader.get("terminal_distance_to_production_envelope")
    if tip_dist is None:
        tip_dist = env.get("min_distance_to_production_envelope")

    pot = classify_potential_bucket(audit_row)
    category = classify_recovery_category(audit_row)
    eid = str(audit_row.get("entity_id") or "")
    bid = str(audit_row.get("beam_id") or "")
    stable = str(audit_row.get("stable_key") or f"{bid}::{eid}")

    reasons = []
    eligible = True

    if audit_row.get("primary_audit_category") != config.target_audit_category:
        eligible = False
        reasons.append("not_leader_chain_failure")

    if pot not in config.candidate_emission_potentials:
        eligible = False
        reasons.append(f"potential_not_emitted:{pot}")

    if spatial == "FAR_OUTSIDE" and config.reject_far_outside:
        eligible = False
        reasons.append("far_outside")

    if spatial and spatial not in config.allowed_spatial_for_emission:
        eligible = False
        reasons.append(f"spatial_not_allowed:{spatial}")

    if config.reject_neighbour_ambiguity and flags.get("neighbour_ambiguity"):
        eligible = False
        reasons.append("neighbour_ambiguity")

    if config.reject_inside_other_beam_envelope and (
        flags.get("inside_other_beam_envelope") or env.get("inside_other_beam_envelopes")
    ):
        eligible = False
        reasons.append("inside_other_beam_envelope")

    if eid in owned_elsewhere_ids or f"{bid}::{eid}" in owned_elsewhere_ids:
        eligible = False
        reasons.append("owned_elsewhere")

    # MEDIUM without any target-beam / near-envelope evidence stays diagnostic
    if pot == "MEDIUM" and not (
        flags.get("target_beam_context")
        or flags.get("near_production_envelope")
        or flags.get("leader_to_bar_proximity")
        or flags.get("endpoint_near_envelope")
        or (tip_dist is not None and tip_dist <= config.support_ext_mm * 2)
    ):
        eligible = False
        reasons.append("medium_insufficient_leader_evidence")

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "beam_id": bid,
        "entity_id": eid,
        "stable_key": stable,
        "entity_type": audit_row.get("entity_type"),
        "recovery_category": category,
        "recovery_potential": pot,
        "spatial_relationship": spatial,
        "min_distance_to_production_envelope": tip_dist,
        "longitudinal_overlap": bool(flags.get("longitudinal_overlap")),
        "transverse_alignment": bool(flags.get("transverse_alignment")),
        "beam_axis_alignment": bool(flags.get("beam_axis_alignment")),
        "endpoint_near_envelope": bool(flags.get("endpoint_near_envelope")),
        "target_beam_context": bool(flags.get("target_beam_context")),
        "neighbour_ambiguity": bool(flags.get("neighbour_ambiguity")),
        "inside_other_beam_envelope": bool(flags.get("inside_other_beam_envelope")),
        "leader_chain_continuity": bool(flags.get("leader_chain_continuity")),
        "leader_to_bar_proximity": bool(flags.get("leader_to_bar_proximity")),
        "points_toward_target_beam": leader.get("points_toward_target_beam"),
        "failure_class": leader.get("failure_class"),
        "recovery_eligible": eligible,
        "recovery_exclusion_reason": None if eligible else ";".join(reasons) or "ineligible",
        "evidence_flags": flags,
    }
