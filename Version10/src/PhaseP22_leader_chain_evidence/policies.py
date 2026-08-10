"""
Explicit leader-chain acceptance policy definitions for P2.2.
MODEL_VERSION: 10.5.4

A–D remain diagnostic comparison policies.
E_STRONG_COMBINED is the only policy eligible for production-candidate
consideration. D must never become the production default.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .config import MODEL_VERSION, PHASE_ID, PRODUCTION_POLICY


POLICY_DEFS: Dict[str, Dict[str, str]] = {
    "A_CURRENT": {
        "label": "CURRENT - exact T18 behaviour",
        "description": "Reproduce existing T18 / R2_LEADER_TIP outcome",
        "production_eligible": "false",
    },
    "B_CHAIN_EVIDENCE": {
        "label": "CHAIN EVIDENCE",
        "description": "continuity AND bar proximity AND target beam context",
        "production_eligible": "false",
    },
    "C_CHAIN_ENDPOINT": {
        "label": "CHAIN + ENDPOINT",
        "description": "B plus endpoint near envelope",
        "production_eligible": "false",
    },
    "D_CHAIN_GEOMETRIC": {
        "label": "CHAIN + GEOMETRIC ALIGNMENT",
        "description": "continuity + context + long/transverse + no neighbour risk (diagnostic only)",
        "production_eligible": "false",
    },
    "E_STRONG_COMBINED": {
        "label": "STRONG COMBINED EVIDENCE",
        "description": (
            "chain+context+bar AND (endpoint OR long overlap) "
            "AND no neighbour risk AND not inside other beam"
        ),
        "production_eligible": "true",
    },
}


def _as_bool(evidence: Mapping[str, Any], *keys: str) -> bool:
    for key in keys:
        if key in evidence and evidence[key] is not None:
            return bool(evidence[key])
    return False


def extract_evidence_flags(evidence: Mapping[str, Any]) -> Dict[str, bool]:
    """Normalise scorecard / raw evidence into canonical boolean flags."""
    return {
        "chain_continuity": _as_bool(
            evidence, "chain_continuity", "A_chain_continuity", "leader_chain_continuity"
        ),
        "bar_proximity": _as_bool(
            evidence,
            "bar_proximity",
            "B_leader_to_bar_proximity",
            "leader_to_bar_proximity",
        ),
        "target_beam_context": _as_bool(
            evidence, "target_beam_context", "C_target_beam_context"
        ),
        "endpoint_near_envelope": _as_bool(
            evidence,
            "endpoint_near_envelope",
            "D_endpoint_near_production_envelope",
            "endpoint_near_production_envelope",
        ),
        "longitudinal_overlap": _as_bool(
            evidence, "longitudinal_overlap", "F_longitudinal_overlap"
        ),
        "transverse_alignment": _as_bool(
            evidence, "transverse_alignment", "G_transverse_alignment"
        ),
        "neighbour_ambiguity": _as_bool(
            evidence, "neighbour_ambiguity", "I_neighbour_ambiguity"
        ),
        "inside_other_beam_envelope": _as_bool(
            evidence,
            "inside_other_beam_envelope",
            "H_inside_another_beam_envelope",
            "inside_another_beam_envelope",
        ),
    }


def evaluate_policy_booleans(
    evidence: Mapping[str, Any],
    *,
    current_t18_accepted: bool = False,
) -> Dict[str, bool]:
    """
    Evaluate policies A–E from evidence flags.

    Pure / deterministic. No magic distance thresholds are introduced here.
    """
    f = extract_evidence_flags(evidence)
    cont = f["chain_continuity"]
    bar = f["bar_proximity"]
    ctx = f["target_beam_context"]
    endp = f["endpoint_near_envelope"]
    longi = f["longitudinal_overlap"]
    trans = f["transverse_alignment"]
    nbr = f["neighbour_ambiguity"]
    inside = f["inside_other_beam_envelope"]

    A = bool(current_t18_accepted)
    B = cont and bar and ctx
    C = cont and bar and ctx and endp
    D = cont and ctx and longi and trans and (not nbr) and (not inside)
    E = (
        cont
        and ctx
        and bar
        and (endp or longi)
        and (not nbr)
        and (not inside)
    )
    return {
        "A_CURRENT": A,
        "B_CHAIN_EVIDENCE": B,
        "C_CHAIN_ENDPOINT": C,
        "D_CHAIN_GEOMETRIC": D,
        "E_STRONG_COMBINED": E,
    }


def anti_contamination_reject_reason(evidence: Mapping[str, Any]) -> Optional[str]:
    """
    Mandatory hard rejection conditions for enhanced recovery.
    Returns reason code or None if anti-contamination gates pass.
    """
    f = extract_evidence_flags(evidence)
    if f["neighbour_ambiguity"]:
        return "reject_neighbour_ambiguity"
    if f["inside_other_beam_envelope"]:
        return "reject_inside_other_beam_envelope"
    if not f["chain_continuity"]:
        return "reject_missing_chain_continuity"
    if not f["target_beam_context"]:
        return "reject_missing_target_beam_context"
    if not f["bar_proximity"]:
        return "reject_missing_bar_proximity"
    return None


def policy_e_reason(evidence: Mapping[str, Any]) -> str:
    """Explainable reason string for Policy E accept/reject."""
    f = extract_evidence_flags(evidence)
    hard = anti_contamination_reject_reason(evidence)
    if hard:
        return hard
    if not (f["endpoint_near_envelope"] or f["longitudinal_overlap"]):
        return "reject_missing_endpoint_or_longitudinal_evidence"
    return "strong_chain_bar_context_with_endpoint_or_longitudinal_evidence"


def policy_catalog() -> Dict[str, Any]:
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "production_policy": PRODUCTION_POLICY,
        "policy_definitions": POLICY_DEFS,
        "note": (
            "Only E_STRONG_COMBINED is eligible for production-candidate "
            "consideration. D_CHAIN_GEOMETRIC is diagnostic comparison only."
        ),
    }
