"""Validate individual engineering decisions before registry export."""

from __future__ import annotations

from typing import Any, Dict, List


class DecisionValidator:
    """Validate EngineeringDecision structural integrity."""

    def validate_all(self, decisions: List[dict[str, Any]]) -> List[dict[str, Any]]:
        return [self.validate_one(decision) for decision in decisions]

    def validate_one(self, decision: dict[str, Any]) -> dict[str, Any]:
        checks = [
            self._check("decision_id", bool(decision.get("decision_id"))),
            self._check("decision_key", bool(decision.get("decision_key"))),
            self._check("beam_id", bool(decision.get("beam_id"))),
            self._check("primary_intent", bool((decision.get("primary_intent") or {}).get("intent_id"))),
            self._check("resolution_rule", bool(decision.get("resolution_rule"))),
            self._check("engineering_justification", bool(decision.get("engineering_justification"))),
            self._check("evidence", bool(decision.get("evidence"))),
            self._check(
                "decision_confidence",
                isinstance(decision.get("decision_confidence"), (int, float))
                and 0.0 <= float(decision.get("decision_confidence")) <= 100.0,
            ),
            self._check("lifecycle", decision.get("lifecycle") == "RESOLVED"),
            self._check(
                "production_eligibility",
                decision.get("production_eligibility") in {"ELIGIBLE", "HOLD"},
            ),
            self._check(
                "suppressed_retained",
                all(item.get("retained") for item in (decision.get("suppressed_intents") or []))
                or not decision.get("suppressed_intents"),
            ),
        ]
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "decision_id": decision.get("decision_id"),
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
        }

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, str]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
