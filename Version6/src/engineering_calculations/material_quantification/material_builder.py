"""Material quantification builder — Phase I.14."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.engineering_calculations.material_quantification.material_types import (
    DEFAULT_STEEL_GRADE,
    DETERMINATION_METHOD,
    CREATED_PHASE,
    MATERIAL_TYPE_REINFORCEMENT_STEEL,
    MaterialState,
    UNIT_KG,
    material_group_sort_key,
)


class MaterialBuilder:
    """Aggregate quantity records into material-centric records."""

    @staticmethod
    def build_records(quantity_records: List[dict[str, Any]]) -> List[dict[str, Any]]:
        groups: dict[Tuple[str, str, int | None], dict[str, Any]] = {}

        for quantity in sorted(
            quantity_records,
            key=lambda item: str(item.get("quantity_id", "")),
        ):
            contribution = MaterialBuilder._contribution_from_quantity(quantity)
            if contribution is None:
                continue

            key = (
                contribution["material_type"],
                contribution["steel_grade"],
                contribution["diameter_mm"],
            )
            bucket = groups.get(key)
            if bucket is None:
                bucket = MaterialBuilder._empty_bucket(
                    contribution["material_type"],
                    contribution["steel_grade"],
                    contribution["diameter_mm"],
                )
                groups[key] = bucket
            MaterialBuilder._accumulate(bucket, quantity, contribution)

        records = [
            MaterialBuilder._finalize_bucket(bucket)
            for _, bucket in sorted(groups.items(), key=lambda item: material_group_sort_key(item[0]))
        ]
        return records

    @staticmethod
    def _contribution_from_quantity(quantity: dict[str, Any]) -> dict[str, Any] | None:
        material_type = MATERIAL_TYPE_REINFORCEMENT_STEEL
        steel_grade = str(quantity.get("steel_grade") or DEFAULT_STEEL_GRADE)
        diameter_value = quantity.get("diameter_mm")
        diameter_mm = int(diameter_value) if diameter_value is not None else None

        if int(quantity.get("bar_count") or 0) == 0:
            return {
                "material_type": material_type,
                "steel_grade": steel_grade,
                "diameter_mm": diameter_mm,
                "total_weight_kg": 0.0,
                "total_cut_length_mm": 0,
                "total_bar_count": 0,
            }

        if diameter_mm is None:
            return None

        return {
            "material_type": material_type,
            "steel_grade": steel_grade,
            "diameter_mm": diameter_mm,
            "total_weight_kg": float(quantity.get("steel_weight_kg") or 0.0),
            "total_cut_length_mm": int(quantity.get("cut_length_mm") or 0),
            "total_bar_count": int(quantity.get("bar_count") or 0),
        }

    @staticmethod
    def _empty_bucket(
        material_type: str,
        steel_grade: str,
        diameter_mm: int | None,
    ) -> dict[str, Any]:
        return {
            "material_type": material_type,
            "steel_grade": steel_grade,
            "diameter_mm": diameter_mm,
            "unit": UNIT_KG,
            "total_weight_kg": 0.0,
            "total_cut_length_mm": 0,
            "total_bar_count": 0,
            "beam_ids": set(),
            "beam_marks": set(),
            "fabrication_marks": set(),
            "source_quantity_ids": [],
            "engineering_ready_flags": [],
            "quality_ready_flags": [],
            "quantities": [],
        }

    @staticmethod
    def _accumulate(
        bucket: dict[str, Any],
        quantity: dict[str, Any],
        contribution: dict[str, Any],
    ) -> None:
        bucket["total_weight_kg"] = round(
            float(bucket["total_weight_kg"]) + float(contribution["total_weight_kg"]),
            3,
        )
        bucket["total_cut_length_mm"] = int(bucket["total_cut_length_mm"]) + int(
            contribution["total_cut_length_mm"]
        )
        bucket["total_bar_count"] = int(bucket["total_bar_count"]) + int(
            contribution["total_bar_count"]
        )
        bucket["beam_ids"].add(str(quantity.get("beam_id", "")))
        bucket["beam_marks"].add(str(quantity.get("beam_mark", "")))
        for mark in quantity.get("fabrication_marks") or []:
            bucket["fabrication_marks"].add(str(mark))
        bucket["source_quantity_ids"].append(str(quantity.get("quantity_id", "")))
        bucket["engineering_ready_flags"].append(bool(quantity.get("engineering_ready")))
        bucket["quality_ready_flags"].append(bool(quantity.get("quality_ready")))
        bucket["quantities"].append(quantity)

    @staticmethod
    def _finalize_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
        quantities = bucket.pop("quantities")
        engineering_ready_flags = bucket.pop("engineering_ready_flags")
        quality_ready_flags = bucket.pop("quality_ready_flags")

        beam_ids = sorted(item for item in bucket["beam_ids"] if item)
        beam_marks = sorted(item for item in bucket["beam_marks"] if item)
        fabrication_marks = sorted(bucket["fabrication_marks"])
        source_quantity_ids = sorted(bucket["source_quantity_ids"])

        representative = sorted(
            quantities,
            key=lambda item: str(item.get("quantity_id", "")),
        )[0] if quantities else {}

        material_state = MaterialBuilder._resolve_material_state(
            int(bucket["total_bar_count"]),
            engineering_ready_flags,
            quality_ready_flags,
        )
        engineering_ready = all(engineering_ready_flags) if engineering_ready_flags else False
        quality_ready = all(quality_ready_flags) if quality_ready_flags else False

        provenance = dict(
            representative.get("calculation_provenance")
            or representative.get("provenance")
            or {}
        )
        completion = dict(representative.get("completion") or {})
        quality = dict(representative.get("quality") or {})
        engineering_state = representative.get("engineering_state")

        return {
            "material_id": None,
            "material_type": bucket["material_type"],
            "steel_grade": bucket["steel_grade"],
            "diameter_mm": bucket["diameter_mm"],
            "unit": bucket["unit"],
            "total_weight_kg": bucket["total_weight_kg"],
            "total_cut_length_mm": bucket["total_cut_length_mm"],
            "total_bar_count": bucket["total_bar_count"],
            "beam_count": len(beam_ids),
            "source_quantity_ids": source_quantity_ids,
            "beam_ids": beam_ids,
            "beam_marks": beam_marks,
            "fabrication_marks": fabrication_marks,
            "engineering_state": engineering_state,
            "engineering_ready": engineering_ready,
            "quality_ready": quality_ready,
            "material_state": material_state,
            "completion": completion,
            "quality": quality,
            "calculation_provenance": provenance,
            "provenance": provenance,
            "trace": list(representative.get("trace") or []),
            "traceability": dict(representative.get("traceability") or {}),
            "material_metadata": {
                "determination_method": DETERMINATION_METHOD,
                "source_phase": CREATED_PHASE,
                "dependency_graph_consulted": True,
            },
            "status": material_state,
        }

    @staticmethod
    def _resolve_material_state(
        total_bar_count: int,
        engineering_ready_flags: List[bool],
        quality_ready_flags: List[bool],
    ) -> str:
        if total_bar_count == 0:
            return MaterialState.EMPTY.value
        if not engineering_ready_flags:
            return MaterialState.UNKNOWN.value
        if not all(engineering_ready_flags):
            return MaterialState.DEFERRED.value
        if not all(quality_ready_flags):
            return MaterialState.BLOCKED.value
        return MaterialState.READY.value
