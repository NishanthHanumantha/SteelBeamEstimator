"""Load drawing and pipeline artifacts for reinforcement discovery analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.estimator_validation.comparison_utils import (
    find_schedule_start_row,
    load_json_if_exists,
    parse_schedule_rows,
)
from src.estimator_validation.audit_types import GENERATED_WORKBOOK_REL, resolve_estimator_workbook
from src.estimator_validation.drawing_interpretation.drawing_loader import DrawingLoader

PHASE = "Phase QA.ENGINEERING.2"
MODEL_VERSION = "5.23.0"
ENGINE_VERSION = "1.0.0"
OUTPUT_DIR_REL = Path("data/output/reinforcement_discovery_analysis")

DISCOVERY_STATUSES: Tuple[str, ...] = (
    "NOT_DETECTED",
    "TEXT_DETECTED",
    "CLASSIFIED",
    "ASSOCIATED",
    "ENGINEERING_OBJECT_CREATED",
    "NORMALIZED",
    "READY",
    "CALCULATED",
    "WRITTEN_TO_BBS",
    "WRITTEN_TO_EXCEL",
    "DISCOVERY_FAILED",
    "ASSOCIATION_FAILED",
    "NORMALIZATION_FAILED",
    "CALCULATION_DEFERRED",
    "EXPORT_SKIPPED",
)

FUNNEL_STAGES: Tuple[tuple[str, str], ...] = (
    ("drawing_callouts", "Drawing Callouts"),
    ("detected", "Detected"),
    ("classified", "Classified"),
    ("associated", "Associated"),
    ("engineering_objects", "Engineering Objects"),
    ("normalized", "Normalized"),
    ("ready", "READY"),
    ("calculated", "Calculated"),
    ("written_to_bbs", "Written to BBS"),
    ("written_to_excel", "Written to Excel"),
)


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_i = root / Path("data/output/phase_i")
    phase_g = root / Path("data/output/phase_g")
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "generated_workbook": root / GENERATED_WORKBOOK_REL,
        "estimator_workbook": resolve_estimator_workbook(root),
        "reinforcement_text": phase_g / "g_2_reinforcement_drawing/reinforcement_text.json",
        "engineering_properties": phase_g / "g_5_3_1_property_parser/engineering_properties.json",
        "resolved_properties": phase_g / "g_5_3_2_property_resolver/resolved_engineering_properties.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "reinforcement_readiness": phase_i / "i_2_1_calculation_readiness/reinforcement_readiness.json",
        "calculation_results": phase_i
        / "i_2_2_calculation_result_framework/engineering_calculation_results.json",
        "calculation_context": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "bar_identity": phase_i / "i_8_bar_identity/bar_identity_results.json",
        "bar_group": phase_i / "i_9_bar_group/bar_group_results.json",
        "bbs": phase_i / "i_10_bbs/bbs_results.json",
        "beam_schedule": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
        "engineering_report": phase_i / "i_16_engineering_report/engineering_reports.json",
        "drawing_interpretation": root
        / Path("data/output/estimator_validation/drawing_interpretation/drawing_interpretation.json"),
        "framing": root / Path("data/output/phase_a/framing_beams.json"),
    }


def round_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0 if numerator <= 0 else 100.0
    return round(min((numerator / denominator) * 100.0, 100.0), 2)


def _list(payload: Optional[dict[str, Any]], *keys: str) -> List[dict[str, Any]]:
    if payload is None:
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


class DiscoveryCollector:
    """Collect read-only drawing and pipeline snapshots."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        for key, path in self.paths.items():
            if key in {"output_dir", "generated_workbook", "estimator_workbook"}:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        reinforcement_text = payloads.get("reinforcement_text") or {}
        reinforcement_objects = payloads.get("reinforcement_objects") or {}
        reinforcement_readiness = payloads.get("reinforcement_readiness") or {}
        calculation_results = payloads.get("calculation_results") or {}
        engineering_properties = payloads.get("engineering_properties") or {}

        text_objects = reinforcement_text.get("text_objects") or []
        bars = reinforcement_objects.get("bars") or []
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
        bar_identities = _list(payloads.get("bar_identity"), "results")
        bar_groups = _list(payloads.get("bar_group"), "results")
        bbs_records = _list(payloads.get("bbs"), "results")
        beam_schedules = _list(payloads.get("beam_schedule"), "results")
        engineering_reports = _list(payloads.get("engineering_report"), "results")
        contexts = _list(payloads.get("calculation_context"), "contexts")

        framing = payloads.get("framing") or {}
        framing_beams = framing.get("beams") or framing.get("results") or []
        beam_marks = sorted(
            {
                str(item.get("beam_mark") or item.get("beam_id"))
                for item in framing_beams
                if item.get("beam_mark") or item.get("beam_id")
            }
        )

        excel_beams, excel_row_count = self._load_excel_schedule()
        calculated_bar_ids = self._collect_calculated_bar_ids(calc_results)
        bbs_bar_ids = self._collect_bbs_bar_ids(bbs_records)
        schedule_rows_by_bar = self._index_schedule_rows(beam_schedules)
        excel_rows_by_beam = self._index_excel_rows(excel_beams)

        indexes = self._build_indexes(
            text_objects,
            bars,
            engineering_properties,
            bbs_records,
            schedule_rows_by_bar,
            excel_rows_by_beam,
        )

        return {
            "paths": {key: str(path) for key, path in self.paths.items()},
            "load_status": dict(self.load_status),
            "text_objects": text_objects,
            "bars": bars,
            "contexts": contexts,
            "calculation_results": calc_results,
            "bar_identities": bar_identities,
            "bar_groups": bar_groups,
            "bbs_records": bbs_records,
            "beam_schedules": beam_schedules,
            "engineering_reports": engineering_reports,
            "engineering_properties": engineering_properties,
            "drawing_interpretation": payloads.get("drawing_interpretation") or {},
            "beam_marks": beam_marks,
            "calculated_bar_ids": sorted(calculated_bar_ids),
            "bbs_bar_ids": sorted(bbs_bar_ids),
            "excel_beams": excel_beams,
            "excel_row_count": excel_row_count,
            "schedule_rows_by_beam": schedule_rows_by_bar,
            "excel_rows_by_beam": excel_rows_by_beam,
            "indexes": indexes,
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
    def _collect_calculated_bar_ids(calc_results: List[dict[str, Any]]) -> Set[str]:
        calculated: Set[str] = set()
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
    def _collect_bbs_bar_ids(bbs_records: List[dict[str, Any]]) -> Set[str]:
        bar_ids: Set[str] = set()
        for record in bbs_records:
            for member_id in record.get("member_bar_ids") or []:
                bar_ids.add(str(member_id))
        return bar_ids

    @staticmethod
    def _index_schedule_rows(beam_schedules: List[dict[str, Any]]) -> Dict[str, List[dict[str, Any]]]:
        indexed: Dict[str, List[dict[str, Any]]] = {}
        for schedule in beam_schedules:
            beam_mark = str(schedule.get("beam_mark") or schedule.get("beam_id"))
            indexed[beam_mark] = schedule.get("rows") or []
        return indexed

    @staticmethod
    def _index_excel_rows(excel_beams: dict[str, Any]) -> Dict[str, List[Any]]:
        indexed: Dict[str, List[Any]] = {}
        for beam_mark, block in excel_beams.items():
            indexed[beam_mark] = getattr(block, "rows", []) or []
        return indexed

    @staticmethod
    def _build_indexes(
        text_objects: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        engineering_properties: dict[str, Any],
        bbs_records: List[dict[str, Any]],
        schedule_rows_by_beam: Dict[str, List[dict[str, Any]]],
        excel_rows_by_beam: Dict[str, List[Any]],
    ) -> dict[str, Any]:
        text_by_geometry: Dict[str, dict[str, Any]] = {}
        for item in text_objects:
            geometry_id = str(item.get("geometry_id") or "")
            if geometry_id:
                text_by_geometry[geometry_id] = item

        bars_by_geometry: Dict[str, dict[str, Any]] = {}
        bars_by_engineering_object: Dict[str, dict[str, Any]] = {}
        bars_by_callout_key: Dict[str, dict[str, Any]] = {}
        for bar in bars:
            trace = bar.get("traceability") or {}
            spec_trace = trace.get("specification_traceability") or {}
            for chain in spec_trace.get("property_chains") or []:
                geometry_id = str(chain.get("drawing_entity_id") or "")
                if geometry_id.startswith("TXT::"):
                    bars_by_geometry.setdefault(geometry_id, bar)
            engineering_object_id = str(trace.get("engineering_object_id") or "")
            if engineering_object_id:
                bars_by_engineering_object[engineering_object_id] = bar
            callout = str(trace.get("callout") or "")
            beam_id = str(bar.get("beam_id") or "")
            diameter = bar.get("diameter_mm")
            role = str(bar.get("role") or "")
            if callout and beam_id:
                key = f"{beam_id}|{callout}|{diameter}|{role}"
                bars_by_callout_key[key] = bar

        properties_by_geometry: Dict[str, List[dict[str, Any]]] = {}
        properties_by_text: Dict[str, List[dict[str, Any]]] = {}
        for prop in engineering_properties.get("properties") or engineering_properties.get("results") or []:
            source_entity = str(prop.get("source_entity_id") or "")
            if source_entity:
                properties_by_geometry.setdefault(source_entity, []).append(prop)
                if source_entity.startswith("TXT::"):
                    properties_by_text.setdefault(source_entity, []).append(prop)

        bbs_by_bar: Dict[str, dict[str, Any]] = {}
        for record in bbs_records:
            for member_id in record.get("member_bar_ids") or []:
                bbs_by_bar[str(member_id)] = record

        schedule_row_by_bar: Dict[str, dict[str, Any]] = {}
        for beam_mark, rows in schedule_rows_by_beam.items():
            for row in rows:
                for source_id in row.get("source_bar_ids") or []:
                    schedule_row_by_bar[str(source_id)] = row

        excel_row_by_bar: Dict[str, Any] = {}
        for beam_mark, rows in excel_rows_by_beam.items():
            for row in rows:
                key = f"{beam_mark}|{row.role_hint}|{row.diameter_mm}|{row.fabrication_mark or ''}"
                excel_row_by_bar[key] = row

        return {
            "text_by_geometry": text_by_geometry,
            "bars_by_geometry": bars_by_geometry,
            "bars_by_engineering_object": bars_by_engineering_object,
            "bars_by_callout_key": bars_by_callout_key,
            "properties_by_geometry": properties_by_geometry,
            "properties_by_text": properties_by_text,
            "bbs_by_bar": bbs_by_bar,
            "schedule_row_by_bar": schedule_row_by_bar,
            "excel_row_by_bar": excel_row_by_bar,
        }

    @staticmethod
    def beam_mark_from_owner(owner_id: str) -> Optional[str]:
        return DrawingLoader.beam_mark_from_owner(owner_id)
