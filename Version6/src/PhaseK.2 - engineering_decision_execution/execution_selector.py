"""Select executable Engineering Decisions."""

from __future__ import annotations

from typing import Any, Dict, List


class ExecutionSelector:
    """Deterministic executability gate for Engineering Decisions."""

    REQUIRED_CHECKS = (
        "decision_valid",
        "primary_intent_exists",
        "calculation_context_complete",
        "geometry_complete",
        "specification_complete",
        "dependencies_complete",
        "lifecycle_ready",
    )

    def select(self, execution_contexts: List[dict[str, Any]]) -> List[dict[str, Any]]:
        results = []
        for context in execution_contexts:
            results.append(self.evaluate(context))
        return sorted(results, key=lambda item: str(item.get("decision_id") or ""))

    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        checks = dict(context.get("checks") or {})
        eligibility = str(context.get("execution_eligibility") or "")
        failed = [name for name in self.REQUIRED_CHECKS if not checks.get(name)]
        executable = not failed and eligibility == "ELIGIBLE"
        status = "EXECUTABLE" if executable else "NOT_EXECUTABLE"
        reason = "All execution gates passed." if executable else (
            "Failed checks: " + ", ".join(failed) if failed else f"production_eligibility={eligibility}"
        )
        return {
            "decision_id": context.get("decision_id"),
            "decision_key": context.get("decision_key"),
            "executable": executable,
            "execution_status": status,
            "failed_checks": failed,
            "reason": reason,
            "production_eligibility": eligibility,
        }
