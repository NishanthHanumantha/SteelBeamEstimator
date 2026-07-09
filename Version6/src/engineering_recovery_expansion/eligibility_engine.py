"""Determine recovery eligibility for expansion candidates."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from src.engineering_recovery.recovery_decision_engine import VALID_RECOVERY_ROLES
from src.engineering_recovery_expansion.candidate_classifier import ExpansionClass
from src.engineering_recovery_expansion.candidate_loader import SIMILARITY_THRESHOLD


class ExpansionDecision:
    RECOVER = "RECOVER"
    REJECT = "REJECT"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    PARTIAL = "PARTIAL"


class EligibilityEngine:
    """Apply deterministic expansion recovery policy."""

    def evaluate(
        self,
        gap: dict[str, Any],
        expansion_class: str,
        similarity: dict[str, Any],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        inventory = gap.get("inventory") or {}
        discovery_id = str(gap.get("discovery_id") or "")
        reasons: List[str] = []
        blocking: List[str] = []

        if expansion_class == ExpansionClass.ALREADY_RECOVERED:
            return self._decision(
                discovery_id,
                ExpansionDecision.ALREADY_EXISTS,
                expansion_class,
                similarity,
                inventory,
                gap,
                ["Already recovered or in production"],
                [],
                False,
            )

        if expansion_class == ExpansionClass.UNRECOVERABLE:
            return self._decision(
                discovery_id,
                ExpansionDecision.REJECT,
                expansion_class,
                similarity,
                inventory,
                gap,
                [],
                ["Unrecoverable expansion class"],
                False,
            )

        if expansion_class in {
            ExpansionClass.MISSING_ASSOCIATION,
            ExpansionClass.MISSING_CONTEXT,
            ExpansionClass.MISSING_SPECIFICATION,
            ExpansionClass.MISSING_GROUP,
        }:
            return self._decision(
                discovery_id,
                ExpansionDecision.INSUFFICIENT_CONTEXT,
                expansion_class,
                similarity,
                inventory,
                gap,
                [],
                [f"Expansion class {expansion_class}"],
                False,
            )

        if expansion_class == ExpansionClass.PARTIAL_OBJECT:
            return self._decision(
                discovery_id,
                ExpansionDecision.PARTIAL,
                expansion_class,
                similarity,
                inventory,
                gap,
                [],
                ["Partial engineering object"],
                False,
            )

        similarity_score = float(similarity.get("similarity_score") or 0.0)
        if similarity_score < SIMILARITY_THRESHOLD:
            blocking.append(
                f"Engineering similarity {similarity_score} below threshold {SIMILARITY_THRESHOLD}"
            )
        else:
            reasons.append(f"Engineering similarity {similarity_score} meets threshold")

        if not inventory.get("classified"):
            blocking.append("Classification failed")
        else:
            reasons.append("Classification passed")

        if not inventory.get("associated"):
            blocking.append("Association failed")
        else:
            reasons.append("Association passed")

        geometry_ready, geometry_reason = self._geometry_ready(inventory)
        if not geometry_ready:
            blocking.append(geometry_reason)
        else:
            reasons.append("Geometry available")

        specification_ready, specification_reason = self._specification_ready(inventory)
        if not specification_ready:
            blocking.append(specification_reason)
        else:
            reasons.append("Specification available")

        beam_id = str(inventory.get("beam_association") or "")
        if beam_id not in (snapshot.get("contexts_by_beam") or {}):
            blocking.append("Required calculation context unavailable")
        else:
            reasons.append("Calculation context available")

        if self._duplicate_signature(inventory, snapshot.get("existing_bars") or []):
            blocking.append("Duplicate production signature")
        else:
            reasons.append("Unique engineering identity")

        if not self._engineering_consistent(inventory):
            blocking.append("Engineering consistency failed")
        else:
            reasons.append("Engineering consistency verified")

        recover = not blocking and expansion_class == ExpansionClass.MISSING_NORMALIZATION
        decision = ExpansionDecision.RECOVER if recover else ExpansionDecision.REJECT
        if recover:
            reasons.append("Normalization gap eligible for expansion recovery")

        return self._decision(
            discovery_id,
            decision,
            expansion_class,
            similarity,
            inventory,
            gap,
            reasons,
            blocking,
            recover,
        )

    @staticmethod
    def _decision(
        discovery_id: str,
        decision: str,
        expansion_class: str,
        similarity: dict[str, Any],
        inventory: dict[str, Any],
        gap: dict[str, Any],
        reasons: List[str],
        blocking: List[str],
        recover: bool,
    ) -> dict[str, Any]:
        return {
            "discovery_id": discovery_id,
            "decision": decision,
            "recover": recover,
            "expansion_class": expansion_class,
            "similarity_score": similarity.get("similarity_score"),
            "similarity_components": similarity.get("components") or {},
            "eligibility": "ELIGIBLE" if recover else "NOT_ELIGIBLE",
            "approval_reasons": reasons,
            "blocking_reasons": blocking,
            "recovery_reason": EligibilityEngine._recovery_reason(expansion_class, reasons),
            "beam_id": inventory.get("beam_association") or gap.get("beam_id"),
            "primary_rejection_code": gap.get("primary_rejection_code"),
            "inventory": inventory,
            "decision_record": gap.get("decision") or {},
            "confidence": similarity.get("similarity_score"),
        }

    @staticmethod
    def _recovery_reason(expansion_class: str, reasons: List[str]) -> str:
        if expansion_class == ExpansionClass.MISSING_NORMALIZATION:
            return "Discovery geometry available; normalization gap recovery"
        return "; ".join(reasons) or "Deterministic expansion recovery"

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
    def _engineering_consistent(inventory: dict[str, Any]) -> bool:
        role = str(inventory.get("role") or "")
        return role in VALID_RECOVERY_ROLES and not inventory.get("ambiguous") and not inventory.get("unknown")

    @staticmethod
    def _duplicate_signature(inventory: dict[str, Any], existing_bars: List[dict[str, Any]]) -> bool:
        signature = EligibilityEngine._signature(inventory)
        existing_signatures: Set[str] = {
            EligibilityEngine._signature_from_bar(bar) for bar in existing_bars if bar.get("bar_id")
        }
        return signature in existing_signatures

    @staticmethod
    def _signature(inventory: dict[str, Any]) -> str:
        beam = str(inventory.get("beam_association") or "")
        role = str(inventory.get("role") or "")
        diameter = inventory.get("diameter_mm")
        quantity = inventory.get("quantity")
        coordinates = inventory.get("coordinates") or {}
        return "|".join(
            [
                beam,
                role,
                str(diameter),
                str(quantity),
                str(coordinates.get("x")),
                str(coordinates.get("y")),
            ]
        )

    @staticmethod
    def _signature_from_bar(bar: dict[str, Any]) -> str:
        trace = bar.get("traceability") or {}
        coordinates = trace.get("coordinates") or {}
        return "|".join(
            [
                str(bar.get("beam_id") or ""),
                str(bar.get("role") or ""),
                str(bar.get("diameter_mm")),
                str(bar.get("quantity")),
                str(coordinates.get("x")),
                str(coordinates.get("y")),
            ]
        )
