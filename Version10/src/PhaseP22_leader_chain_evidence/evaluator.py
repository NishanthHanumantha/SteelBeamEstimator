"""
LeaderChainEvidenceEvaluator — controlled leader-chain evidence enhancement.
MODEL_VERSION: 10.5.4

Read-only during DIAGNOSTIC_ONLY. Identifies ACCEPT_CANDIDATE under Policy E
but never writes BeamOwnership unless ProductionGate.PRODUCTION_ENABLED is set
and write_beam_ownership is explicitly True (not enabled in P2.2).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Union

from .config import (
    DEFAULT_CONFIG,
    MODEL_VERSION,
    PHASE_ID,
    PRODUCTION_POLICY,
    EnhancedDecision,
    P22Config,
    ProductionGate,
)
from .policies import (
    anti_contamination_reject_reason,
    evaluate_policy_booleans,
    extract_evidence_flags,
    policy_e_reason,
)


@dataclass(frozen=True)
class LeaderEvidence:
    """Canonical evidence inputs for the evaluator (no invented thresholds)."""

    chain_continuity: bool
    bar_proximity: bool
    target_beam_context: bool
    endpoint_near_envelope: bool
    longitudinal_overlap: bool = False
    neighbour_ambiguity: bool = False
    inside_other_beam_envelope: bool = False
    transverse_alignment: bool = False

    def as_dict(self) -> Dict[str, bool]:
        return {
            "chain_continuity": self.chain_continuity,
            "bar_proximity": self.bar_proximity,
            "target_beam_context": self.target_beam_context,
            "endpoint_near_envelope": self.endpoint_near_envelope,
            "longitudinal_overlap": self.longitudinal_overlap,
            "neighbour_ambiguity": self.neighbour_ambiguity,
            "inside_other_beam_envelope": self.inside_other_beam_envelope,
            "transverse_alignment": self.transverse_alignment,
        }

    @classmethod
    def from_mapping(cls, evidence: Mapping[str, Any]) -> "LeaderEvidence":
        f = extract_evidence_flags(evidence)
        return cls(
            chain_continuity=f["chain_continuity"],
            bar_proximity=f["bar_proximity"],
            target_beam_context=f["target_beam_context"],
            endpoint_near_envelope=f["endpoint_near_envelope"],
            longitudinal_overlap=f["longitudinal_overlap"],
            neighbour_ambiguity=f["neighbour_ambiguity"],
            inside_other_beam_envelope=f["inside_other_beam_envelope"],
            transverse_alignment=f["transverse_alignment"],
        )


class LeaderChainEvidenceEvaluator:
    """
    Deterministic evidence evaluator independent of BeamOwnership writing.

    Principle: recover ownership from independent evidence, not relaxed geometry.
    """

    def __init__(self, config: Optional[P22Config] = None):
        self.config = config or DEFAULT_CONFIG

    @property
    def production_gate(self) -> ProductionGate:
        return self.config.production_gate

    def may_write_ownership(self) -> bool:
        return (
            self.config.production_gate == ProductionGate.PRODUCTION_ENABLED
            and bool(self.config.write_beam_ownership)
        )

    def evaluate_evidence(
        self,
        evidence: Union[Mapping[str, Any], LeaderEvidence],
        *,
        current_t18_accepted: bool = False,
        enhanced_policy: str = PRODUCTION_POLICY,
    ) -> Dict[str, Any]:
        """
        Evaluate evidence flags under policies A-E.

        Returns a structured decision object. Does not mutate ownership.
        """
        if isinstance(evidence, LeaderEvidence):
            ev = evidence.as_dict()
        else:
            ev = dict(evidence)

        flags = extract_evidence_flags(ev)
        policy_results = evaluate_policy_booleans(
            flags, current_t18_accepted=current_t18_accepted
        )
        policy = enhanced_policy or self.config.production_policy
        if policy not in policy_results:
            raise ValueError(f"Unknown enhanced_policy: {policy}")

        accepted = bool(policy_results[policy])
        reason = policy_e_reason(flags) if policy == PRODUCTION_POLICY else (
            "policy_accept" if accepted else "policy_reject"
        )
        if accepted and policy == PRODUCTION_POLICY:
            decision = EnhancedDecision.ACCEPT_CANDIDATE.value
        elif current_t18_accepted and policy == "A_CURRENT":
            decision = EnhancedDecision.CURRENT_T18.value
        else:
            decision = EnhancedDecision.REJECT.value

        hard = anti_contamination_reject_reason(flags)
        return {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "enhanced_policy": policy,
            "enhanced_decision": decision,
            "enhanced_reason": reason if accepted or policy == PRODUCTION_POLICY else (
                hard or "policy_reject"
            ),
            "policy_results": policy_results,
            "evidence_flags": flags,
            "anti_contamination_reject": hard,
            "production_gate": self.production_gate.value,
            "beam_ownership_written": False,
            "may_write_ownership": self.may_write_ownership(),
            "diagnostic_only": self.production_gate
            != ProductionGate.PRODUCTION_ENABLED,
            "label": self.config.label,
        }

    def decide_leader(
        self,
        *,
        beam_id: str,
        leader_id: str,
        stable_key: str,
        evidence: Union[Mapping[str, Any], LeaderEvidence],
        current_t18_decision: str,
        current_rejection_rule: Optional[str] = None,
        recovery_eligible: Optional[bool] = None,
        recovery_potential: Optional[str] = None,
        evidence_details: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Full structured decision record for one leader."""
        existing = str(current_t18_decision or "").upper()
        t18_accepted = existing == "ACCEPTED"
        core = self.evaluate_evidence(
            evidence,
            current_t18_accepted=t18_accepted,
            enhanced_policy=self.config.production_policy,
        )
        flags = core["evidence_flags"]
        return {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "beam_id": beam_id,
            "leader_id": leader_id,
            "stable_key": stable_key,
            "current_t18_decision": existing or "UNKNOWN",
            "current_rejection_rule": current_rejection_rule,
            "chain_continuity": flags["chain_continuity"],
            "bar_proximity": flags["bar_proximity"],
            "target_beam_context": flags["target_beam_context"],
            "endpoint_near_envelope": flags["endpoint_near_envelope"],
            "longitudinal_overlap": flags["longitudinal_overlap"],
            "neighbour_ambiguity": flags["neighbour_ambiguity"],
            "inside_other_beam_envelope": flags["inside_other_beam_envelope"],
            "enhanced_policy": core["enhanced_policy"],
            "enhanced_decision": core["enhanced_decision"],
            "enhanced_reason": core["enhanced_reason"],
            "recovery_eligible": recovery_eligible,
            "recovery_potential": recovery_potential,
            "policy_results": core["policy_results"],
            "evidence_details": dict(evidence_details or {}),
            "production_gate": core["production_gate"],
            "beam_ownership_written": False,
            "label": core["label"],
        }
