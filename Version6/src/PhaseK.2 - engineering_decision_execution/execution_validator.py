"""Validate individual execution registry entries."""

from __future__ import annotations

from typing import Any, Dict, List

from execution_registry import LIFECYCLE_STATES


class ExecutionValidator:
    """Validate execution registry structural integrity."""

    def validate_all(self, entries: List[dict[str, Any]]) -> List[dict[str, Any]]:
        return [self.validate_one(entry) for entry in entries]

    def validate_one(self, entry: dict[str, Any]) -> dict[str, Any]:
        checks = [
            self._check("execution_id", bool(entry.get("execution_id"))),
            self._check("decision_id", bool(entry.get("decision_id"))),
            self._check("execution_source", entry.get("execution_source") == "ENGINEERING_DECISION"),
            self._check("calculation_target", bool(entry.get("calculation_target"))),
            self._check("steel_target", bool(entry.get("steel_target"))),
            self._check("bbs_target", bool(entry.get("bbs_target"))),
            self._check("excel_target", bool(entry.get("excel_target"))),
            self._check("lifecycle_valid", entry.get("lifecycle") in LIFECYCLE_STATES),
            self._check("traceability", bool(entry.get("traceability"))),
        ]
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "execution_id": entry.get("execution_id"),
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
        }

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, str]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
