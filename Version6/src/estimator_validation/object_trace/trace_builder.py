"""Build engineering object traces — Phase QA.2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.estimator_validation.comparison_utils import (
    beam_sort_key,
    find_schedule_start_row,
    load_json_if_exists,
    load_workbook_pair,
    parse_schedule_rows,
    row_match_key,
)
from src.estimator_validation.object_trace.geometry_comparator import GeometryComparator
from src.estimator_validation.object_trace.identity_matcher import (
    compute_match_confidence,
    identity_from_estimator_row,
    identity_from_pipeline_row,
)
from src.estimator_validation.object_trace.trace_matcher import TraceMatcher
from src.estimator_validation.object_trace.trace_registry import TraceRegistry
from src.estimator_validation.object_trace.trace_types import (
    LAYER_TO_ROOT_CAUSE,
    TRACE_LAYERS,
    EngineeringIdentity,
    LayerMatch,
    ObjectTrace,
    TraceRootCause,
    default_paths,
)


class TraceBuilder:
    """Trace every estimator reinforcement row through the engineering pipeline."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.matcher = TraceMatcher()
        self.geometry = GeometryComparator()
        self.registry_builder = TraceRegistry()

    def build(self) -> dict[str, Any]:
        pipeline = self._load_pipeline()
        estimator_beams, generated_beams = self._load_workbook_beams()
        traces = self._build_traces(estimator_beams, generated_beams, pipeline)
        identity_matching = self._build_identity_matching(traces, estimator_beams, generated_beams)
        geometry_comparison = self.geometry.compare_beams(
            estimator_beams,
            generated_beams,
            pipeline["beam_summaries_by_beam"],
            pipeline["reports_by_beam"],
            pipeline["calculation_contexts"],
            pipeline["framing_beams"],
            pipeline["geometry_beams"],
        )
        qa1_validation = self._validate_qa1(traces, estimator_beams, generated_beams)
        registry = self.registry_builder.build(traces)
        root_cause_matrix = self._build_root_cause_matrix(traces)
        statistics = self._build_statistics(traces, identity_matching, qa1_validation)
        return {
            "phase": "Phase QA.2",
            "trace_version": "1.0.0",
            "generated_workbook": str(self.paths["generated_workbook"]),
            "estimator_workbook": str(self.paths["estimator_workbook"]),
            "engineering_traces": [trace.to_dict() for trace in traces],
            "trace_registry": registry,
            "identity_matching": identity_matching,
            "geometry_comparison": geometry_comparison,
            "qa1_validation": qa1_validation,
            "root_cause_matrix": root_cause_matrix,
            "trace_statistics": statistics,
            "pipeline_data_loaded": pipeline["load_status"],
        }

    def _load_workbook_beams(self):
        _, _, generated_ws, estimator_ws = load_workbook_pair(
            self.paths["generated_workbook"],
            self.paths["estimator_workbook"],
        )
        generated_start = find_schedule_start_row(generated_ws)
        estimator_start = find_schedule_start_row(estimator_ws)
        return (
            parse_schedule_rows(estimator_ws, estimator_start),
            parse_schedule_rows(generated_ws, generated_start),
        )

    def _load_pipeline(self) -> dict[str, Any]:
        load_status: Dict[str, bool] = {}
        data: Dict[str, Any] = {}

        def load_list(key: str, path_key: str, list_name: str = "results") -> List[dict[str, Any]]:
            path = self.paths[path_key]
            payload = load_json_if_exists(path)
            load_status[path_key] = payload is not None
            if payload is None:
                return []
            if list_name == "contexts":
                return payload.get("contexts") or []
            if list_name == "objects":
                return payload.get("objects") or payload.get("results") or []
            return payload.get("results") or []

        data["bar_identities"] = load_list("bar_identity", "bar_identity")
        data["bar_groups"] = load_list("bar_group", "bar_group")
        data["bbs_records"] = load_list("bbs", "bbs")
        data["steel_weights"] = load_list("steel_weight", "steel_weight")
        data["beam_summaries"] = load_list("beam_summary", "beam_summary")
        data["quantities"] = load_list("quantity", "quantity")
        data["materials"] = load_list("material", "material")
        data["beam_schedules"] = load_list("beam_schedule", "beam_schedule")
        data["engineering_reports"] = load_list("engineering_report", "engineering_report")
        data["reinforcement_objects"] = load_list("reinforcement_objects", "reinforcement_objects", "objects")
        data["calculation_contexts"] = load_list("calculation_context", "calculation_context", "contexts")

        framing_payload = load_json_if_exists(self.paths["framing"])
        load_status["framing"] = framing_payload is not None
        data["framing_beams"] = (
            framing_payload.get("beams") or framing_payload.get("results") or []
            if framing_payload
            else []
        )

        geometry_payload = load_json_if_exists(self.paths["geometry_model"])
        load_status["geometry_model"] = geometry_payload is not None
        data["geometry_beams"] = (
            geometry_payload.get("beams") or geometry_payload.get("results") or []
            if geometry_payload
            else []
        )

        data["schedules_by_beam"] = {
            str(item.get("beam_mark") or item.get("beam_id")): item for item in data["beam_schedules"]
        }
        data["reports_by_beam"] = {
            str(item.get("beam_mark") or item.get("beam_id")): item for item in data["engineering_reports"]
        }
        data["beam_summaries_by_beam"] = {
            str(item.get("beam_mark") or item.get("beam_id")): item for item in data["beam_summaries"]
        }
        data["load_status"] = load_status
        return data

    def _build_traces(
        self,
        estimator_beams,
        generated_beams,
        pipeline: dict[str, Any],
    ) -> List[ObjectTrace]:
        traces: List[ObjectTrace] = []
        skip_layers = self._skip_layers_for_pipeline(pipeline)
        for beam_mark in sorted(estimator_beams.keys(), key=beam_sort_key):
            estimator_block = estimator_beams[beam_mark]
            generated_block = generated_beams.get(beam_mark)
            generated_rows = generated_block.rows if generated_block else []
            schedule = pipeline["schedules_by_beam"].get(beam_mark, {})
            report = pipeline["reports_by_beam"].get(beam_mark, {})
            schedule_rows = schedule.get("rows") or []
            report_rows = report.get("sections", {}).get("schedule_table") or []
            steel_grade = None
            if report:
                steel_grade = report.get("sections", {}).get("project_information", {}).get("steel_grade")

            for index, row in enumerate(estimator_block.rows):
                identity = identity_from_estimator_row(beam_mark, row, steel_grade=steel_grade)
                trace = ObjectTrace(estimator_row_index=index, identity=identity)
                trace.layer_matches["drawing"] = self.matcher.match_drawing_objects(
                    identity, pipeline["reinforcement_objects"]
                )
                trace.layer_matches["identity"] = self.matcher.match_bar_identities(
                    identity, pipeline["bar_identities"]
                )
                trace.layer_matches["bar_group"] = self.matcher.match_member_group(
                    identity,
                    pipeline["bar_groups"],
                    "bar_group",
                    "bar_group_id",
                )
                trace.layer_matches["bbs"] = self.matcher.match_member_group(
                    identity,
                    pipeline["bbs_records"],
                    "bbs",
                    "bbs_id",
                )
                trace.layer_matches["steel_weight"] = self.matcher.match_beam_level(
                    identity,
                    pipeline["steel_weights"],
                    "steel_weight",
                    "beam_id",
                    "weight_id",
                    "role",
                )
                trace.layer_matches["beam_summary"] = self.matcher.match_beam_level(
                    identity,
                    [pipeline["beam_summaries_by_beam"][beam_mark]]
                    if beam_mark in pipeline["beam_summaries_by_beam"]
                    else [],
                    "beam_summary",
                    "beam_mark",
                    "beam_summary_id",
                    "roles",
                )
                trace.layer_matches["quantity"] = self.matcher.match_beam_level(
                    identity,
                    [item for item in pipeline["quantities"] if str(item.get("beam_mark")) == beam_mark],
                    "quantity",
                    "beam_mark",
                    "quantity_id",
                    "roles",
                )
                trace.layer_matches["material"] = self._match_material(identity, pipeline["materials"])
                trace.layer_matches["beam_schedule"] = self.matcher.match_schedule_table(
                    identity, schedule_rows, "beam_schedule"
                )
                trace.layer_matches["engineering_report"] = self.matcher.match_schedule_table(
                    identity, report_rows, "engineering_report"
                )
                trace.layer_matches["excel"] = self.matcher.match_excel_row(identity, generated_rows)

                self._apply_layer_skips(trace.layer_matches, skip_layers)
                trace.first_missing_layer = self._first_missing_layer(trace.layer_matches)
                trace.root_cause = self._root_cause_for_layer(trace.first_missing_layer)
                trace.confidence = self._trace_confidence(trace.layer_matches)
                trace.trace_status = "PASS" if trace.first_missing_layer is None else "FAIL"
                traces.append(trace)
        return traces

    @staticmethod
    def _match_material(identity: EngineeringIdentity, materials: List[dict[str, Any]]) -> LayerMatch:
        for material in materials:
            marks = material.get("beam_marks") or material.get("beam_ids") or []
            if identity.beam_mark in [str(item) for item in marks]:
                return LayerMatch(
                    layer="material",
                    status="PASS",
                    confidence=80,
                    matched_id=str(material.get("material_id") or ""),
                )
        return LayerMatch(layer="material", status="FAIL", confidence=0)

    @staticmethod
    def _skip_layers_for_pipeline(pipeline: dict[str, Any]) -> set[str]:
        skipped: set[str] = set()
        if not pipeline.get("reinforcement_objects"):
            skipped.add("drawing")
        if not pipeline.get("framing_beams"):
            skipped.update({"drawing"})
        if not pipeline.get("geometry_beams"):
            pass
        return skipped

    @staticmethod
    def _apply_layer_skips(layer_matches: Dict[str, LayerMatch], skip_layers: set[str]) -> None:
        for layer in skip_layers:
            if layer in layer_matches and layer_matches[layer].status == "FAIL":
                layer_matches[layer] = LayerMatch(
                    layer=layer,
                    status="SKIP",
                    confidence=0,
                    matched_id="source_unavailable",
                )

    @staticmethod
    def _first_missing_layer(layer_matches: Dict[str, LayerMatch]) -> Optional[str]:
        for layer in TRACE_LAYERS:
            match = layer_matches.get(layer)
            if match is None:
                return layer
            if match.status == "SKIP":
                continue
            if match.status != "PASS":
                return layer
        return None

    @staticmethod
    def _root_cause_for_layer(layer: Optional[str]) -> str:
        if layer is None:
            return TraceRootCause.GROUND_TRUTH_DIFFERENCE.value
        return LAYER_TO_ROOT_CAUSE.get(layer, TraceRootCause.UNKNOWN).value

    @staticmethod
    def _trace_confidence(layer_matches: Dict[str, LayerMatch]) -> int:
        scores = [match.confidence for match in layer_matches.values() if match.status == "PASS"]
        return max(scores) if scores else 0

    def _build_identity_matching(
        self,
        traces: List[ObjectTrace],
        estimator_beams,
        generated_beams,
    ) -> dict[str, Any]:
        exact = partial = identity_matches = positional_only = false_positional = false_identity = 0
        confidence_distribution: Dict[str, int] = {}
        entries: List[dict[str, Any]] = []

        for trace in traces:
            identity = trace.identity
            generated_block = generated_beams.get(identity.beam_mark)
            generated_rows = generated_block.rows if generated_block else []
            estimator_block = estimator_beams[identity.beam_mark]
            estimator_row = estimator_block.rows[trace.estimator_row_index]

            best_generated = None
            best_score = 0
            for row in generated_rows:
                candidate = identity_from_estimator_row(identity.beam_mark, row)
                score = compute_match_confidence(identity, candidate)
                if score > best_score:
                    best_score = score
                    best_generated = row

            positional_index_match = (
                trace.estimator_row_index < len(generated_rows)
                and generated_rows[trace.estimator_row_index].normalized_description
                == estimator_row.normalized_description
            )
            identity_match = best_score >= 80
            excel_pass = trace.layer_matches.get("excel", LayerMatch("excel", "FAIL")).status == "PASS"

            if best_score >= 100:
                exact += 1
            elif best_score >= 80:
                partial += 1
            if identity_match:
                identity_matches += 1
            if positional_index_match and not identity_match:
                false_positional += 1
            if identity_match and not positional_index_match:
                false_identity += 1
            if positional_index_match and not identity_match:
                positional_only += 1

            bucket = str(best_score if best_score >= 80 else "UNMATCHED")
            confidence_distribution[bucket] = confidence_distribution.get(bucket, 0) + 1
            entries.append(
                {
                    "beam_mark": identity.beam_mark,
                    "description": identity.description,
                    "role": identity.role,
                    "diameter_mm": identity.diameter_mm,
                    "identity_match": identity_match,
                    "excel_layer_pass": excel_pass,
                    "positional_index_match": positional_index_match,
                    "match_confidence": best_score,
                    "first_missing_layer": trace.first_missing_layer,
                }
            )

        return {
            "exact_matches": exact,
            "partial_matches": partial,
            "identity_matches": identity_matches,
            "positional_only_matches": positional_only,
            "false_positional_mismatches": false_positional,
            "false_identity_mismatches": false_identity,
            "confidence_distribution": confidence_distribution,
            "entries": entries,
        }

    def _validate_qa1(
        self,
        traces: List[ObjectTrace],
        estimator_beams,
        generated_beams,
    ) -> dict[str, Any]:
        qa1_path = self.paths["qa1_output_dir"] / "row_comparison.json"
        qa1_stats_path = self.paths["qa1_output_dir"] / "comparison_statistics.json"
        qa1_row_comparison = load_json_if_exists(qa1_path) or {}
        qa1_stats = load_json_if_exists(qa1_stats_path) or {}

        identity_pass_rows = sum(
            1 for trace in traces if trace.layer_matches.get("excel", LayerMatch("excel", "FAIL")).status == "PASS"
        )
        identity_partial_rows = sum(
            1
            for trace in traces
            if trace.confidence >= 80
            and trace.layer_matches.get("excel", LayerMatch("excel", "FAIL")).status != "PASS"
        )

        positional_matching_rows = qa1_stats.get("matching_rows", 0)
        qa1_claim_zero_matches = positional_matching_rows == 0

        positional_false_mismatch_count = 0
        for trace in traces:
            generated_block = generated_beams.get(trace.identity.beam_mark)
            if not generated_block:
                continue
            if trace.estimator_row_index >= len(generated_block.rows):
                continue
            positional_row = generated_block.rows[trace.estimator_row_index]
            identity_row_match = trace.layer_matches.get("excel", LayerMatch("excel", "FAIL")).status == "PASS"
            if not identity_row_match and row_match_key(positional_row) == trace.identity.identity_key().split("|")[1:]:
                positional_false_mismatch_count += 1

        conclusion = (
            "QA.1 matching_rows=0 is partially caused by positional comparison. "
            "Identity matching finds additional correspondences in generated Excel."
            if identity_pass_rows > 0 and qa1_claim_zero_matches
            else "QA.1 positional matching results are consistent with identity matching."
        )
        if identity_pass_rows == 0 and qa1_claim_zero_matches:
            conclusion = (
                "QA.1 matching_rows=0 is TRUE under both positional and identity matching. "
                "Generated Excel rows do not match estimator identities."
            )

        return {
            "qa1_matching_rows_reported": positional_matching_rows,
            "qa1_matching_rows_zero": qa1_claim_zero_matches,
            "identity_excel_pass_rows": identity_pass_rows,
            "identity_partial_matches_not_in_excel": identity_partial_rows,
            "total_estimator_rows": len(traces),
            "positional_false_mismatch_estimate": positional_false_mismatch_count,
            "qa1_row_comparison_available": qa1_path.exists(),
            "conclusion": conclusion,
            "identity_matching_used": True,
            "positional_matching_used_in_qa1": True,
        }

    def _build_root_cause_matrix(self, traces: List[ObjectTrace]) -> dict[str, Any]:
        matrix: Dict[str, Dict[str, int]] = {}
        for trace in traces:
            layer = trace.first_missing_layer or "NONE"
            cause = trace.root_cause
            matrix.setdefault(layer, {})
            matrix[layer][cause] = matrix[layer].get(cause, 0) + 1
        return {
            "layers": list(TRACE_LAYERS) + ["NONE"],
            "matrix": matrix,
            "unknown_count": sum(1 for trace in traces if trace.root_cause == TraceRootCause.UNKNOWN.value),
            "unknown_pct": round(
                100.0
                * sum(1 for trace in traces if trace.root_cause == TraceRootCause.UNKNOWN.value)
                / max(len(traces), 1),
                2,
            ),
        }

    def _build_statistics(
        self,
        traces: List[ObjectTrace],
        identity_matching: dict[str, Any],
        qa1_validation: dict[str, Any],
    ) -> dict[str, Any]:
        first_missing: Dict[str, int] = {}
        root_causes: Dict[str, int] = {}
        for trace in traces:
            layer = trace.first_missing_layer or "NONE"
            first_missing[layer] = first_missing.get(layer, 0) + 1
            root_causes[trace.root_cause] = root_causes.get(trace.root_cause, 0) + 1
        return {
            "total_estimator_rows_traced": len(traces),
            "trace_pass_count": sum(1 for trace in traces if trace.trace_status == "PASS"),
            "trace_fail_count": sum(1 for trace in traces if trace.trace_status == "FAIL"),
            "first_missing_layer_distribution": first_missing,
            "root_cause_distribution": root_causes,
            "identity_match_quality": {
                "exact_matches": identity_matching["exact_matches"],
                "partial_matches": identity_matching["partial_matches"],
                "identity_matches": identity_matching["identity_matches"],
                "false_positional_mismatches": identity_matching["false_positional_mismatches"],
            },
            "qa1_validation": qa1_validation,
            "confidence": "HIGH",
        }
