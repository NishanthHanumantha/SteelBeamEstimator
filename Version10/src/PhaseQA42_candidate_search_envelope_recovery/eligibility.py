"""
Recovery eligibility evaluator — evidence-supported gates only.
MODEL_VERSION: 10.5.1
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Set

from .config import CandidateRecoveryConfig, DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID


def evaluate_eligibility(
    audit_row: Dict[str, Any],
    *,
    config: CandidateRecoveryConfig = DEFAULT_CONFIG,
    owned_elsewhere_ids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Decide whether a QA.4.1 dropped entity is eligible for recovery candidate generation.

    Does NOT assign ownership.
    """
    owned_elsewhere_ids = owned_elsewhere_ids or set()
    flags = dict(audit_row.get("evidence_flags") or {})
    env = audit_row.get("envelope_audit") or {}
    potential = audit_row.get("recovery_potential")
    category = audit_row.get("primary_audit_category")
    entity_type = audit_row.get("entity_type")
    spatial = env.get("spatial_relationship")
    eid = str(audit_row.get("entity_id") or "")
    bid = str(audit_row.get("beam_id") or "")
    stable = str(audit_row.get("stable_key") or f"{bid}::{eid}")

    reasons = []
    eligible = True

    if category != config.target_audit_category:
        eligible = False
        reasons.append(f"category_not_{config.target_audit_category}")

    if potential not in config.allowed_recovery_potentials:
        eligible = False
        reasons.append(f"potential_not_in_allowed:{potential}")

    if spatial not in config.allowed_spatial_relationships:
        eligible = False
        reasons.append(f"spatial_not_allowed:{spatial}")

    if config.require_target_beam_context and not flags.get("target_beam_context"):
        eligible = False
        reasons.append("missing_target_beam_context")

    if config.require_longitudinal_overlap and not flags.get("longitudinal_overlap"):
        eligible = False
        reasons.append("missing_longitudinal_overlap")

    # Strong near-envelope evidence: near OR endpoint_near OR BOUNDARY (dist≈0)
    near_ok = bool(
        flags.get("near_production_envelope")
        or flags.get("endpoint_near_envelope")
        or spatial == "BOUNDARY"
    )
    if not near_ok:
        eligible = False
        reasons.append("missing_near_envelope_evidence")

    if config.reject_neighbour_ambiguity and flags.get("neighbour_ambiguity"):
        eligible = False
        reasons.append("neighbour_ambiguity")

    if config.reject_inside_other_beam_envelope and (
        flags.get("inside_other_beam_envelope")
        or env.get("inside_other_beam_envelopes")
    ):
        eligible = False
        reasons.append("inside_other_beam_envelope")

    if eid in owned_elsewhere_ids or f"{bid}::{eid}" in owned_elsewhere_ids:
        eligible = False
        reasons.append("owned_elsewhere")

    # Beam marks: eligible for confirmation-against-production only; not new recovery
    beam_mark = entity_type in config.exclude_entity_types_from_new_recovery

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "beam_id": bid,
        "entity_id": eid,
        "stable_key": stable,
        "entity_type": entity_type,
        "recovery_potential": potential,
        "primary_audit_category": category,
        "spatial_relationship": spatial,
        "min_distance_to_production_envelope": env.get(
            "min_distance_to_production_envelope"
        ),
        "evidence_flags": flags,
        "recovery_eligible": eligible,
        "recovery_exclusion_reason": None if eligible else ";".join(reasons) or "ineligible",
        "beam_mark_not_reinforcement": beam_mark,
        "near_envelope_evidence": near_ok,
        "longitudinal_overlap": bool(flags.get("longitudinal_overlap")),
        "transverse_alignment": bool(flags.get("transverse_alignment")),
        "beam_axis_alignment": bool(flags.get("beam_axis_alignment")),
        "endpoint_near_envelope": bool(flags.get("endpoint_near_envelope")),
        "target_beam_context": bool(flags.get("target_beam_context")),
        "neighbour_ambiguity": bool(flags.get("neighbour_ambiguity")),
        "inside_other_beam_envelope": bool(flags.get("inside_other_beam_envelope")),
    }
