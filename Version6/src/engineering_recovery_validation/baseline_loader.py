"""Construct PRE-J.1 baseline and POST-J.1 current pipeline snapshots."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.engineering_recovery_validation.validation_collector import MODEL_VERSION, PHASE, RECOVERY_PHASE


def _is_recovered_bar(bar: dict[str, Any], recovered_bar_ids: Set[str]) -> bool:
    bar_id = str(bar.get("bar_id") or "")
    if bar_id in recovered_bar_ids:
        return True
    return bool((bar.get("traceability") or {}).get("recovery_source"))


def _sum_steel(weights: List[dict[str, Any]]) -> dict[str, Any]:
    total = 0.0
    counted = 0
    deferred = 0
    for item in weights:
        value = item.get("weight_kg")
        if value is None:
            deferred += 1
            continue
        total += float(value)
        counted += 1
    return {
        "total_kg": round(total, 3),
        "weighted_bar_count": counted,
        "deferred_count": deferred,
    }


def _count_calculated_bars(bars: List[dict[str, Any]], calc_results: List[dict[str, Any]]) -> int:
    calc_bar_ids = {
        str(item.get("bar_id") or item.get("source_bar_id") or "")
        for item in calc_results
        if item.get("bar_id") or item.get("source_bar_id")
    }
    if calc_bar_ids:
        return len(calc_bar_ids)
    return len([bar for bar in bars if str(bar.get("status") or "").upper() in {"CALCULATED", "COMPLETED", "NORMALIZED"}])


def _schedule_row_count(beam_schedules: List[dict[str, Any]], payload: dict[str, Any] | None) -> int:
    if payload and payload.get("determination_count") is not None:
        return int(payload["determination_count"])
    return len(beam_schedules)


class BaselineLoader:
    """Derive PRE-J.1 baseline by subtracting recovered artifacts from POST state."""

    def build(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        recovery_index = snapshot.get("recovery_index") or {}
        recovered_bar_ids = set(recovery_index.get("recovered_bar_ids") or [])
        recovered_object_ids = set(recovery_index.get("recovered_object_ids") or [])
        recovered_spec_ids = set(recovery_index.get("recovered_spec_ids") or [])
        recovered_context_ids = set(recovery_index.get("recovered_context_ids") or [])

        post_metrics = self._pipeline_metrics(snapshot, recovered_bar_ids, mode="post")
        pre_metrics = self._pipeline_metrics(snapshot, recovered_bar_ids, mode="pre")

        recovery_health = snapshot.get("recovery_health") or {}
        if recovery_health.get("steel_coverage_before_percent") is not None:
            pre_metrics["inventory_coverage_percent"] = recovery_health["steel_coverage_before_percent"]
        if recovery_health.get("steel_coverage_after_percent") is not None:
            post_metrics["inventory_coverage_percent"] = recovery_health["steel_coverage_after_percent"]

        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "recovery_phase": RECOVERY_PHASE,
            "baseline_method": "SUBTRACTIVE_FILTER_FROM_POST_J1",
            "recovery_index": recovery_index,
            "pre_j1": pre_metrics,
            "post_j1": post_metrics,
            "inventory_count": snapshot.get("inventory_count", 0),
            "recovered_artifact_counts": {
                "engineering_objects": len(recovered_object_ids),
                "specifications": len(recovered_spec_ids),
                "calculation_contexts": len(recovered_context_ids),
                "normalized_bars": len(recovered_bar_ids),
            },
        }

    def _pipeline_metrics(
        self,
        snapshot: dict[str, Any],
        recovered_bar_ids: Set[str],
        mode: str,
    ) -> dict[str, Any]:
        bars = snapshot.get("bars") or []
        objects = snapshot.get("objects") or []
        specs = snapshot.get("specifications") or []
        contexts = snapshot.get("contexts") or []
        calc_results = snapshot.get("calculation_results") or []
        bbs_records = snapshot.get("bbs_records") or []
        steel_weights = snapshot.get("steel_weights") or []
        beam_schedules = snapshot.get("beam_schedules") or []
        excel_statistics = snapshot.get("excel_statistics") or {}
        beam_schedule_payload = snapshot.get("payloads", {}).get("beam_schedule_results") or {}

        recovery_index = snapshot.get("recovery_index") or {}
        recovered_object_ids = set(recovery_index.get("recovered_object_ids") or [])
        recovered_spec_ids = set(recovery_index.get("recovered_spec_ids") or [])
        recovered_context_ids = set(recovery_index.get("recovered_context_ids") or [])

        if mode == "pre":
            bars = [bar for bar in bars if not _is_recovered_bar(bar, recovered_bar_ids)]
            objects = [obj for obj in objects if str(obj.get("engineering_object_id") or obj.get("object_id") or "") not in recovered_object_ids]
            specs = [spec for spec in specs if str(spec.get("specification_id") or "") not in recovered_spec_ids]
            contexts = [ctx for ctx in contexts if str(ctx.get("context_id") or "") not in recovered_context_ids]
            bbs_records = [
                item
                for item in bbs_records
                if str(item.get("bar_id") or "") not in recovered_bar_ids
                and not recovered_bar_ids.intersection(set(item.get("member_bar_ids") or []))
            ]
            steel_weights = [item for item in steel_weights if str(item.get("bar_id") or "") not in recovered_bar_ids]
            calc_results = [
                item
                for item in calc_results
                if str(item.get("bar_id") or item.get("source_bar_id") or "") not in recovered_bar_ids
            ]

        steel_summary = _sum_steel(steel_weights)
        inventory_count = int(snapshot.get("inventory_count") or 0)
        normalized_count = len(bars)
        coverage = round((normalized_count / inventory_count) * 100, 2) if inventory_count else 0.0

        return {
            "engineering_objects": len(objects),
            "specifications": len(specs),
            "calculation_contexts": len(contexts),
            "normalized_bars": normalized_count,
            "calculated_bars": _count_calculated_bars(bars, calc_results),
            "bbs_rows": len(bbs_records),
            "beam_schedule_rows": _schedule_row_count(beam_schedules, beam_schedule_payload),
            "excel_rows": int(excel_statistics.get("rows_written") or 0),
            "steel_weight_kg": steel_summary["total_kg"],
            "steel_weighted_bars": steel_summary["weighted_bar_count"],
            "steel_deferred_bars": steel_summary["deferred_count"],
            "inventory_coverage_percent": coverage,
            "beams_with_bars": len({str(bar.get("beam_id")) for bar in bars if bar.get("beam_id")}),
        }
