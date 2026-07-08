"""Validate recovery safety and completeness."""

from __future__ import annotations

from typing import Any, Dict, List, Set


class RecoveryValidator:
    """Validate recovery candidates and recovered objects."""

    def validate_candidates(
        self,
        candidates: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
    ) -> dict[str, Any]:
        decision_by_id = {str(item.get("discovery_id")): item for item in decisions}
        checks = [
            self._check(
                "Every Recovery Candidate Evaluated",
                len(decisions) == len(candidates),
            )
        ]
        for candidate in candidates:
            discovery_id = str(candidate.get("discovery_id"))
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

    def validate_recovery(
        self,
        decisions: List[dict[str, Any]],
        recovered_objects: List[dict[str, Any]],
        registry_entries: List[dict[str, Any]],
        traceability_records: List[dict[str, Any]],
        existing_bar_count: int,
        merged_bar_count: int,
    ) -> dict[str, Any]:
        approved = [item for item in decisions if item.get("recover")]
        recovered_ids = [
            str(item.get("source_discovery_id") or item.get("discovery_id"))
            for item in recovered_objects
            if item.get("source_discovery_id") or item.get("discovery_id")
        ]
        registry_ids = [str(item.get("discovery_id")) for item in registry_entries if item.get("discovery_id")]
        trace_ids = [
            str(item.get("discovery_id") or item.get("source_discovery_id"))
            for item in traceability_records
            if item.get("discovery_id") or item.get("source_discovery_id")
        ]

        checks = [
            self._check(
                "Every Recovered Object Has Deterministic Evidence",
                all(
                    item.get("recovery_justification") or item.get("recovery_source")
                    for item in recovered_objects
                ),
            ),
            self._check(
                "Confidence Threshold Enforced",
                all(float(item.get("confidence_score", 0.0)) >= 70.0 for item in approved),
            ),
            self._check(
                "Geometry Verified",
                all(item.get("coordinates") for item in recovered_objects),
            ),
            self._check(
                "Specification Verified",
                all(item.get("specification_id") for item in recovered_objects),
            ),
            self._check(
                "No Duplicate Recoveries",
                len(recovered_ids) == len(set(recovered_ids)),
            ),
            self._check(
                "One Recovery Per Discovery ID",
                len(recovered_ids) == len(registry_ids) == len(trace_ids),
            ),
            self._check(
                "Recovery Registry Complete",
                len(registry_entries) == len(recovered_objects),
            ),
            self._check(
                "Traceability Complete",
                len(traceability_records) == len(recovered_objects),
            ),
            self._check(
                "Existing Engineering Objects Preserved",
                merged_bar_count >= existing_bar_count,
            ),
            self._check(
                "Recovery Count Matches Approved Decisions",
                len(recovered_objects) == len(approved),
            ),
        ]
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

    def validate_exports(self, output_dir, export_files: tuple[str, ...]) -> dict[str, Any]:
        checks = [
            self._check(
                f"Export Written {filename}",
                (output_dir / filename).exists() and (output_dir / filename).stat().st_size > 0,
            )
            for filename in export_files
        ]
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
    def validate_no_conflicts(
        recovered_discovery_ids: Set[str],
        existing_discovery_ids: Set[str],
    ) -> List[str]:
        return sorted(recovered_discovery_ids.intersection(existing_discovery_ids))

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
