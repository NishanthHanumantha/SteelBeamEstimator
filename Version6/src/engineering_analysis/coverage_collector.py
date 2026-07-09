"""Load engineering pipeline artifacts for read-only coverage analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.estimator_validation.comparison_utils import (
    find_schedule_start_row,
    load_json_if_exists,
    parse_schedule_rows,
)
from src.estimator_validation.audit_types import GENERATED_WORKBOOK_REL, resolve_estimator_workbook

PHASE = "Phase QA.ENGINEERING.1"
MODEL_VERSION = "5.22.0"
ENGINE_VERSION = "1.0.0"
OUTPUT_DIR_REL = Path("data/output/engineering_analysis")
PHASE_I_ROOT_REL = Path("data/output/phase_i")
PHASE_F_ROOT_REL = Path("data/output/phase_f")
PHASE_A_ROOT_REL = Path("data/output/phase_a")
PHASE_G_ROOT_REL = Path("data/output/phase_g")
DRAWING_INTERPRETATION_REL = Path(
    "data/output/estimator_validation/drawing_interpretation/drawing_interpretation.json"
)

STANDARD_DIAMETERS_MM: Tuple[int, ...] = (8, 10, 12, 16, 20, 25, 32)

REINFORCEMENT_CATEGORIES: Tuple[str, ...] = (
    "Top Main",
    "Bottom Main",
    "Top Extra",
    "Bottom Extra",
    "Support Bars",
    "Curtailment Bars",
    "Lap Bars",
    "Hooks",
    "Anchorage",
    "Stirrups",
    "Spacer Bars",
    "Chair Bars",
    "Side Face Bars",
    "Distribution Bars",
    "Other",
)

ROLE_TO_CATEGORY: Dict[str, str] = {
    "TOP_MAIN": "Top Main",
    "BOTTOM_MAIN": "Bottom Main",
    "EXTRA_TOP": "Top Extra",
    "TOP_EXTRA": "Top Extra",
    "EXTRA_BOTTOM": "Bottom Extra",
    "BOTTOM_EXTRA": "Bottom Extra",
    "STIRRUP": "Stirrups",
    "SIDE_BAR": "Side Face Bars",
    "SPACER": "Spacer Bars",
    "SPACER_BAR": "Spacer Bars",
    "LINK_BAR": "Support Bars",
    "STARTER": "Support Bars",
    "SFR": "Chair Bars",
    "CURTAILMENT": "Curtailment Bars",
    "LAP": "Lap Bars",
    "HOOK": "Hooks",
    "ANCHORAGE": "Anchorage",
    "DISTRIBUTION": "Distribution Bars",
    "UNKNOWN": "Other",
}

CALCULATION_STATES: Tuple[str, ...] = (
    "UNKNOWN",
    "READY",
    "DEFERRED",
    "BLOCKED",
    "COMPLETED",
    "FAILED",
)


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_i = root / PHASE_I_ROOT_REL
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "phase_i_root": phase_i,
        "generated_workbook": root / GENERATED_WORKBOOK_REL,
        "estimator_workbook": resolve_estimator_workbook(root),
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "reinforcement_readiness": phase_i / "i_2_1_calculation_readiness/reinforcement_readiness.json",
        "calculation_results": phase_i
        / "i_2_2_calculation_result_framework/engineering_calculation_results.json",
        "calculation_context": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "bar_identity": phase_i / "i_8_bar_identity/bar_identity_results.json",
        "bar_group": phase_i / "i_9_bar_group/bar_group_results.json",
        "bbs": phase_i / "i_10_bbs/bbs_results.json",
        "bbs_statistics": phase_i / "i_10_bbs/bbs_statistics.json",
        "steel_weight": phase_i / "i_11_steel_weight/steel_weight_results.json",
        "beam_summary": phase_i / "i_12_beam_summary/beam_summary_results.json",
        "quantity": phase_i / "i_13_quantity/quantity_results.json",
        "material": phase_i / "i_14_material_quantification/material_results.json",
        "beam_schedule": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
        "engineering_report": phase_i / "i_16_engineering_report/engineering_reports.json",
        "excel_export_validation": phase_i / "i_17_excel_export/excel_export_validation.json",
        "framing": root / PHASE_A_ROOT_REL / "framing_beams.json",
        "geometry_model": root / PHASE_F_ROOT_REL / "beam_geometry_model.json",
        "engineering_properties": root
        / PHASE_G_ROOT_REL
        / "g_5_3_1_property_parser/engineering_properties.json",
        "resolved_properties": root
        / PHASE_G_ROOT_REL
        / "g_5_3_2_property_resolver/resolved_engineering_properties.json",
        "reinforcement_text": root
        / PHASE_G_ROOT_REL
        / "g_2_reinforcement_drawing/reinforcement_text.json",
        "drawing_interpretation": root / DRAWING_INTERPRETATION_REL,
    }


def _load_list(payload: Optional[dict[str, Any]], *keys: str) -> List[dict[str, Any]]:
    if payload is None:
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _round_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0 if numerator <= 0 else 100.0
    return round(min((numerator / denominator) * 100.0, 100.0), 2)


class CoverageCollector:
    """Collect read-only snapshots from every major engineering pipeline stage."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        for key, path in self.paths.items():
            if key in {"output_dir", "phase_i_root", "generated_workbook", "estimator_workbook"}:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        reinforcement_objects = payloads.get("reinforcement_objects") or {}
        reinforcement_readiness = payloads.get("reinforcement_readiness") or {}
        calculation_results = payloads.get("calculation_results") or {}
        calculation_context = payloads.get("calculation_context") or {}
        framing = payloads.get("framing") or {}
        geometry_model = payloads.get("geometry_model") or {}
        engineering_properties = payloads.get("engineering_properties") or {}
        resolved_properties = payloads.get("resolved_properties") or {}
        reinforcement_text = payloads.get("reinforcement_text") or {}
        drawing_interpretation = payloads.get("drawing_interpretation") or {}

        bars = reinforcement_objects.get("bars") or []
        groups = reinforcement_objects.get("groups") or []
        readiness_bars = reinforcement_readiness.get("bars") or []
        readiness_by_id = {
            str(item.get("bar_id")): item.get("calculation_readiness") or {}
            for item in readiness_bars
        }

        for bar in bars:
            bar_id = str(bar.get("bar_id"))
            readiness = readiness_by_id.get(bar_id)
            if readiness:
                bar["calculation_readiness"] = readiness

        calc_results = calculation_results.get("results") or []
        contexts = calculation_context.get("contexts") or []
        framing_beams = framing.get("beams") or framing.get("results") or []
        geometry_beams = geometry_model.get("beams") or geometry_model.get("results") or []

        bar_identities = _load_list(payloads.get("bar_identity"), "results")
        bar_groups = _load_list(payloads.get("bar_group"), "results")
        bbs_records = _load_list(payloads.get("bbs"), "results")
        steel_weights = _load_list(payloads.get("steel_weight"), "results")
        beam_summaries = _load_list(payloads.get("beam_summary"), "results")
        quantities = _load_list(payloads.get("quantity"), "results")
        materials = _load_list(payloads.get("material"), "results")
        beam_schedules = _load_list(payloads.get("beam_schedule"), "results")
        engineering_reports = _load_list(payloads.get("engineering_report"), "results")

        excel_beams, excel_row_count = self._load_excel_schedule()

        drawing_entities = self._count_drawing_entities(
            bars,
            reinforcement_text,
            drawing_interpretation,
            engineering_properties,
        )
        property_graph_nodes = self._count_property_graph_nodes(bars, resolved_properties)
        specification_ids = {
            str(bar.get("specification_id"))
            for bar in bars
            if bar.get("specification_id")
        }
        engineering_object_ids = self._collect_engineering_object_ids(bars)
        geometry_associations = sum(
            1
            for context in contexts
            if str(context.get("association_status", "")).upper() == "VALID"
            or context.get("geometry_association_valid") is True
            or context.get("geometry_association_id")
            or context.get("association_id")
        )

        beam_ids_from_bars = sorted(
            {str(bar.get("beam_id")) for bar in bars if bar.get("beam_id")}
        )
        beam_ids_from_framing = sorted(
            {
                str(item.get("beam_mark") or item.get("beam_id"))
                for item in framing_beams
                if item.get("beam_mark") or item.get("beam_id")
            }
        )
        beam_ids_from_schedules = sorted(
            {
                str(item.get("beam_mark") or item.get("beam_id"))
                for item in beam_schedules
                if item.get("beam_mark") or item.get("beam_id")
            }
        )
        all_beam_ids = sorted(
            set(beam_ids_from_bars) | set(beam_ids_from_framing) | set(beam_ids_from_schedules)
        )

        calculated_bar_ids = self._collect_calculated_bar_ids(calc_results)
        ready_bar_ids = {
            str(bar.get("bar_id"))
            for bar in bars
            if str((bar.get("calculation_readiness") or {}).get("calculation_state", "")).upper()
            == "READY"
        }
        bbs_bar_ids = self._collect_bbs_bar_ids(bbs_records)
        schedule_bar_ids = self._collect_schedule_bar_ids(beam_schedules)
        excel_bar_ids = self._collect_excel_bar_ids(excel_beams)

        return {
            "paths": {key: str(path) for key, path in self.paths.items()},
            "load_status": dict(self.load_status),
            "drawing_entities": drawing_entities,
            "engineering_object_ids": sorted(engineering_object_ids),
            "property_graph_nodes": property_graph_nodes,
            "specification_ids": sorted(specification_ids),
            "geometry_associations": geometry_associations,
            "contexts": contexts,
            "bars": bars,
            "groups": groups,
            "readiness_bars": readiness_bars,
            "calculation_results": calc_results,
            "bar_identities": bar_identities,
            "bar_groups": bar_groups,
            "bbs_records": bbs_records,
            "bbs_statistics": payloads.get("bbs_statistics") or {},
            "steel_weights": steel_weights,
            "beam_summaries": beam_summaries,
            "quantities": quantities,
            "materials": materials,
            "beam_schedules": beam_schedules,
            "engineering_reports": engineering_reports,
            "framing_beams": framing_beams,
            "geometry_beams": geometry_beams,
            "drawing_interpretation": drawing_interpretation,
            "beam_ids": all_beam_ids,
            "beam_ids_from_bars": beam_ids_from_bars,
            "beam_ids_from_framing": beam_ids_from_framing,
            "beam_ids_from_schedules": beam_ids_from_schedules,
            "ready_bar_ids": sorted(ready_bar_ids),
            "calculated_bar_ids": sorted(calculated_bar_ids),
            "bbs_bar_ids": sorted(bbs_bar_ids),
            "schedule_bar_ids": sorted(schedule_bar_ids),
            "excel_bar_ids": sorted(excel_bar_ids),
            "excel_beams": excel_beams,
            "excel_row_count": excel_row_count,
            "generated_workbook": str(self.paths["generated_workbook"]),
            "estimator_workbook": str(self.paths["estimator_workbook"]),
        }

    def _load_excel_schedule(self) -> tuple[dict[str, Any], int]:
        workbook_path = self.paths["generated_workbook"]
        if not workbook_path.exists():
            self.load_status["generated_workbook"] = False
            return {}, 0
        self.load_status["generated_workbook"] = True
        try:
            from openpyxl import load_workbook

            workbook = load_workbook(workbook_path, data_only=True)
            worksheet = workbook.active
            start_row = find_schedule_start_row(worksheet)
            parsed = parse_schedule_rows(worksheet, start_row)
            row_count = sum(len(block.rows) for block in parsed.values())
            return parsed, row_count
        except Exception:
            return {}, 0

    @staticmethod
    def _count_drawing_entities(
        bars: List[dict[str, Any]],
        reinforcement_text: dict[str, Any],
        drawing_interpretation: dict[str, Any],
        engineering_properties: dict[str, Any],
    ) -> int:
        text_entities = _load_list(reinforcement_text, "text_entities", "entities", "results")
        if text_entities:
            return len(text_entities)
        interpretation_entities = _load_list(
            drawing_interpretation,
            "drawing_entities",
            "entities",
            "results",
        )
        if interpretation_entities:
            return len(interpretation_entities)
        property_objects = _load_list(engineering_properties, "properties", "objects", "results")
        if property_objects:
            return len(property_objects)
        entity_ids = set()
        callouts = set()
        for bar in bars:
            traceability = bar.get("traceability") or {}
            callout = traceability.get("callout")
            if callout:
                callouts.add(str(callout))
            entity_ids.add(str(traceability.get("drawing_entity_id") or ""))
            for chain in traceability.get("property_chains") or []:
                entity_ids.add(str(chain.get("drawing_entity_id") or ""))
        entity_ids.discard("")
        if callouts:
            return len(callouts)
        return len(entity_ids) if entity_ids else len(bars)

    @staticmethod
    def _count_property_graph_nodes(
        bars: List[dict[str, Any]],
        resolved_properties: dict[str, Any],
    ) -> int:
        resolved = _load_list(resolved_properties, "resolved_properties", "properties", "results")
        if resolved:
            return len(resolved)
        nodes = set()
        for bar in bars:
            traceability = bar.get("traceability") or {}
            nodes.add(str(traceability.get("engineering_object_id") or ""))
            for chain in traceability.get("property_chains") or []:
                nodes.add(str(chain.get("resolved_property_id") or ""))
                nodes.add(str((chain.get("engineering_property") or {}).get("property_id") or ""))
        nodes.discard("")
        return len(nodes)

    @staticmethod
    def _collect_engineering_object_ids(bars: List[dict[str, Any]]) -> set[str]:
        object_ids = set()
        for bar in bars:
            traceability = bar.get("traceability") or {}
            object_id = traceability.get("engineering_object_id")
            if object_id:
                object_ids.add(str(object_id))
        return object_ids

    @staticmethod
    def _collect_calculated_bar_ids(calc_results: List[dict[str, Any]]) -> set[str]:
        calculated = set()
        for result in calc_results:
            if str(result.get("calculation_type")) != "CUT_LENGTH":
                continue
            state = str(result.get("calculation_state", "")).upper()
            status = str(result.get("result_status", "")).upper()
            if state == "CALCULATED" or status == "SUCCESS":
                bar_id = result.get("input_bar_id")
                if bar_id:
                    calculated.add(str(bar_id))
        return calculated

    @staticmethod
    def _collect_bbs_bar_ids(bbs_records: List[dict[str, Any]]) -> set[str]:
        bar_ids: set[str] = set()
        for record in bbs_records:
            for member_id in record.get("member_bar_ids") or []:
                bar_ids.add(str(member_id))
            for member in record.get("members") or record.get("bar_members") or []:
                member_id = member.get("bar_id") or member.get("source_bar_id")
                if member_id:
                    bar_ids.add(str(member_id))
            for source_id in record.get("source_bar_ids") or []:
                bar_ids.add(str(source_id))
        return bar_ids

    @staticmethod
    def _collect_schedule_bar_ids(beam_schedules: List[dict[str, Any]]) -> set[str]:
        bar_ids: set[str] = set()
        for schedule in beam_schedules:
            for row in schedule.get("rows") or []:
                for source_id in row.get("source_bar_ids") or []:
                    bar_ids.add(str(source_id))
        return bar_ids

    @staticmethod
    def _collect_excel_bar_ids(excel_beams: dict[str, Any]) -> set[str]:
        identifiers: set[str] = set()
        for beam_mark, block in excel_beams.items():
            for row in getattr(block, "rows", []) or []:
                key = f"{beam_mark}|{row.role_hint}|{row.diameter_mm}|{row.fabrication_mark or ''}"
                identifiers.add(key)
        return identifiers


def category_for_role(role: Optional[str]) -> str:
    if not role:
        return "Other"
    return ROLE_TO_CATEGORY.get(str(role).upper(), "Other")


def round_pct(numerator: float, denominator: float) -> float:
    return _round_pct(numerator, denominator)
