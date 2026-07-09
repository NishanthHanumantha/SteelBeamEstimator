"""Cross-artifact validation for recovery statistics."""

from __future__ import annotations

from typing import Any, Dict, List


class ArtifactCrossChecker:
    """Validate consistency across exported JSON artifacts."""

    def check(self, snapshot: dict[str, Any], authoritative: dict[str, Any]) -> dict[str, Any]:
        pairs = [
            ("recovery_statistics", "recovery_summary", self._recovery_pairs(snapshot)),
            ("expansion_statistics", "expansion_summary", self._expansion_pairs(snapshot)),
        ]
        checks: List[dict[str, Any]] = []
        for left_name, right_name, fields in pairs:
            left = snapshot.get(left_name) or {}
            right = snapshot.get(right_name) or {}
            for field in fields:
                checks.append(
                    {
                        "artifact_left": left_name,
                        "artifact_right": right_name,
                        "field": field,
                        "left_value": left.get(field),
                        "right_value": right.get(field),
                        "status": "PASS" if left.get(field) == right.get(field) else "FAIL",
                    }
                )

        registry_checks = [
            self._registry_check("J.1", snapshot.get("j1_registry_entries"), authoritative["j1_recovered_bars"]),
            self._registry_check("J.2", snapshot.get("j2_registry_entries"), authoritative["j2_recovered_bars"]),
        ]
        return {
            "pair_checks": checks,
            "registry_checks": registry_checks,
            "status": "PASS"
            if all(item["status"] == "PASS" for item in checks + registry_checks)
            else "FAIL",
        }

    @staticmethod
    def _recovery_pairs(snapshot: dict[str, Any]) -> List[str]:
        return ["recovered_objects", "recovered_normalized_bars"]

    @staticmethod
    def _expansion_pairs(snapshot: dict[str, Any]) -> List[str]:
        return [
            "recovered",
            "coverage_before_percent",
            "coverage_after_percent",
            "coverage_before_bars",
            "coverage_after_bars",
            "inventory_count",
            "objects_evaluated",
        ]

    @staticmethod
    def _registry_check(phase: str, entries: List[dict[str, Any]], production_count: int) -> dict[str, Any]:
        success = sum(1 for entry in entries if entry.get("recovery_status") == "SUCCESS")
        return {
            "phase": phase,
            "registry_success_count": success,
            "production_bar_count": production_count,
            "status": "PASS" if success == production_count else "FAIL",
        }
