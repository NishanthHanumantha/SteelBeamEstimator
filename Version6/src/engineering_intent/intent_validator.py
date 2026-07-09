"""Validate intent reconstruction eligibility."""

from __future__ import annotations

from typing import Any, Dict, List


class IntentValidator:
    """Deterministic eligibility validation for intent reconstruction."""

    def validate_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        context = candidate.get("context") or {}
        checks = [
            self._check("Engineering Object Exists", bool(context.get("engineering_object_id"))),
            self._check("Specification Exists", bool(context.get("specification_id"))),
            self._check("Beam Exists", bool(context.get("beam_id"))),
            self._check("Geometry Exists", bool(context.get("geometry_reference"))),
            self._check("Calculation Context Complete", context.get("calculation_status") == "COMPLETE"),
            self._check("Engineering Rule Exists", bool(candidate.get("engineering_rule"))),
            self._check("General Note Reference", bool(candidate.get("general_note_id"))),
            self._check("Source Reinforcement Exists", bool(candidate.get("source_bar_id"))),
        ]
        if candidate.get("intent_type") in {
            "SUPPLEMENTARY_DEVELOPMENT_LENGTH",
            "SUPPLEMENTARY_ANCHORAGE",
            "SUPPLEMENTARY_TERMINATION",
        }:
            checks.append(self._check("Development Length Available", bool(context.get("development_length_mm"))))
        if candidate.get("intent_type") in {"SUPPLEMENTARY_ANCHORAGE", "SUPPLEMENTARY_HOOK", "SUPPLEMENTARY_TERMINATION"}:
            checks.append(self._check("Support Exists", bool(context.get("support_refs"))))
        if candidate.get("intent_type") == "SUPPLEMENTARY_CONTINUATION":
            checks.append(self._check("Continuity Relationship", bool(context.get("continuity_beams"))))
        failed = [item for item in checks if item["status"] == "FAIL"]
        eligible = not failed and candidate.get("reconstruct") is True
        return {
            "intent_key": candidate.get("intent_key"),
            "eligible": eligible,
            "decision": "APPROVE" if eligible else "REJECT",
            "checks": checks,
            "status": "PASS" if not failed else "FAIL",
        }

    def validate_all(self, candidates: List[dict[str, Any]]) -> List[dict[str, Any]]:
        return [self.validate_candidate(candidate) for candidate in candidates]

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
