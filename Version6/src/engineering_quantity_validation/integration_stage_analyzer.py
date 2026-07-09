"""Integration stage evaluation for recovered objects."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.engineering_quantity_validation.quantity_traceability import (
    QUANTITY_CALC_TYPES,
    QuantityState,
    STAGE_ORDER,
)


class IntegrationStageAnalyzer:
    """Evaluate each downstream stage for recovered objects."""

    def evaluate_object(self, snapshot: dict[str, Any], registry_entry: dict[str, Any]) -> dict[str, Any]:
        bar_id = str(registry_entry.get("normalized_bar_id") or "")
        bar = snapshot.get("bar_by_id", {}).get(bar_id, {})
        calc_results = snapshot.get("calc_by_bar", {}).get(bar_id, [])
        steel = snapshot.get("steel_weight_by_bar", {}).get(bar_id, {})
        bbs = snapshot.get("bbs_by_bar", {}).get(bar_id)
        beam_id = str(registry_entry.get("beam_id") or bar.get("beam_id") or "")

        stages = {
            "engineering_object": self._stage_engineering_object(registry_entry, bar),
            "normalization": self._stage_normalization(bar),
            "calculation": self._stage_calculation(calc_results, snapshot, bar_id),
            "steel_weight": self._stage_steel_weight(steel, calc_results),
            "engineering_report": self._stage_engineering_report(snapshot, beam_id, bar_id),
            "beam_schedule": self._stage_beam_schedule(snapshot, beam_id, bar_id),
            "excel_export": self._stage_excel_export(snapshot, bar_id, beam_id),
            "qa_aggregation": self._stage_qa_aggregation(snapshot, bar_id, steel, bbs),
        }

        first_failure = self._first_failure(stages)
        current_state = self._current_quantity_state(stages, first_failure, steel, calc_results)
        return {
            "stages": stages,
            "first_failure_stage": first_failure.get("stage"),
            "first_failure_label": first_failure.get("label"),
            "primary_blocking_reason": first_failure.get("reason"),
            "current_quantity_state": current_state,
        }

    def analyze_all(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        entries = snapshot.get("registry_entries") or []
        analyses = [self.evaluate_object(snapshot, entry) for entry in entries]
        distribution: Dict[str, int] = {}
        for analysis in analyses:
            stage = analysis.get("first_failure_stage") or "unknown"
            distribution[stage] = distribution.get(stage, 0) + 1
        return {
            "recovered_count": len(entries),
            "analyses": analyses,
            "first_failure_distribution": distribution,
        }

    @staticmethod
    def _stage_engineering_object(registry_entry: dict[str, Any], bar: dict[str, Any]) -> dict[str, Any]:
        if registry_entry.get("recovered_object_id") and bar.get("bar_id"):
            return {"status": "PASS", "reason": None}
        return {"status": "FAIL", "reason": "Recovered engineering object missing from production registry"}

    @staticmethod
    def _stage_normalization(bar: dict[str, Any]) -> dict[str, Any]:
        status = str(bar.get("status") or "").upper()
        if status == "NORMALIZED":
            return {"status": "PASS", "reason": None}
        return {"status": "FAIL", "reason": f"Bar normalization state is {status or 'UNKNOWN'}"}

    def _stage_calculation(
        self,
        calc_results: List[dict[str, Any]],
        snapshot: dict[str, Any],
        bar_id: str,
    ) -> dict[str, Any]:
        if not calc_results:
            return {"status": "FAIL", "reason": "No calculation results registered for recovered bar"}

        calc_by_type = {
            str(item.get("calculation_type") or ""): item for item in calc_results if item.get("calculation_type")
        }
        for calc_type in QUANTITY_CALC_TYPES:
            result = calc_by_type.get(calc_type)
            if result is None:
                if calc_type in {"CUT_LENGTH", "BAR_IDENTITY", "SHAPE_CODE"}:
                    return {
                        "status": "FAIL",
                        "reason": f"{calc_type} result missing from calculation framework",
                    }
                continue
            result_status = str(result.get("result_status") or "").upper()
            calculation_state = str(result.get("calculation_state") or "").upper()
            if result_status in {"FAILED", "DEPENDENCY_BLOCKED", "BLOCKED"} or calculation_state == "FAILED":
                return {
                    "status": "FAIL",
                    "reason": f"{calc_type} {result_status or calculation_state}",
                    "calculation_type": calc_type,
                    "result_status": result_status,
                }
            if calc_type == "STEEL_WEIGHT" and calculation_state == "DEFERRED":
                continue

        readiness = snapshot.get("readiness_by_bar", {}).get(bar_id)
        if readiness is None:
            return {
                "status": "FAIL",
                "reason": "Recovered bar absent from calculation readiness registry",
            }

        cut_length = snapshot.get("cut_length_by_bar", {}).get(bar_id)
        if cut_length is None:
            return {"status": "FAIL", "reason": "Cut length result missing for recovered bar"}

        return {"status": "PASS", "reason": None}

    @staticmethod
    def _stage_steel_weight(steel: dict[str, Any], calc_results: List[dict[str, Any]]) -> dict[str, Any]:
        if not steel:
            return {"status": "FAIL", "reason": "Steel weight result missing for recovered bar"}

        status = str(steel.get("status") or "").upper()
        result_status = str(steel.get("result_status") or "").upper()
        weight = steel.get("weight_kg")

        if weight is not None and float(weight) > 0:
            return {"status": "PASS", "reason": None}

        calc_steel = next(
            (item for item in calc_results if str(item.get("calculation_type") or "") == "STEEL_WEIGHT"),
            {},
        )
        trace = steel.get("trace") or []
        reason_parts = []
        if steel.get("cut_length") is None and steel.get("cut_length_mm") is None:
            reason_parts.append("Missing cut length")
        if status == "DEFERRED" or result_status == "PRESERVED_DEFERRED":
            reason_parts.append("Weight engine deferred")
        if calc_steel.get("result_status") == "PRESERVED_DEFERRED":
            reason_parts.append("Calculation steel weight preserved deferred")
        if trace:
            reason_parts.append(str(trace[-1]))

        return {
            "status": "FAIL",
            "reason": "; ".join(reason_parts) or "Steel weight not generated",
            "weight_status": status or result_status,
        }

    @staticmethod
    def _stage_engineering_report(snapshot: dict[str, Any], beam_id: str, bar_id: str) -> dict[str, Any]:
        reports = snapshot.get("engineering_reports") or []
        beam_report = next(
            (item for item in reports if str(item.get("beam_id") or item.get("beam_mark") or "") == beam_id),
            None,
        )
        if beam_report is None:
            return {"status": "FAIL", "reason": f"No engineering report entry for beam {beam_id}"}

        completion = beam_report.get("completion") or {}
        bars_total = completion.get("bars_total")
        if bar_id in str(beam_report):
            return {"status": "PASS", "reason": None}

        return {
            "status": "FAIL",
            "reason": f"Recovered bar not represented in engineering report for {beam_id} (report bars_total={bars_total})",
        }

    @staticmethod
    def _stage_beam_schedule(snapshot: dict[str, Any], beam_id: str, bar_id: str) -> dict[str, Any]:
        schedules = snapshot.get("beam_schedules") or []
        schedule = next(
            (item for item in schedules if str(item.get("beam_id") or item.get("beam_mark") or "") == beam_id),
            None,
        )
        if schedule is None:
            return {"status": "FAIL", "reason": f"No beam schedule entry for {beam_id}"}

        completion = schedule.get("completion") or {}
        if bar_id in str(schedule):
            return {"status": "PASS", "reason": None}
        return {
            "status": "FAIL",
            "reason": (
                f"Recovered bar not represented in beam schedule for {beam_id} "
                f"(schedule bars_total={completion.get('bars_total')})"
            ),
        }

    @staticmethod
    def _stage_excel_export(snapshot: dict[str, Any], bar_id: str, beam_id: str) -> dict[str, Any]:
        registries = snapshot.get("registries") or {}
        steel_registry = registries.get("steel_weight") or {}
        if bar_id not in str(steel_registry):
            return {"status": "FAIL", "reason": "Recovered bar absent from steel weight registry used by Excel export"}

        excel_stats = snapshot.get("excel_statistics") or {}
        if int(excel_stats.get("rows_written") or 0) <= 0:
            return {"status": "FAIL", "reason": "Excel export rows not written"}

        return {
            "status": "FAIL",
            "reason": f"Recovered bar {bar_id} not visible in Excel quantity export for beam {beam_id}",
        }

    @staticmethod
    def _stage_qa_aggregation(
        snapshot: dict[str, Any],
        bar_id: str,
        steel: dict[str, Any],
        bbs: dict[str, Any] | None,
    ) -> dict[str, Any]:
        accuracy = snapshot.get("accuracy_report") or {}
        kpis = accuracy.get("current_kpis") or {}
        if steel.get("weight_kg") is not None and bbs:
            return {"status": "PASS", "reason": None}
        return {
            "status": "FAIL",
            "reason": (
                "Recovered bar quantities not visible in QA dashboard "
                f"(steel_quantity_coverage={kpis.get('steel_quantity_coverage_percent')}%)"
            ),
        }

    @staticmethod
    def _first_failure(stages: Dict[str, dict[str, Any]]) -> dict[str, Any]:
        for stage_key, label in STAGE_ORDER:
            stage = stages.get(stage_key) or {}
            if stage.get("status") != "PASS":
                return {
                    "stage": stage_key,
                    "label": label,
                    "reason": stage.get("reason") or "Stage failed",
                }
        return {"stage": None, "label": None, "reason": None}

    @staticmethod
    def _current_quantity_state(
        stages: Dict[str, dict[str, Any]],
        first_failure: dict[str, Any],
        steel: dict[str, Any],
        calc_results: List[dict[str, Any]],
    ) -> str:
        first_stage = first_failure.get("stage")
        if first_stage == "engineering_object":
            return QuantityState.OBJECT_CREATED.value
        if first_stage == "normalization":
            return QuantityState.NORMALIZED.value
        if first_stage == "calculation":
            calc_by_type = {
                str(item.get("calculation_type") or ""): item for item in calc_results if item.get("calculation_type")
            }
            blocked = any(
                str(calc_by_type.get(calc_type, {}).get("result_status") or "").upper()
                in {"FAILED", "DEPENDENCY_BLOCKED", "BLOCKED"}
                for calc_type in QUANTITY_CALC_TYPES
            )
            return QuantityState.BLOCKED.value if blocked else QuantityState.FAILED.value
        if first_stage == "steel_weight":
            status = str(steel.get("status") or steel.get("result_status") or "").upper()
            if "DEFERRED" in status:
                return QuantityState.DEFERRED.value
            return QuantityState.BLOCKED.value
        if first_stage == "engineering_report":
            return QuantityState.CALCULATED.value
        if first_stage == "beam_schedule":
            return QuantityState.STEEL_READY.value
        if first_stage == "excel_export":
            return QuantityState.BBS_WRITTEN.value
        if first_stage == "qa_aggregation":
            return QuantityState.EXCEL_WRITTEN.value
        return QuantityState.QA_VISIBLE.value
