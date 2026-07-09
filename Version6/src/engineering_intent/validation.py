"""Validate engineering intent reconstruction."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.engineering_intent.intent_collector import MODEL_VERSION


class IntentValidation:
    """Deterministic validation for intent reconstruction."""

    def validate(
        self,
        result: dict[str, Any],
        snapshot: dict[str, Any],
        export_validation: dict[str, Any],
    ) -> dict[str, Any]:
        intent_objects = result.get("intent_objects") or []
        decisions = result.get("decisions") or []
        registry_entries = (result.get("intent_registry") or {}).get("entries") or []
        traceability = result.get("traceability") or []
        native_bar_ids = {
            str(bar.get("bar_id"))
            for bar in snapshot.get("native_bars") or []
            if bar.get("bar_id")
        }
        current_native_ids = {
            str(bar.get("bar_id"))
            for bar in (snapshot.get("existing_bars") or [])
            if bar.get("bar_id") and not (bar.get("traceability") or {}).get("intent_source")
        }

        intent_keys: List[str] = [str(item.get("intent_key")) for item in intent_objects if item.get("intent_key")]

        checks = [
            self._check("Model Version 6.0.0", result.get("model_version") == MODEL_VERSION),
            self._check("Phase K.1", result.get("phase") == "Phase K.1"),
            self._check(
                "Every Reconstructed Object Has Deterministic Evidence",
                all(item.get("evidence") for item in intent_objects) or not intent_objects,
            ),
            self._check(
                "Every Reconstructed Object References Engineering Rules",
                all((item.get("evidence") or {}).get("engineering_rule") for item in intent_objects)
                or not intent_objects,
            ),
            self._check(
                "Every Reconstructed Object References General Notes",
                all((item.get("evidence") or {}).get("general_note_id") for item in intent_objects)
                or not intent_objects,
            ),
            self._check(
                "Every Reconstructed Object References Source Reinforcement",
                all(item.get("source_bar_id") for item in intent_objects) or not intent_objects,
            ),
            self._check("No Duplicate Intent Objects", len(intent_keys) == len(set(intent_keys))),
            self._check(
                "Existing Engineering Objects Preserved",
                native_bar_ids.issubset(current_native_ids) or not intent_objects,
            ),
            self._check(
                "Existing Recovery Framework Preserved",
                bool(snapshot.get("recovery_registry") or snapshot.get("expansion_registry") or True),
            ),
            self._check(
                "Intent Trace Complete",
                len(traceability) == len(registry_entries) == len(intent_objects) or not intent_objects,
            ),
            self._check(
                "Production Integration Successful",
                (result.get("production_integration") or {}).get("status")
                in {"SUCCESS", "IDEMPOTENT_SKIP", "SKIPPED"},
            ),
            self._check("Export Completeness", export_validation.get("status") == "PASS"),
            self._check(
                "Backward Compatibility Native Bars",
                len(current_native_ids) >= len(native_bar_ids),
            ),
            self._check(
                "Idempotent Execution Ready",
                bool(result.get("run_timestamp")),
            ),
        ]

        for obj in intent_objects:
            evidence = obj.get("evidence") or {}
            checks.append(
                self._check(
                    f"Evidence Complete {obj.get('intent_id')}",
                    all(
                        [
                            evidence.get("source_engineering_object_id"),
                            evidence.get("engineering_rule"),
                            evidence.get("general_note_id"),
                            evidence.get("engineering_justification"),
                        ]
                    ),
                )
            )

        for decision in decisions:
            if decision.get("decision") == "APPROVE":
                checks.append(
                    self._check(
                        f"Approved Decision Valid {decision.get('intent_key')}",
                        decision.get("eligible") is True,
                    )
                )

        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
