"""Build estimator audit comparisons — Phase QA.1."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.estimator_validation.audit_types import DiscrepancySeverity, RootCause
from src.estimator_validation.comparison_utils import (
    beam_sort_key,
    find_schedule_start_row,
    index_reports_by_beam,
    index_schedules_by_beam,
    load_json_if_exists,
    load_workbook_pair,
    normalize_description,
    parse_schedule_rows,
    row_match_key,
    values_equal,
    workbook_structure_snapshot,
)
from src.estimator_validation.root_cause_classifier import RootCauseClassifier


class AuditBuilder:
    """Compare generated and estimator workbooks and build audit artifacts."""

    ENGINEERING_COLUMNS = {
        "diameter_mm": 4,
        "spacing_m": 5,
        "bar_count": 6,
        "development_length_m": 7,
        "cut_length_m": 8,
        "total_length_m": 9,
        "steel_weight_kg": 17,
    }

    def __init__(self, paths: dict[str, Path]) -> None:
        self._paths = paths
        self._classifier = RootCauseClassifier()
        self._pipeline = self._load_pipeline_data()

    def _load_pipeline_data(self) -> dict[str, Any]:
        root = self._paths["phase_i_root"]
        engineering_reports = load_json_if_exists(root / "i_16_engineering_report" / "engineering_reports.json") or {}
        beam_schedules = load_json_if_exists(root / "i_15_beam_schedule" / "beam_schedules.json") or {}
        return {
            "engineering_reports": index_reports_by_beam(engineering_reports.get("results", [])),
            "beam_schedules": index_schedules_by_beam(beam_schedules.get("results", [])),
        }

    def build(self) -> dict[str, Any]:
        generated_wb, estimator_wb, generated_ws, estimator_ws = load_workbook_pair(
            self._paths["generated_workbook"],
            self._paths["estimator_workbook"],
        )
        generated_start = find_schedule_start_row(generated_ws)
        estimator_start = find_schedule_start_row(estimator_ws)
        generated_beams = parse_schedule_rows(generated_ws, generated_start)
        estimator_beams = parse_schedule_rows(estimator_ws, estimator_start)

        structure = self._compare_structure(generated_wb, estimator_wb, generated_ws, estimator_ws)
        beam_comparison = self._compare_beams(generated_beams, estimator_beams)
        row_comparison, row_discrepancies = self._compare_rows(generated_beams, estimator_beams)
        cell_comparison = self._compare_cells(generated_beams, estimator_beams)
        summary_comparison = self._compare_summaries(generated_beams, estimator_beams)
        presentation = self._compare_presentation(generated_wb, estimator_wb, generated_ws, estimator_ws)
        missing_items = self._collect_missing_items(beam_comparison, row_comparison)
        traces = self._build_engineering_traces(generated_beams, estimator_beams, row_discrepancies)
        root_cause_report = self._build_root_cause_report(
            beam_comparison,
            row_discrepancies,
            cell_comparison,
            structure,
            traces,
        )
        fix_recommendations = self._build_fix_recommendations(root_cause_report)
        statistics = self._build_statistics(
            generated_beams,
            estimator_beams,
            beam_comparison,
            row_comparison,
            cell_comparison,
            presentation,
            root_cause_report,
        )
        return {
            "workbook_structure_report": structure,
            "beam_comparison": beam_comparison,
            "row_comparison": row_comparison,
            "cell_comparison": cell_comparison,
            "summary_comparison": summary_comparison,
            "presentation_report": presentation,
            "missing_items": missing_items,
            "engineering_trace_report": traces,
            "root_cause_report": root_cause_report,
            "fix_recommendations": fix_recommendations,
            "comparison_statistics": statistics,
        }

    def _compare_structure(self, generated_wb, estimator_wb, generated_ws, estimator_ws) -> dict[str, Any]:
        generated = workbook_structure_snapshot(generated_wb, generated_ws)
        estimator = workbook_structure_snapshot(estimator_wb, estimator_ws)
        differences = []
        for key in sorted(set(generated) | set(estimator)):
            if generated.get(key) != estimator.get(key):
                root_cause = self._classifier.classify_structure_difference(key)
                differences.append({
                    "category": key,
                    "generated": generated.get(key),
                    "estimator": estimator.get(key),
                    "status": "DIFFERENT",
                    "root_cause": root_cause.value,
                })
        return {
            "generated": generated,
            "estimator": estimator,
            "differences": differences,
            "difference_count": len(differences),
            "status": "PASS" if not differences else "INFORMATIONAL",
        }

    def _compare_beams(
        self,
        generated_beams: dict[str, Any],
        estimator_beams: dict[str, Any],
    ) -> dict[str, Any]:
        generated_marks = set(generated_beams)
        estimator_marks = set(estimator_beams)
        rows = []
        for mark in sorted(estimator_marks | generated_marks, key=beam_sort_key):
            in_generated = mark in generated_marks
            in_estimator = mark in estimator_marks
            generated_rows = len(generated_beams.get(mark, {}).rows) if in_generated else 0
            estimator_rows = len(estimator_beams.get(mark, {}).rows) if in_estimator else 0
            if in_generated and in_estimator:
                status = "PASS" if generated_rows == estimator_rows else "ROW_COUNT_DIFFERENT"
            elif in_estimator and not in_generated:
                status = "MISSING_IN_GENERATED"
            else:
                status = "EXTRA_IN_GENERATED"
            rows.append({
                "beam_mark": mark,
                "in_generated": in_generated,
                "in_estimator": in_estimator,
                "generated_row_count": generated_rows,
                "estimator_row_count": estimator_rows,
                "generated_clear_span_m": generated_beams.get(mark).clear_span_m if in_generated else None,
                "estimator_clear_span_m": estimator_beams.get(mark).clear_span_m if in_estimator else None,
                "status": status,
            })
        return {
            "beams": rows,
            "matching_beams": sum(1 for item in rows if item["status"] == "PASS"),
            "missing_beams": [item["beam_mark"] for item in rows if item["status"] == "MISSING_IN_GENERATED"],
            "extra_beams": [item["beam_mark"] for item in rows if item["status"] == "EXTRA_IN_GENERATED"],
            "duplicate_beams": [],
        }

    def _compare_rows(
        self,
        generated_beams: dict[str, Any],
        estimator_beams: dict[str, Any],
    ) -> tuple[dict[str, Any], List[dict[str, Any]]]:
        comparisons = []
        discrepancies: List[dict[str, Any]] = []
        for mark in sorted(estimator_beams.keys(), key=beam_sort_key):
            estimator_rows = sorted(
                estimator_beams.get(mark).rows,
                key=lambda row: (row.role_hint, row.diameter_mm or 0, row.normalized_description),
            )
            generated_block = generated_beams.get(mark)
            generated_rows = sorted(
                generated_block.rows if generated_block else [],
                key=lambda row: (row.role_hint, row.diameter_mm or 0, row.normalized_description),
            )
            max_len = max(len(estimator_rows), len(generated_rows))
            for index in range(max_len):
                estimator_row = estimator_rows[index] if index < len(estimator_rows) else None
                generated_row = generated_rows[index] if index < len(generated_rows) else None
                if estimator_row and generated_row:
                    status = "PASS" if row_match_key(estimator_row) == row_match_key(generated_row) else "DIFFERENT"
                    entry = {
                        "beam_mark": mark,
                        "row_index": index,
                        "description": estimator_row.description,
                        "role_hint": estimator_row.role_hint,
                        "diameter_mm": estimator_row.diameter_mm,
                        "estimator": "Present",
                        "generated": "Present",
                        "status": status,
                    }
                    comparisons.append(entry)
                    if status != "PASS":
                        discrepancies.append({**entry, "type": "different_row"})
                elif estimator_row:
                    entry = {
                        "beam_mark": mark,
                        "row_index": index,
                        "description": estimator_row.description,
                        "role_hint": estimator_row.role_hint,
                        "diameter_mm": estimator_row.diameter_mm,
                        "estimator": "Present",
                        "generated": "Missing",
                        "status": "MISSING_IN_GENERATED",
                    }
                    comparisons.append(entry)
                    discrepancies.append({**entry, "type": "missing_row"})
                elif generated_row:
                    entry = {
                        "beam_mark": mark,
                        "row_index": index,
                        "description": generated_row.description,
                        "role_hint": generated_row.role_hint,
                        "diameter_mm": generated_row.diameter_mm,
                        "estimator": "Missing",
                        "generated": "Present",
                        "status": "EXTRA_IN_GENERATED",
                    }
                    comparisons.append(entry)
                    discrepancies.append({**entry, "type": "extra_row"})
        return {"rows": comparisons}, discrepancies

    def _compare_cells(
        self,
        generated_beams: dict[str, Any],
        estimator_beams: dict[str, Any],
    ) -> dict[str, Any]:
        cells = []
        for mark in sorted(estimator_beams.keys(), key=beam_sort_key):
            estimator_block = estimator_beams[mark]
            generated_block = generated_beams.get(mark)
            if generated_block:
                if not values_equal(estimator_block.clear_span_m, generated_block.clear_span_m):
                    cells.append({
                        "beam_mark": mark,
                        "field": "clear_span_m",
                        "estimator_value": estimator_block.clear_span_m,
                        "generated_value": generated_block.clear_span_m,
                        "status": "DIFFERENT",
                    })
            estimator_map = {row_match_key(row): row for row in estimator_block.rows}
            generated_map = {row_match_key(row): row for row in (generated_block.rows if generated_block else [])}
            for key, estimator_row in estimator_map.items():
                generated_row = generated_map.get(key)
                if not generated_row:
                    continue
                for field in (
                    "diameter_mm",
                    "spacing_m",
                    "bar_count",
                    "development_length_m",
                    "cut_length_m",
                    "total_length_m",
                    "steel_weight_kg",
                ):
                    left = getattr(estimator_row, field)
                    right = getattr(generated_row, field)
                    if not values_equal(left, right):
                        cells.append({
                            "beam_mark": mark,
                            "description": estimator_row.description,
                            "field": field,
                            "estimator_value": left,
                            "generated_value": right,
                            "status": "DIFFERENT",
                        })
        matching = sum(1 for item in cells if item["status"] == "PASS")
        return {
            "cells": cells,
            "matching_cells": matching,
            "different_cells": len(cells),
            "status": "PASS" if not cells else "FAIL",
        }

    def _compare_summaries(
        self,
        generated_beams: dict[str, Any],
        estimator_beams: dict[str, Any],
    ) -> dict[str, Any]:
        def totals(beams: dict[str, Any]) -> dict[str, float]:
            total_bars = 0.0
            total_cut = 0.0
            total_weight = 0.0
            for block in beams.values():
                for row in block.rows:
                    total_bars += float(row.bar_count or 0)
                    total_cut += float(row.cut_length_m or 0)
                    total_weight += float(row.steel_weight_kg or 0)
            return {
                "total_bars": total_bars,
                "total_cut_length_m": total_cut,
                "total_steel_weight_kg": total_weight,
            }
        generated_totals = totals(generated_beams)
        estimator_totals = totals(estimator_beams)
        differences = []
        for key in generated_totals:
            if not values_equal(generated_totals[key], estimator_totals[key]):
                differences.append({
                    "metric": key,
                    "generated": generated_totals[key],
                    "estimator": estimator_totals[key],
                })
        return {
            "generated": generated_totals,
            "estimator": estimator_totals,
            "differences": differences,
            "status": "PASS" if not differences else "FAIL",
        }

    def _compare_presentation(self, generated_wb, estimator_wb, generated_ws, estimator_ws) -> dict[str, Any]:
        generated = workbook_structure_snapshot(generated_wb, generated_ws)
        estimator = workbook_structure_snapshot(estimator_wb, estimator_ws)
        differences = []
        for key in ("merged_cell_count", "max_row", "column_widths", "page_margins", "freeze_panes"):
            if generated.get(key) != estimator.get(key):
                differences.append({
                    "category": key,
                    "generated": generated.get(key),
                    "estimator": estimator.get(key),
                    "priority": "INFORMATIONAL",
                })
        return {
            "differences": differences,
            "difference_count": len(differences),
            "status": "INFORMATIONAL",
        }

    def _collect_missing_items(
        self,
        beam_comparison: dict[str, Any],
        row_comparison: dict[str, Any],
    ) -> dict[str, Any]:
        missing_rows = [
            item for item in row_comparison["rows"]
            if item["status"] == "MISSING_IN_GENERATED"
        ]
        return {
            "missing_beams": beam_comparison["missing_beams"],
            "extra_beams": beam_comparison["extra_beams"],
            "missing_rows": missing_rows,
            "missing_row_count": len(missing_rows),
        }

    def _trace_row(self, beam_mark: str, description: str, role_hint: str) -> dict[str, Any]:
        reports = self._pipeline["engineering_reports"]
        schedules = self._pipeline["beam_schedules"]
        report = reports.get(beam_mark)
        schedule = schedules.get(beam_mark)
        trace = {
            "beam_mark": beam_mark,
            "description": description,
            "role_hint": role_hint,
            "layers": {},
            "first_missing_layer": None,
            "present_in_estimator_only": True,
        }
        if report:
            schedule_table = (report.get("sections") or {}).get("schedule_table") or []
            matched = [
                row for row in schedule_table
                if normalize_description(row.get("description")) == normalize_description(description)
                or normalize_description(row.get("role", "")).endswith(role_hint.split("_")[-1].lower())
            ]
            trace["layers"]["engineering_report"] = "present" if matched else "missing"
            if not matched and trace["first_missing_layer"] is None:
                trace["first_missing_layer"] = "engineering_report"
            trace["engineering_report_clear_span_mm"] = (report.get("sections") or {}).get("header", {}).get("clear_span_mm")
        else:
            trace["layers"]["engineering_report"] = "missing"
            trace["first_missing_layer"] = "engineering_report"
        if schedule:
            rows = schedule.get("rows") or []
            matched = [row for row in rows if normalize_description(row.get("description")) == normalize_description(description)]
            trace["layers"]["beam_schedule"] = "present" if matched else "missing"
            if not matched and trace["first_missing_layer"] is None:
                trace["first_missing_layer"] = "beam_schedule"
        else:
            trace["layers"]["beam_schedule"] = "missing"
            if trace["first_missing_layer"] is None:
                trace["first_missing_layer"] = "beam_schedule"
        trace["layers"]["excel"] = "missing"
        return trace

    def _build_engineering_traces(
        self,
        generated_beams: dict[str, Any],
        estimator_beams: dict[str, Any],
        row_discrepancies: List[dict[str, Any]],
    ) -> dict[str, Any]:
        traces = []
        for item in row_discrepancies:
            if item.get("type") != "missing_row":
                continue
            trace = self._trace_row(item["beam_mark"], item["description"], item["role_hint"])
            traces.append(trace)
        return {"traces": traces, "trace_count": len(traces)}

    def _build_root_cause_report(
        self,
        beam_comparison: dict[str, Any],
        row_discrepancies: List[dict[str, Any]],
        cell_comparison: dict[str, Any],
        structure: dict[str, Any],
        traces: dict[str, Any],
    ) -> dict[str, Any]:
        entries = []
        trace_by_key = {
            (trace["beam_mark"], normalize_description(trace["description"])): trace
            for trace in traces.get("traces", [])
        }
        for item in row_discrepancies:
            trace = trace_by_key.get((item["beam_mark"], normalize_description(item["description"])), {})
            root_cause = self._classifier.classify_missing_generated_row(
                item["beam_mark"],
                item["description"],
                trace,
            )
            entries.append({
                "type": item["type"],
                "beam_mark": item["beam_mark"],
                "description": item["description"],
                "root_cause": root_cause.value,
                "trace": trace,
                "severity": self._classifier.severity_for(item["type"], root_cause),
            })
        for item in cell_comparison["cells"]:
            trace = trace_by_key.get((item["beam_mark"], normalize_description(item.get("description", ""))), {})
            root_cause = self._classifier.classify_value_difference(item["field"], item["beam_mark"], trace)
            entries.append({
                "type": "value_difference",
                "beam_mark": item["beam_mark"],
                "field": item["field"],
                "description": item.get("description"),
                "root_cause": root_cause.value,
                "severity": self._classifier.severity_for("value_difference", root_cause),
            })
        for item in structure["differences"]:
            root_cause = RootCause.TEMPLATE_LAYOUT
            entries.append({
                "type": "structure_difference",
                "category": item["category"],
                "root_cause": root_cause.value,
                "severity": DiscrepancySeverity.INFO.value,
            })
        distribution = Counter(entry["root_cause"] for entry in entries)
        return {
            "entries": entries,
            "entry_count": len(entries),
            "root_cause_distribution": dict(distribution),
        }

    def _build_fix_recommendations(self, root_cause_report: dict[str, Any]) -> dict[str, Any]:
        recommendations = []
        seen = set()
        for entry in root_cause_report["entries"]:
            key = (entry.get("beam_mark"), entry.get("description"), entry.get("field"), entry.get("root_cause"))
            if key in seen:
                continue
            seen.add(key)
            root_cause = RootCause(entry["root_cause"])
            problem = entry.get("description") or entry.get("field") or entry.get("category") or entry["type"]
            recommendations.append(
                self._classifier.build_recommendation(
                    problem=str(problem),
                    root_cause=root_cause,
                    beam_mark=str(entry.get("beam_mark") or ""),
                    description=str(entry.get("description") or ""),
                )
            )
        return {"recommendations": recommendations, "recommendation_count": len(recommendations)}

    def _build_statistics(
        self,
        generated_beams: dict[str, Any],
        estimator_beams: dict[str, Any],
        beam_comparison: dict[str, Any],
        row_comparison: dict[str, Any],
        cell_comparison: dict[str, Any],
        presentation: dict[str, Any],
        root_cause_report: dict[str, Any],
    ) -> dict[str, Any]:
        row_rows = row_comparison["rows"]
        return {
            "total_beams_estimator": len(estimator_beams),
            "total_beams_generated": len(generated_beams),
            "matching_beams": beam_comparison["matching_beams"],
            "missing_beams": len(beam_comparison["missing_beams"]),
            "extra_beams": len(beam_comparison["extra_beams"]),
            "matching_rows": sum(1 for item in row_rows if item["status"] == "PASS"),
            "missing_rows": sum(1 for item in row_rows if item["status"] == "MISSING_IN_GENERATED"),
            "extra_rows": sum(1 for item in row_rows if item["status"] == "EXTRA_IN_GENERATED"),
            "different_cells": cell_comparison["different_cells"],
            "presentation_differences": presentation["difference_count"],
            "engineering_differences": cell_comparison["different_cells"] + sum(
                1 for item in row_rows if item["status"] != "PASS"
            ),
            "root_cause_distribution": root_cause_report["root_cause_distribution"],
            "confidence": "HIGH" if self._pipeline["engineering_reports"] else "MEDIUM",
        }
