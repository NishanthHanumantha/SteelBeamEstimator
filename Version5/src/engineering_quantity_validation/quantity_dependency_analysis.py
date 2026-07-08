"""Dependency validation for recovered object quantity integration."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_quantity_validation.quantity_traceability import DEPENDENCY_FIELDS


class QuantityDependencyAnalyzer:
    """Inspect dependency readiness for each recovered object."""

    def analyze(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        recovery_index = snapshot.get("recovery_index") or {}
        recovered_bar_ids = recovery_index.get("recovered_bar_ids") or []
        records: List[dict[str, Any]] = []

        for bar_id in recovered_bar_ids:
            bar = snapshot.get("bar_by_id", {}).get(bar_id, {})
            registry_entry = (recovery_index.get("registry_by_bar") or {}).get(bar_id, {})
            context = snapshot.get("context_by_id", {}).get(str(bar.get("context_id") or ""), {})
            spec = snapshot.get("spec_by_id", {}).get(str(bar.get("specification_id") or ""), {})
            steel = snapshot.get("steel_weight_by_bar", {}).get(bar_id, {})
            cut_length = snapshot.get("cut_length_by_bar", {}).get(bar_id)
            development = snapshot.get("development_length_by_bar", {}).get(bar_id)
            bbs = snapshot.get("bbs_by_bar", {}).get(bar_id)
            calc_results = snapshot.get("calc_by_bar", {}).get(bar_id, [])
            beam_id = str(bar.get("beam_id") or registry_entry.get("beam_id") or "")

            dependencies = {
                "geometry": self._status(bool(context.get("geometry") or bar.get("coordinates") or spec.get("geometry"))),
                "specification": self._status(bool(bar.get("specification_id"))),
                "length": self._status(bar.get("length") is not None),
                "development_length": self._status(development is not None or self._calc_success(calc_results, "DEVELOPMENT_LENGTH")),
                "cut_length": self._status(cut_length is not None or steel.get("cut_length_mm") is not None),
                "diameter": self._status(bar.get("diameter_mm") not in (None, 0, 0.0)),
                "quantity": self._status(bar.get("quantity") is not None),
                "steel_density": self._status(steel.get("density") is not None),
                "lifecycle_state": self._status(bool(context.get("lifecycle_state") or context.get("engineering_state"))),
                "availability": self._status(bool(context.get("availability") or context.get("availability_state"))),
                "calculation_result": self._status(len(calc_results) > 0),
                "weight_result": self._status(steel.get("weight_kg") is not None),
                "engineering_report_entry": self._status(self._has_beam_report(snapshot, beam_id)),
                "bbs_entry": self._status(bbs is not None),
                "excel_entry": self._status(bar_id in str(snapshot.get("registries", {}).get("excel_export") or {})),
            }

            failed = [name for name, value in dependencies.items() if value == "FAIL"]
            unknown = [name for name, value in dependencies.items() if value == "UNKNOWN"]
            records.append(
                {
                    "recovery_id": registry_entry.get("recovery_id"),
                    "bar_id": bar_id,
                    "beam_id": beam_id,
                    "dependencies": dependencies,
                    "failed_dependencies": failed,
                    "unknown_dependencies": unknown,
                    "primary_dependency_failure": failed[0] if failed else None,
                }
            )

        return {
            "recovered_count": len(records),
            "records": records,
            "dependency_failure_ranking": self._rank_failures(records),
        }

    @staticmethod
    def _status(passed: bool) -> str:
        if passed:
            return "PASS"
        return "FAIL"

    @staticmethod
    def _calc_success(calc_results: List[dict[str, Any]], calc_type: str) -> bool:
        for item in calc_results:
            if str(item.get("calculation_type") or "") != calc_type:
                continue
            status = str(item.get("result_status") or "").upper()
            state = str(item.get("calculation_state") or "").upper()
            return status not in {"FAILED", "DEPENDENCY_BLOCKED", "BLOCKED"} and state != "FAILED"
        return False

    @staticmethod
    def _has_beam_report(snapshot: dict[str, Any], beam_id: str) -> bool:
        for item in snapshot.get("engineering_reports") or []:
            if str(item.get("beam_id") or item.get("beam_mark") or "") == beam_id:
                return True
        return False

    @staticmethod
    def _rank_failures(records: List[dict[str, Any]]) -> List[dict[str, Any]]:
        counts: Dict[str, int] = {}
        for record in records:
            for name in record.get("failed_dependencies") or []:
                counts[name] = counts.get(name, 0) + 1
        return [{"dependency": name, "count": count} for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)]
