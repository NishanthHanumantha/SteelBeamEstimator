"""Build recovery candidates from QA evidence."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_recovery.recovery_collector import CONFIDENCE_THRESHOLD


RECOVERABLE_LEGITIMACY_CLASSES = frozenset({"LIKELY_ENGINEERING_BAR", "INCORRECT_SUPPRESSION"})

NON_RECOVERABLE_REJECTION_CODES = frozenset(
    {
        "UNSUPPORTED_NOTATION",
        "AMBIGUOUS_CALLOUT",
        "MISSING_GEOMETRY",
        "MISSING_SPECIFICATION",
        "BEAM_NOT_ASSOCIATED",
        "NOT_REINFORCEMENT",
    }
)


class RecoveryCandidateBuilder:
    """Identify discovery IDs eligible for deterministic recovery."""

    def build(self, snapshot: dict[str, Any]) -> List[dict[str, Any]]:
        inventory_by_id = snapshot.get("inventory_by_id") or {}
        decision_by_id = snapshot.get("decision_by_id") or {}
        audit_by_id = snapshot.get("audit_by_id") or {}
        legitimacy_by_discovery = snapshot.get("legitimacy_by_discovery") or {}

        candidates: List[dict[str, Any]] = []
        for discovery_id, legitimacy in sorted(legitimacy_by_discovery.items()):
            if not legitimacy.get("suppressed"):
                continue
            item = inventory_by_id.get(str(discovery_id))
            if not item:
                continue
            decision = decision_by_id.get(str(discovery_id), {})
            audit = audit_by_id.get(str(discovery_id), {})
            candidates.append(
                {
                    "discovery_id": str(discovery_id),
                    "inventory": item,
                    "decision": decision,
                    "audit": audit,
                    "legitimacy": legitimacy,
                    "primary_rejection_code": decision.get("primary_rejection_code"),
                    "legitimacy_class": legitimacy.get("legitimacy_class"),
                    "confidence_score": legitimacy.get("confidence_score"),
                    "group_id": legitimacy.get("group_id"),
                    "signature": legitimacy.get("signature"),
                    "beam_id": item.get("beam_association") or legitimacy.get("beam_id"),
                    "classified": bool(item.get("classified")),
                    "associated": bool(item.get("associated")),
                    "suppressed": True,
                }
            )
        return candidates
