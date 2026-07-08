"""Deterministic recovery decision engine."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.engineering_recovery.recovery_candidate_builder import (
    NON_RECOVERABLE_REJECTION_CODES,
    RECOVERABLE_LEGITIMACY_CLASSES,
)
from src.engineering_recovery.recovery_collector import CONFIDENCE_THRESHOLD

VALID_RECOVERY_ROLES = frozenset(
    {
        "TOP_MAIN",
        "BOTTOM_MAIN",
        "EXTRA_TOP",
        "EXTRA_BOTTOM",
        "SIDE_BAR",
        "STIRRUP",
        "LINK_BAR",
        "SPACER",
        "STARTER",
    }
)


class RecoveryDecisionEngine:
    """Apply conservative recovery decision tree."""

    def evaluate_all(self, candidates: List[dict[str, Any]]) -> List[dict[str, Any]]:
        return [self.evaluate(candidate) for candidate in candidates]

    def evaluate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        inventory = candidate.get("inventory") or {}
        discovery_id = str(candidate.get("discovery_id"))
        reasons: List[str] = []
        blocking_reasons: List[str] = []

        if candidate.get("primary_rejection_code") != "DUPLICATE_SUPPRESSED":
            blocking_reasons.append("Not duplicate suppressed")

        legitimacy_class = str(candidate.get("legitimacy_class") or "")
        if legitimacy_class not in RECOVERABLE_LEGITIMACY_CLASSES:
            blocking_reasons.append(f"Legitimacy class {legitimacy_class or 'UNKNOWN'} not recoverable")

        confidence = float(candidate.get("confidence_score") or 0.0)
        if confidence < CONFIDENCE_THRESHOLD:
            blocking_reasons.append(f"Confidence {confidence} below threshold {CONFIDENCE_THRESHOLD}")

        if not candidate.get("classified"):
            blocking_reasons.append("Classification failed")
        else:
            reasons.append("Classification passed")

        if not candidate.get("associated"):
            blocking_reasons.append("Association failed")
        else:
            reasons.append("Association passed")

        if not candidate.get("suppressed"):
            blocking_reasons.append("Callout not suppressed in duplicate group")

        rejection_code = str(candidate.get("primary_rejection_code") or "")
        if rejection_code in NON_RECOVERABLE_REJECTION_CODES:
            blocking_reasons.append(f"Rejection code {rejection_code} is non-recoverable")

        geometry_ready, geometry_reason = self._geometry_ready(inventory)
        if not geometry_ready:
            blocking_reasons.append(geometry_reason)
        else:
            reasons.append("Geometry available")

        specification_ready, specification_reason = self._specification_ready(inventory)
        if not specification_ready:
            blocking_reasons.append(specification_reason)
        else:
            reasons.append("Specification available")

        rule_consistent, rule_reason = self._engineering_rule_consistent(inventory)
        if not rule_consistent:
            blocking_reasons.append(rule_reason)
        else:
            reasons.append("Engineering rule consistent")

        if inventory.get("normalized_bar_id"):
            blocking_reasons.append("Already normalized")

        if inventory.get("engineering_object_id"):
            blocking_reasons.append("Engineering object already exists")

        recover = not blocking_reasons
        return {
            "discovery_id": discovery_id,
            "recover": recover,
            "recovery_status": "APPROVED" if recover else "REJECTED",
            "confidence_score": confidence,
            "legitimacy_class": legitimacy_class,
            "primary_rejection_code": rejection_code,
            "approval_reasons": reasons,
            "blocking_reasons": blocking_reasons,
            "recovery_reason": self._recovery_reason(legitimacy_class, reasons),
            "beam_id": candidate.get("beam_id"),
            "signature": candidate.get("signature"),
            "group_id": candidate.get("group_id"),
            "inventory": inventory,
            "legitimacy": candidate.get("legitimacy") or {},
            "decision": candidate.get("decision") or {},
            "audit": candidate.get("audit") or {},
        }

    @staticmethod
    def _geometry_ready(inventory: dict[str, Any]) -> Tuple[bool, str]:
        if not inventory.get("geometry_id"):
            return False, "Missing geometry ID"
        coordinates = inventory.get("coordinates") or {}
        if coordinates.get("x") is None or coordinates.get("y") is None:
            return False, "Missing geometry coordinates"
        return True, "Geometry available"

    @staticmethod
    def _specification_ready(inventory: dict[str, Any]) -> Tuple[bool, str]:
        if not inventory.get("beam_association"):
            return False, "Missing beam association"
        if inventory.get("diameter_mm") is None:
            return False, "Missing diameter"
        if inventory.get("quantity") is None:
            return False, "Missing quantity"
        if not inventory.get("role"):
            return False, "Missing role"
        return True, "Specification available"

    @staticmethod
    def _engineering_rule_consistent(inventory: dict[str, Any]) -> Tuple[bool, str]:
        if inventory.get("ambiguous"):
            return False, "Ambiguous callout"
        if inventory.get("unknown"):
            return False, "Unknown notation"
        role = str(inventory.get("role") or "")
        if role not in VALID_RECOVERY_ROLES:
            return False, f"Unsupported role {role}"
        return True, "Engineering rule consistent"

    @staticmethod
    def _recovery_reason(legitimacy_class: str, reasons: List[str]) -> str:
        if legitimacy_class == "LIKELY_ENGINEERING_BAR":
            return "Independent reinforcement region"
        if legitimacy_class == "INCORRECT_SUPPRESSION":
            return "Incorrect duplicate suppression"
        return "; ".join(reasons) or "Deterministic recovery"
