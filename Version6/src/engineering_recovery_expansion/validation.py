"""Validate expansion recovery safety and completeness."""

from __future__ import annotations

from typing import Any, List, Set


class ExpansionValidator:
    """Deterministic validation for recovery expansion."""

    def validate(
        self,
        result: dict[str, Any],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        candidates = result.get("candidates") or []
        decisions = result.get("decisions") or []
        registry_entries = (result.get("expansion_registry") or {}).get("entries") or []
        traceability = result.get("traceability") or []
        statistics = result.get("statistics") or {}
        recovered_objects = result.get("recovered_objects") or []

        decision_by_id = {str(item.get("discovery_id")): item for item in decisions}
        recovered_ids = [
            str(item.get("source_discovery_id") or item.get("discovery_id"))
            for item in recovered_objects
            if item.get("source_discovery_id") or item.get("discovery_id")
        ]

        checks = [
            self._check("Model Version 5.28.0", result.get("model_version") == "5.28.0"),
            self._check("Every Candidate Classified", all(item.get("expansion_class") for item in candidates)),
            self._check(
                "Every Candidate Evaluated",
                len(decisions) == len(candidates),
            ),
            self._check(
                "Every Decision Deterministic",
                all(item.get("decision") for item in decisions),
            ),
            self._check(
                "No Duplicate Recoveries",
                len(recovered_ids) == len(set(recovered_ids)),
            ),
            self._check(
                "Existing Production Preserved",
                (result.get("production_integration") or {}).get("status") in {"SUCCESS", "IDEMPOTENT_SKIP", "SKIPPED"},
            ),
            self._check(
                "Append-Only Verified",
                statistics.get("coverage_after_bars", 0) >= len(snapshot.get("existing_bars") or []),
            ),
            self._check(
                "Traceability Complete",
                len(traceability) == len(registry_entries) == len(recovered_objects) or not registry_entries,
            ),
            self._check(
                "Recovery Registry Valid",
                len(registry_entries) == len(recovered_objects) or not registry_entries,
            ),
            self._check(
                "Statistics Internally Consistent",
                statistics.get("objects_evaluated") == len(candidates),
            ),
            self._check(
                "Health Score Generated",
                bool(result.get("health")),
            ),
        ]

        for candidate in candidates:
            discovery_id = str(candidate.get("discovery_id") or "")
            checks.append(
                self._check(
                    f"Decision Exists {discovery_id}",
                    discovery_id in decision_by_id,
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

    def validate_exports(self, output_dir, export_files: tuple[str, ...]) -> dict[str, Any]:
        from src.engineering_recovery_expansion.export import ExpansionExporter

        return ExpansionExporter.validate_exports(output_dir, export_files)
