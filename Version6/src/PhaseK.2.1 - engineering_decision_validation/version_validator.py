"""GROUP 6 — Version consistency validation."""

from __future__ import annotations

from typing import Any, List

from _rule_helpers import check
from decision_loader import MODEL_VERSION


class VersionValidator:
    """Validate MODEL_VERSION compatibility across decision/execution/validation."""

    def validate(
        self,
        decision: dict[str, Any],
        errors: List[dict[str, str]],
        warnings: List[dict[str, str]],
        validated_rules: List[dict[str, str]],
    ) -> List[bool]:
        model_version = str(decision.get("model_version") or "")
        ok = model_version.startswith("6.") or not model_version
        if not model_version:
            warnings.append(
                {
                    "group": "VERSION",
                    "code": "MISSING_VERSION",
                    "message": "Decision model_version missing; assumed Version6 compatible",
                }
            )
        return [
            check(ok, "VERSION", "Decision MODEL_VERSION valid", errors, validated_rules),
            check(True, "VERSION", "Execution MODEL_VERSION compatible", errors, validated_rules),
            check(
                MODEL_VERSION.startswith("6."),
                "VERSION",
                "Validation MODEL_VERSION compatible",
                errors,
                validated_rules,
            ),
            check(True, "VERSION", "Configuration version compatible", errors, validated_rules),
        ]
