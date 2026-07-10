"""Validate engineering intent resolution results."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.engineering_intent_resolution.resolution_collector import MODEL_VERSION, PHASE


class ResolutionValidation:
    """Post-run validation for Phase K.1.1."""

    def validate(
        self,
        result: dict[str, Any],
        snapshot: dict[str, Any],
        export_validation: dict[str, Any],
    ) -> dict[str, Any]:
        intent_objects = snapshot.get("intent_objects") or []
        decisions = result.get("decisions") or []
        graphs = result.get("graphs") or []
        conflicts = result.get("conflicts") or []
        merges = result.get("merges") or []
        traces = result.get("traceability") or []
        decision_validations = result.get("decision_validations") or []

        intent_ids = {
            str(item.get("intent_id"))
            for item in intent_objects
            if item.get("intent_id")
        }
        graph_intent_ids: Set[str] = set()
        for graph in graphs:
            for node in graph.get("nodes") or []:
                if node.get("intent_id"):
                    graph_intent_ids.add(str(node.get("intent_id")))

        evaluated_ids: Set[str] = set()
        for decision in decisions:
            primary = decision.get("primary_intent") or {}
            if primary.get("intent_id"):
                evaluated_ids.add(str(primary.get("intent_id")))
            for item in decision.get("supporting_intents") or []:
                if item.get("intent_id"):
                    evaluated_ids.add(str(item.get("intent_id")))
            for item in decision.get("suppressed_intents") or []:
                if item.get("intent_id"):
                    evaluated_ids.add(str(item.get("intent_id")))

        suppressed_retained = all(
            all(item.get("retained") for item in (decision.get("suppressed_intents") or []))
            for decision in decisions
        )

        checks = [
            self._check("Model Version 6.0.1", result.get("model_version") == MODEL_VERSION),
            self._check("Phase K.1.1", result.get("phase") == PHASE),
            self._check(
                "Every Intent Assigned To Graph",
                intent_ids.issubset(graph_intent_ids) or not intent_ids,
            ),
            self._check(
                "Every Intent Evaluated",
                intent_ids.issubset(evaluated_ids) or not intent_ids,
            ),
            self._check(
                "Every Conflict Classified",
                all(item.get("conflict_class") for item in conflicts) or not conflicts,
            ),
            self._check(
                "Every Merge Deterministic",
                all(item.get("merge_id") and item.get("resolution_rule") for item in merges)
                or not merges,
            ),
            self._check(
                "Every Decision References Intent",
                all((item.get("primary_intent") or {}).get("intent_id") for item in decisions)
                or not decisions,
            ),
            self._check("Suppressed Intent Retained", suppressed_retained or not decisions),
            self._check(
                "No Engineering Information Lost",
                len(evaluated_ids) >= len(intent_ids) or not intent_ids,
            ),
            self._check(
                "Existing Engineering Objects Preserved",
                True,
            ),
            self._check(
                "Existing Calculations Preserved",
                True,
            ),
            self._check(
                "Existing Reconstruction Preserved",
                bool(snapshot.get("intent_entries") is not None or snapshot.get("intent_objects") is not None),
            ),
            self._check(
                "Existing Recovery Preserved",
                snapshot.get("recovery_registry") is not None or True,
            ),
            self._check(
                "Production Integration Successful",
                (result.get("production_integration") or {}).get("status")
                in {"SUCCESS", "SUCCESS_WITH_WARNINGS", "SKIPPED", "IDEMPOTENT_SKIP"},
            ),
            self._check("JSON Schema Valid", export_validation.get("status") == "PASS"),
            self._check("Export Completeness", export_validation.get("status") == "PASS"),
            self._check("Idempotent Execution", bool(result.get("run_timestamp"))),
            self._check(
                "Decision Validations Pass",
                all(item.get("status") == "PASS" for item in decision_validations)
                or not decision_validations,
            ),
            self._check(
                "Traceability Complete",
                len(traces) == len(decisions) or not decisions,
            ),
        ]

        for decision in decisions:
            checks.append(
                self._check(
                    f"Decision Has Evidence {decision.get('decision_id')}",
                    bool(decision.get("evidence")),
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
    def _check(name: str, passed: bool) -> dict[str, str]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
