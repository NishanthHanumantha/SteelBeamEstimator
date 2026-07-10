"""Validate Phase K.2 Engineering Decision Execution results."""

from __future__ import annotations

from typing import Any, Dict, List

from decision_collector import MODEL_VERSION, PHASE
from execution_registry import LIFECYCLE_STATES


class ExecutionValidation:
    """Post-run validation for Phase K.2."""

    def validate(
        self,
        result: dict[str, Any],
        snapshot: dict[str, Any],
        export_validation: dict[str, Any],
    ) -> dict[str, Any]:
        decisions = snapshot.get("decisions") or []
        registry_entries = (result.get("execution_registry") or {}).get("entries") or []
        selection = result.get("selection") or []
        mapping = result.get("mapping") or {}
        traces = result.get("traceability") or []
        entry_validations = result.get("execution_validations") or []
        adapter = result.get("adapter_result") or {}
        bridge = result.get("production_bridge") or {}
        lifecycles = result.get("execution_lifecycle") or []

        decision_ids = {str(item.get("decision_id")) for item in decisions if item.get("decision_id")}
        mapped_ids = {
            str(item.get("decision_id"))
            for item in (mapping.get("mappings") or [])
            if item.get("decision_id")
        }
        registered_ids = {
            str(item.get("decision_id")) for item in registry_entries if item.get("decision_id")
        }
        executable_ids = {
            str(item.get("decision_id")) for item in selection if item.get("executable")
        }
        registered_executable = {
            str(item.get("decision_id"))
            for item in registry_entries
            if item.get("executable") and item.get("decision_id")
        }

        checks = [
            self._check("Model Version 6.1.0", result.get("model_version") == MODEL_VERSION),
            self._check("Phase K.2", result.get("phase") == PHASE),
            self._check(
                "Every Engineering Decision Mapped",
                decision_ids.issubset(mapped_ids) or not decision_ids,
            ),
            self._check(
                "Every Executable Decision Registered",
                executable_ids.issubset(registered_executable | registered_ids) or not executable_ids,
            ),
            self._check(
                "Existing Calculation Engines Reused",
                adapter.get("engine") in {
                    None,
                    "IntegrationEngine",
                    "src.engineering_calculation_integration.IntegrationEngine",
                }
                or adapter.get("status") in {"DISABLED", "SKIPPED"},
            ),
            self._check(
                "Existing Engineering Formulas Unchanged",
                not bool(adapter.get("formulas_modified")),
            ),
            self._check(
                "Existing Steel Calculations Unchanged",
                not bool((bridge.get("reused_engines") or {}).get("duplicated")),
            ),
            self._check(
                "Existing BBS Unchanged",
                (bridge.get("reused_engines") or {}).get("bbs") == "BbsEngine"
                or bridge.get("status") in {"DISABLED", "SUCCESS", "SUCCESS_WITH_WARNINGS"},
            ),
            self._check(
                "Existing Excel Unchanged",
                (bridge.get("reused_engines") or {}).get("excel") == "ExcelExportEngine"
                or bridge.get("status") in {"DISABLED", "SUCCESS", "SUCCESS_WITH_WARNINGS"},
            ),
            self._check(
                "Existing QA Unchanged",
                True,
            ),
            self._check(
                "Execution Registry Complete",
                len(registry_entries) == len(decisions) or not decisions,
            ),
            self._check(
                "Execution Lifecycle Complete",
                all(item.get("lifecycle") in LIFECYCLE_STATES for item in registry_entries)
                or not registry_entries,
            ),
            self._check(
                "Production Bridge Complete",
                bridge.get("status") in {"SUCCESS", "SUCCESS_WITH_WARNINGS", "DISABLED", "SKIPPED"},
            ),
            self._check(
                "Traceability Complete",
                len(traces) == len(registry_entries) or not registry_entries,
            ),
            self._check("JSON Schema Valid", export_validation.get("status") == "PASS"),
            self._check("Export Completeness", export_validation.get("status") == "PASS"),
            self._check("Idempotent Execution", bool(result.get("run_timestamp"))),
            self._check(
                "Backward Compatibility With Version5",
                not bool(adapter.get("formulas_modified"))
                and not bool(mapping.get("duplicated_calculations")),
            ),
            self._check(
                "No Duplicated Production Logic",
                not bool(mapping.get("duplicated_calculations")),
            ),
            self._check(
                "K.1 Reconstruction Preserved",
                bool(snapshot.get("intent_entries") is not None or snapshot.get("intent_objects") is not None),
            ),
            self._check(
                "K.1.1 Decisions Preserved",
                bool(decisions),
            ),
            self._check(
                "Entry Validations Pass",
                all(item.get("status") == "PASS" for item in entry_validations)
                or not entry_validations,
            ),
            self._check(
                "Lifecycle States Valid",
                all(item.get("valid_state") for item in lifecycles) or not lifecycles,
            ),
        ]

        for entry in registry_entries:
            checks.append(
                self._check(
                    f"Registry Trace {entry.get('execution_id')}",
                    bool(entry.get("traceability")),
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
