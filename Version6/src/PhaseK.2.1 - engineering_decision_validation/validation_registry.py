"""Build validated decision registry entries."""

from __future__ import annotations

from typing import Any, List

from decision_loader import MODEL_VERSION, PHASE
from decision_validation_types import ValidationStatus


class ValidationRegistry:
    """Assemble validated decision registry payload."""

    @staticmethod
    def build(validations: List[dict[str, Any]]) -> dict[str, Any]:
        entries = []
        for item in validations:
            entries.append(
                {
                    "validation_id": item.get("validation_id"),
                    "decision_id": item.get("decision_id"),
                    "decision_key": item.get("decision_key"),
                    "validation_status": item.get("validation_status"),
                    "validation_score": item.get("validation_score"),
                    "execution_allowed": bool(item.get("execution_allowed")),
                    "validation_errors": item.get("validation_errors") or [],
                    "validation_warnings": item.get("validation_warnings") or [],
                    "validated_rules": item.get("validated_rules") or [],
                    "traceability": item.get("traceability") or {},
                    "validation_timestamp": item.get("validation_timestamp"),
                    "validation_version": item.get("validation_version") or MODEL_VERSION,
                    "lifecycle": item.get("lifecycle"),
                    "decision_category": item.get("decision_category"),
                    "production_eligibility": item.get("production_eligibility"),
                    "resolution_rule": item.get("resolution_rule"),
                    "score_breakdown": item.get("score_breakdown") or {},
                }
            )
        entries = sorted(entries, key=lambda item: str(item.get("decision_id") or ""))
        allowed_ids = [
            str(item.get("decision_id"))
            for item in entries
            if item.get("validation_status") == ValidationStatus.VALID.value
            and item.get("execution_allowed")
        ]
        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "registry_count": len(entries),
            "validated_count": sum(
                1 for item in entries if item.get("validation_status") == ValidationStatus.VALID.value
            ),
            "invalid_count": sum(
                1
                for item in entries
                if item.get("validation_status") == ValidationStatus.INVALID.value
            ),
            "warning_count": sum(
                1
                for item in entries
                if item.get("validation_status") == ValidationStatus.WARNING.value
            ),
            "execution_allowed_ids": allowed_ids,
            "entries": entries,
        }
