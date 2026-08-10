"""
Deterministic leader evidence scorecard (independent of T18 score).
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

from typing import Any, Dict

from PhaseQA41_dropped_entity_recovery_audit.geometry_helpers import SUPPORT_EXT_MM

from .config import MODEL_VERSION, PHASE_ID


def build_scorecard(trace: Dict[str, Any]) -> Dict[str, Any]:
    flags = trace.get("evidence_flags") or {}
    continuity = bool(
        flags.get("leader_chain_continuity")
        if flags.get("leader_chain_continuity") is not None
        else (trace.get("leader_start_point") and trace.get("leader_end_point_tip"))
    )
    bar_prox = bool(flags.get("leader_to_bar_proximity"))
    if not bar_prox and trace.get("bar_distance") is not None:
        bar_prox = float(trace["bar_distance"]) <= SUPPORT_EXT_MM

    dist = trace.get("distance_tip_to_envelope")
    endpoint_near = bool(flags.get("endpoint_near_envelope"))
    if not endpoint_near and dist is not None:
        endpoint_near = float(dist) <= SUPPORT_EXT_MM

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "beam_id": trace.get("beam_id"),
        "leader_id": trace.get("leader_id"),
        "stable_key": trace.get("stable_key"),
        "A_chain_continuity": continuity,
        "B_leader_to_bar_proximity": bar_prox,
        "C_target_beam_context": bool(trace.get("target_beam_context")),
        "D_endpoint_near_production_envelope": endpoint_near,
        "E_points_toward_target_beam": bool(trace.get("points_toward_target_beam")),
        "F_longitudinal_overlap": bool(trace.get("longitudinal_overlap")),
        "G_transverse_alignment": bool(trace.get("transverse_alignment")),
        "H_inside_another_beam_envelope": bool(trace.get("inside_other_beam_envelope")),
        "I_neighbour_ambiguity": bool(trace.get("neighbour_ambiguity")),
        "J_distance_from_envelope_mm": dist,
        "note": "Deterministic evidence scorecard — independent of T18 ownership score",
    }
