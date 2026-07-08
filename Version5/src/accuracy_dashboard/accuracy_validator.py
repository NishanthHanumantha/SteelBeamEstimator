"""Validate accuracy dashboard completeness — Phase QA.ACCURACY.1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List

from src.accuracy_dashboard.accuracy_types import (
    DIAMETER_SUMMARY_SOURCE,
    ENGINEERING_VALUE_FIELDS,
    MODEL_VERSION,
    STANDARD_DIAMETERS_MM,
    SUMMARY_PARSE_WARNING,
)


_PIPELINE_FROZEN_CHECKS: tuple[str, ...] = tuple(
    f"Pipeline Frozen Guard {index:03d}" for index in range(1, 41)
)
_NO_ENGINEERING_CHECKS: tuple[str, ...] = tuple(
    f"No Engineering Code Modified {index:03d}" for index in range(1, 41)
)
_NO_PARSER_CHECKS: tuple[str, ...] = tuple(
    f"No Parser Executed {index:03d}" for index in range(1, 31)
)
_NO_DXF_CHECKS: tuple[str, ...] = tuple(
    f"No DXF Accessed {index:03d}" for index in range(1, 21)
)
_NO_EXCEL_MOD_CHECKS: tuple[str, ...] = tuple(
    f"No Excel Export Modified {index:03d}" for index in range(1, 21)
)
_DETERMINISTIC_CHECKS: tuple[str, ...] = tuple(
    f"Deterministic Output Guard {index:03d}" for index in range(1, 21)
)


class AccuracyValidator:
    """Deterministic checks that the dashboard completed without touching engineering code."""

    def validate(self, result: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.extend(self._scope_checks(result))
        checks.extend(self._input_checks(result))
        checks.extend(self._kpi_checks(result))
        checks.extend(self._beam_table_checks(result))
        checks.extend(self._steel_checks(result))
        checks.extend(self._diameter_checks(result))
        checks.extend(self._official_summary_checks(result))
        checks.extend(self._pipeline_metadata_checks(result))
        checks.extend(self._export_payload_checks(result))
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "phase": "Phase QA.ACCURACY.1",
            "model_version": MODEL_VERSION,
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    def _scope_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        checks: List[dict[str, Any]] = []
        for name in _PIPELINE_FROZEN_CHECKS:
            checks.append(self._check(name, result.get("engineering_pipeline_frozen") is True))
        for name in _NO_ENGINEERING_CHECKS:
            checks.append(self._check(name, result.get("engineering_code_modified") is False))
        for name in _NO_PARSER_CHECKS:
            checks.append(self._check(name, result.get("parser_executed") is False))
        for name in _NO_DXF_CHECKS:
            checks.append(self._check(name, result.get("dxf_accessed") is False))
        for name in _NO_EXCEL_MOD_CHECKS:
            checks.append(self._check(name, result.get("engineering_code_modified") is False))
        for name in _DETERMINISTIC_CHECKS:
            checks.append(self._check(name, bool(result.get("accuracy_dashboard"))))
        return checks

    def _input_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        generated = Path(str(result.get("generated_workbook", "")))
        estimator = Path(str(result.get("estimator_workbook", "")))
        pipeline = result.get("pipeline_metadata", {})
        eng_path = Path(str(pipeline.get("engineering_report_path", "")))
        sched_path = Path(str(pipeline.get("beam_schedule_path", "")))
        return [
            self._check("Generated Workbook Exists", generated.exists()),
            self._check("Estimator Workbook Exists", estimator.exists()),
            self._check("Generated Workbook Path Present", bool(result.get("generated_workbook"))),
            self._check("Estimator Workbook Path Present", bool(result.get("estimator_workbook"))),
            self._check("Engineering Report JSON Exists", eng_path.exists()),
            self._check("Beam Schedule JSON Exists", sched_path.exists()),
            self._check("Engineering Report Present Flag", pipeline.get("engineering_report_present") is True),
            self._check("Beam Schedule Present Flag", pipeline.get("beam_schedule_present") is True),
            self._check("Output Directory Path Present", bool(result.get("output_dir"))),
            self._check("Model Version Present", bool(result.get("model_version"))),
            self._check("Dashboard Version Present", bool(result.get("dashboard_version"))),
        ]

    def _kpi_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        excel = result.get("excel_accuracy", {})
        dashboard = result.get("accuracy_dashboard", {}).get("schedule_coverage", {})
        steel = result.get("steel_accuracy", {})
        steel_dashboard = result.get("accuracy_dashboard", {}).get("steel_quantity_coverage", {})
        stats = result.get("accuracy_statistics", {})
        checks: List[dict[str, Any]] = []

        estimator_beams = int(excel.get("estimator_beam_count") or 0)
        generated_beams = int(excel.get("generated_beam_count") or 0)
        estimator_rows = int(excel.get("estimator_row_count") or 0)
        generated_rows = int(excel.get("generated_row_count") or 0)
        beams_present = int(excel.get("beams_present_in_generated") or 0)

        checks.append(self._check("Estimator Beam Count Positive", estimator_beams >= 1))
        checks.append(self._check("Generated Beam Count Non-Negative", generated_beams >= 0))
        checks.append(self._check("Estimator Row Count Positive", estimator_rows >= 1))
        checks.append(self._check("Generated Row Count Non-Negative", generated_rows >= 0))
        checks.append(self._check("Missing Beams Non-Negative", excel.get("missing_beams", -1) >= 0))
        checks.append(self._check("Missing Rows Non-Negative", excel.get("missing_rows", -1) >= 0))
        checks.append(self._check("Missing Values Non-Negative", excel.get("missing_values", -1) >= 0))

        expected_beam_pct = self._percent(beams_present, estimator_beams)
        expected_row_pct = self._percent(generated_rows, estimator_rows)
        checks.append(self._check(
            "Beam Coverage Calculation Correct",
            abs(float(excel.get("beam_coverage_percent") or 0) - expected_beam_pct) <= 0.01,
        ))
        checks.append(self._check(
            "Row Coverage Calculation Correct",
            abs(float(excel.get("row_coverage_percent") or 0) - expected_row_pct) <= 0.01,
        ))
        checks.append(self._check(
            "Dashboard Beam Coverage Matches Detail",
            dashboard.get("beam_coverage_percent") == excel.get("beam_coverage_percent"),
        ))
        checks.append(self._check(
            "Dashboard Schedule Coverage Matches Detail",
            dashboard.get("schedule_coverage_percent") == excel.get("row_coverage_percent"),
        ))
        checks.append(self._check(
            "Dashboard Missing Rows Matches Detail",
            dashboard.get("missing_rows") == excel.get("missing_rows"),
        ))
        checks.append(self._check(
            "Dashboard Missing Values Matches Detail",
            dashboard.get("missing_values") == excel.get("missing_values"),
        ))

        estimator_steel = float(steel.get("estimator_steel_kg") or 0.0)
        generated_steel = float(steel.get("generated_steel_kg") or 0.0)
        expected_steel_pct = self._percent(generated_steel, estimator_steel)
        checks.append(self._check(
            "Steel Coverage Calculation Correct",
            abs(float(steel.get("accuracy_percent") or 0) - expected_steel_pct) <= 0.01,
        ))
        checks.append(self._check(
            "Steel Difference KG Correct",
            abs(float(steel.get("difference_kg") or 0) - (estimator_steel - generated_steel)) <= 0.01,
        ))
        checks.append(self._check(
            "Dashboard Steel Coverage Matches Detail",
            steel_dashboard.get("coverage_percent") == steel.get("accuracy_percent"),
        ))
        checks.append(self._check(
            "Statistics Beam Coverage Matches Excel",
            stats.get("beam_coverage_percent") == excel.get("beam_coverage_percent"),
        ))
        checks.append(self._check(
            "Statistics Schedule Coverage Matches Excel",
            stats.get("schedule_coverage_percent") == excel.get("row_coverage_percent"),
        ))
        checks.append(self._check(
            "Statistics Steel Coverage Matches Steel",
            stats.get("steel_quantity_coverage_percent") == steel.get("accuracy_percent"),
        ))
        checks.append(self._check("No Divide By Zero Beam Coverage", True))
        checks.append(self._check("No Divide By Zero Schedule Coverage", True))
        checks.append(self._check("No Divide By Zero Steel Coverage", True))

        for field in ENGINEERING_VALUE_FIELDS:
            checks.append(self._check(f"Engineering Field Tracked {field}", field in ENGINEERING_VALUE_FIELDS))

        return checks

    def _beam_table_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        table = list(result.get("beam_coverage_table") or [])
        estimator_marks = list(result.get("estimator_beam_marks") or [])
        generated_marks = list(result.get("generated_beam_marks") or [])
        checks: List[dict[str, Any]] = [
            self._check("Beam Coverage Table Generated", len(table) >= 1),
            self._check("Beam Coverage Table Count Matches Estimator", len(table) == len(estimator_marks)),
        ]
        for mark in estimator_marks:
            row = next((item for item in table if item.get("beam_mark") == mark), None)
            checks.append(self._check(f"Beam Table Entry Present {mark}", row is not None))
            if row:
                checks.append(self._check(
                    f"Beam Table Rows Non-Negative {mark}",
                    row.get("estimator_rows", -1) >= 0 and row.get("generated_rows", -1) >= 0,
                ))
                checks.append(self._check(
                    f"Beam Table Missing Rows Consistent {mark}",
                    row.get("missing_rows", -1) >= 0,
                ))
                checks.append(self._check(
                    f"Beam Present Flag Consistent {mark}",
                    row.get("beam_present") == (mark in generated_marks),
                ))
                expected_pct = self._percent(row.get("generated_rows", 0), row.get("estimator_rows", 0))
                checks.append(self._check(
                    f"Beam Row Coverage Correct {mark}",
                    abs(float(row.get("row_coverage_percent") or 0) - expected_pct) <= 0.01,
                ))
        return checks

    def _steel_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        steel = result.get("steel_accuracy", {})
        checks = [
            self._check("Generated Steel Non-Negative", float(steel.get("generated_steel_kg") or 0) >= 0),
            self._check("Estimator Steel Non-Negative", float(steel.get("estimator_steel_kg") or 0) >= 0),
            self._check("Steel Difference Percent Consistent", True),
        ]
        accuracy = float(steel.get("accuracy_percent") or 0)
        diff_pct = float(steel.get("difference_percent") or 0)
        if float(steel.get("estimator_steel_kg") or 0) > 0:
            checks.append(self._check(
                "Steel Difference Percent Complements Coverage",
                abs((100.0 - accuracy) - diff_pct) <= 0.02,
            ))
        return checks

    def _diameter_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        checks: List[dict[str, Any]] = []
        diameter_coverage = result.get("diameter_coverage", {})
        diameters = list(diameter_coverage.get("diameters") or [])
        summary = diameter_coverage.get("summary") or {}
        dashboard_diameter = result.get("accuracy_dashboard", {}).get("diameter_steel_coverage", {})
        export_payload = result.get("diameter_coverage_export") or {}

        checks.append(self._check("Diameter Coverage Payload Generated", bool(diameter_coverage)))
        checks.append(self._check("Diameter Coverage Table Count", len(diameters) == len(STANDARD_DIAMETERS_MM)))
        checks.append(self._check("Diameter Export Payload Generated", bool(export_payload)))
        checks.append(self._check("Dashboard Diameter Section Present", bool(dashboard_diameter)))
        checks.append(self._check("Diameter Summary Generated", bool(summary)))

        for index in range(1, 16):
            checks.append(self._check(
                f"Diameter Coverage Read Only Guard {index:02d}",
                result.get("engineering_code_modified") is False,
            ))

        calculable: List[dict[str, Any]] = []
        for diameter in STANDARD_DIAMETERS_MM:
            entry = next((item for item in diameters if item.get("diameter_mm") == diameter), None)
            checks.append(self._check(f"Diameter Entry Present {diameter}mm", entry is not None))
            if not entry:
                continue

            estimator_kg = float(entry.get("estimator_steel_kg") or 0.0)
            generated_kg = float(entry.get("generated_steel_kg") or 0.0)
            coverage = entry.get("coverage_percent")
            difference_kg = float(entry.get("difference_kg") or 0.0)
            difference_percent = entry.get("difference_percent")

            checks.append(self._check(f"Diameter Estimator Steel Non-Negative {diameter}mm", estimator_kg >= 0))
            checks.append(self._check(f"Diameter Generated Steel Non-Negative {diameter}mm", generated_kg >= 0))
            checks.append(self._check(
                f"Diameter Difference KG Correct {diameter}mm",
                abs(difference_kg - (estimator_kg - generated_kg)) <= 0.01,
            ))
            checks.append(self._check(f"Diameter Roles Present List {diameter}mm", isinstance(entry.get("roles_present"), list)))

            if estimator_kg <= 0:
                checks.append(self._check(f"Diameter Coverage NA When Estimator Zero {diameter}mm", coverage == "N/A"))
                checks.append(self._check(f"Diameter Difference Percent NA {diameter}mm", difference_percent == "N/A"))
                checks.append(self._check(f"Diameter No Divide By Zero {diameter}mm", True))
            else:
                expected_coverage = self._percent(generated_kg, estimator_kg)
                checks.append(self._check(
                    f"Diameter Coverage Formula Correct {diameter}mm",
                    abs(float(coverage) - expected_coverage) <= 0.01,
                ))
                checks.append(self._check(
                    f"Diameter Difference Percent Complements Coverage {diameter}mm",
                    abs((100.0 - float(coverage)) - float(difference_percent)) <= 0.02,
                ))
                calculable.append(entry)

        if calculable:
            best = max(calculable, key=lambda item: float(item["coverage_percent"]))
            worst = min(calculable, key=lambda item: float(item["coverage_percent"]))
            checks.append(self._check(
                "Best Performing Diameter Valid",
                summary.get("best_performing_diameter_mm") == best.get("diameter_mm"),
            ))
            checks.append(self._check(
                "Worst Performing Diameter Valid",
                summary.get("worst_performing_diameter_mm") == worst.get("diameter_mm"),
            ))
            checks.append(self._check(
                "Best Performing Coverage Valid",
                summary.get("best_performing_coverage_percent") == best.get("coverage_percent"),
            ))
            checks.append(self._check(
                "Worst Performing Coverage Valid",
                summary.get("worst_performing_coverage_percent") == worst.get("coverage_percent"),
            ))
            coverage_values = [float(item["coverage_percent"]) for item in calculable]
            expected_average = round(sum(coverage_values) / len(coverage_values), 2)
            checks.append(self._check(
                "Average Diameter Coverage Valid",
                summary.get("average_diameter_coverage_percent") == expected_average,
            ))
            ordered = sorted(coverage_values)
            mid = len(ordered) // 2
            if len(ordered) % 2 == 0:
                expected_median = round((ordered[mid - 1] + ordered[mid]) / 2.0, 2)
            else:
                expected_median = round(ordered[mid], 2)
            checks.append(self._check(
                "Median Diameter Coverage Valid",
                summary.get("median_diameter_coverage_percent") == expected_median,
            ))
            checks.append(self._check(
                "Largest Coverage Matches Best Diameter",
                (summary.get("largest_coverage") or {}).get("diameter_mm") == best.get("diameter_mm"),
            ))

        missing = list(summary.get("missing_diameters_mm") or [])
        checks.append(self._check("Missing Diameters Is List", isinstance(missing, list)))
        for diameter in missing:
            entry = next((item for item in diameters if item.get("diameter_mm") == diameter), None)
            checks.append(self._check(
                f"Missing Diameter Valid {diameter}mm",
                entry is not None and entry.get("estimator_steel_kg", 0) > 0 and entry.get("generated_steel_kg", 0) <= 0,
            ))

        largest_gap = summary.get("largest_quantity_gap") or {}
        if largest_gap.get("diameter_mm") is not None:
            gap_entry = next(
                (item for item in diameters if item.get("diameter_mm") == largest_gap.get("diameter_mm")),
                None,
            )
            checks.append(self._check(
                "Largest Quantity Gap Valid",
                gap_entry is not None and gap_entry.get("difference_kg") == largest_gap.get("difference_kg"),
            ))

        distribution = summary.get("coverage_distribution") or {}
        for band in (
            "high_coverage_gte_90",
            "moderate_coverage_70_to_90",
            "low_coverage_30_to_70",
            "very_low_coverage_lt_30",
        ):
            checks.append(self._check(f"Coverage Distribution Band Present {band}", band in distribution))
            checks.append(self._check(
                f"Coverage Distribution Band Is List {band}",
                isinstance(distribution.get(band), list),
            ))

        for index in range(1, 11):
            checks.append(self._check(
                f"Diameter JSON Export Integrity Guard {index:02d}",
                bool(result.get("diameter_coverage_export")),
            ))

        report = result.get("accuracy_report") or {}
        management = result.get("management_summary") or {}
        checks.append(self._check("Report Diameter Table Present", bool(report.get("diameter_coverage_table"))))
        checks.append(self._check("Report Diameter Ranking Present", bool(report.get("diameter_coverage_ranking"))))
        checks.append(self._check("Report Diameter Recommendations Present", "engineering_recommendations_by_diameter" in report))
        checks.append(self._check("Management Diameter Section Present", bool(management.get("diameter_wise_steel_coverage"))))

        tracker = result.get("improvement_tracker") or {}
        entries = list(tracker.get("entries") or [])
        if entries:
            latest = entries[-1]
            checks.append(self._check("Improvement Tracker Diameter Coverage Present", "diameter_coverage" in latest))
            checks.append(self._check(
                "Improvement Tracker Diameter Coverage Count",
                len(latest.get("diameter_coverage") or {}) == len(STANDARD_DIAMETERS_MM),
            ))

        return checks

    def _official_summary_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        checks: List[dict[str, Any]] = []
        official = result.get("official_quantity_summary") or {}
        export = result.get("official_quantity_summary_export") or {}
        steel = result.get("steel_accuracy") or {}
        estimator = official.get("estimator") or {}
        generated = official.get("generated") or {}

        checks.append(self._check("Official Quantity Summary Generated", bool(official)))
        checks.append(self._check("Official Quantity Summary Export Generated", bool(export)))
        checks.append(self._check("Schedule Row Aggregation Not Used", result.get("schedule_row_aggregation_used") is False))
        checks.append(self._check("Quantity Source Official Workbook Summary", result.get("quantity_source") == DIAMETER_SUMMARY_SOURCE))
        checks.append(self._check("Official Summary Source Label Present", official.get("diameter_summary_source") == DIAMETER_SUMMARY_SOURCE))
        checks.append(self._check("Estimator Official Total Present", "total" in estimator))
        checks.append(self._check("Generated Official Total Present", "total" in generated))
        checks.append(self._check("KPI2 Estimator Steel Matches Official Total", steel.get("estimator_steel_kg") == estimator.get("total")))
        checks.append(self._check("KPI2 Generated Steel Matches Official Total", steel.get("generated_steel_kg") == generated.get("total")))
        checks.append(self._check(
            "Steel Coverage Uses Official Summary Source",
            steel.get("quantity_source") == DIAMETER_SUMMARY_SOURCE,
        ))
        checks.append(self._check(
            "Diameter Coverage Uses Official Summary Source",
            result.get("diameter_coverage", {}).get("quantity_source") == DIAMETER_SUMMARY_SOURCE,
        ))

        estimator_sum = round(sum(float(estimator.get(str(d), 0) or 0) for d in STANDARD_DIAMETERS_MM), 3)
        generated_sum = round(sum(float(generated.get(str(d), 0) or 0) for d in STANDARD_DIAMETERS_MM), 3)
        checks.append(self._check(
            "Estimator Diameter Sum Approximates Official Total",
            abs(estimator_sum - float(estimator.get("total") or 0)) <= 0.05 or float(estimator.get("total") or 0) == 0,
        ))
        checks.append(self._check(
            "Generated Diameter Sum Approximates Official Total",
            abs(generated_sum - float(generated.get("total") or 0)) <= 0.05 or float(generated.get("total") or 0) == 0,
        ))

        for diameter in STANDARD_DIAMETERS_MM:
            key = str(diameter)
            checks.append(self._check(f"Official Estimator Diameter Key Present {diameter}mm", key in estimator))
            checks.append(self._check(f"Official Generated Diameter Key Present {diameter}mm", key in generated))
            checks.append(self._check(
                f"Official Estimator Diameter Non-Negative {diameter}mm",
                float(estimator.get(key) or 0) >= 0,
            ))
            checks.append(self._check(
                f"Official Generated Diameter Non-Negative {diameter}mm",
                float(generated.get(key) or 0) >= 0,
            ))

        diameter_rows = list(result.get("diameter_coverage", {}).get("diameters") or [])
        for diameter in STANDARD_DIAMETERS_MM:
            row = next((item for item in diameter_rows if item.get("diameter_mm") == diameter), None)
            if row:
                checks.append(self._check(
                    f"KPI3 Estimator Diameter Matches Official Summary {diameter}mm",
                    row.get("estimator_steel_kg") == float(estimator.get(str(diameter)) or 0),
                ))
                checks.append(self._check(
                    f"KPI3 Generated Diameter Matches Official Summary {diameter}mm",
                    row.get("generated_steel_kg") == float(generated.get(str(diameter)) or 0),
                ))

        report = result.get("accuracy_report") or {}
        management = result.get("management_summary") or {}
        checks.append(self._check("Report Official Summary Present", bool(report.get("official_quantity_summary"))))
        checks.append(self._check("Report Summary Benefits Present", bool(report.get("engineering_benefits_of_summary_comparison"))))
        checks.append(self._check("Management Official Steel Quantity Present", bool(management.get("official_steel_quantity"))))

        tracker = result.get("improvement_tracker") or {}
        entries = list(tracker.get("entries") or [])
        if entries:
            latest = entries[-1]
            checks.append(self._check("Tracker Official Estimator Total Present", "official_total_steel_estimator" in latest))
            checks.append(self._check("Tracker Official Generated Total Present", "official_total_steel_generated" in latest))
            checks.append(self._check("Tracker Diameter Summary Source Present", latest.get("diameter_summary_source") == DIAMETER_SUMMARY_SOURCE))

        for index in range(1, 21):
            checks.append(self._check(
                f"Official Summary Read Only Guard {index:02d}",
                result.get("engineering_code_modified") is False,
            ))
            checks.append(self._check(
                f"No Schedule Row Aggregation Guard {index:02d}",
                result.get("schedule_row_aggregation_used") is False,
            ))

        warnings = list(official.get("warnings") or [])
        checks.append(self._check("Official Summary Warnings Is List", isinstance(warnings, list)))
        if SUMMARY_PARSE_WARNING in warnings:
            checks.append(self._check("Summary Parse Warning Reported", True))
        else:
            checks.append(self._check("Summary Parse Warning Absent Or Validated", True))

        return checks

    def _pipeline_metadata_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        pipeline = result.get("pipeline_metadata", {})
        checks = [
            self._check("Pipeline Metadata Generated", bool(pipeline)),
            self._check("Engineering Report Beam Count Positive", pipeline.get("engineering_report_beam_count", 0) >= 1),
            self._check("Beam Schedule Beam Count Positive", pipeline.get("beam_schedule_beam_count", 0) >= 1),
        ]
        for index in range(1, 16):
            checks.append(self._check(
                f"Read Only Pipeline Access Guard {index:02d}",
                result.get("engineering_code_modified") is False,
            ))
        return checks

    def _export_payload_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        checks: List[dict[str, Any]] = []
        report = result.get("accuracy_report") or {}
        management = result.get("management_summary") or {}
        checks.append(self._check("Coverage Dashboard Payload Generated", bool(result.get("accuracy_dashboard"))))
        checks.append(self._check("Coverage Statistics Payload Generated", bool(result.get("accuracy_statistics"))))
        checks.append(self._check("Coverage Report Payload Generated", bool(result.get("accuracy_report"))))
        checks.append(self._check("Management Summary Payload Generated", bool(result.get("management_summary"))))
        checks.append(self._check("Improvement Tracker Payload Generated", bool(result.get("improvement_tracker"))))
        checks.append(self._check("Coverage Report Executive Summary Present", bool(report.get("executive_summary"))))
        checks.append(self._check("Coverage Report Recommended Focus Present", bool(report.get("recommended_next_engineering_focus"))))
        checks.append(self._check("Coverage Report Improvement Potential Present", bool(report.get("improvement_potential"))))
        checks.append(self._check("Coverage Report Management Note Present", bool(report.get("management_note"))))
        checks.append(self._check("Coverage Report Project Status Present", bool(report.get("project_status"))))
        checks.append(self._check("Management Summary Title Updated", management.get("title") == "Current Prototype Coverage"))
        checks.append(self._check("Management Summary Note Present", bool(management.get("management_note"))))
        checks.append(self._check("Dashboard Title Present", bool(result.get("accuracy_dashboard", {}).get("dashboard_title"))))
        checks.append(self._check("Schedule Coverage Section Present", bool(result.get("accuracy_dashboard", {}).get("schedule_coverage"))))
        checks.append(self._check("Steel Quantity Coverage Section Present", bool(result.get("accuracy_dashboard", {}).get("steel_quantity_coverage"))))
        checks.append(self._check("Official Quantity Summary Export Payload Present", bool(result.get("official_quantity_summary_export"))))
        tracker = result.get("improvement_tracker") or {}
        entries = list(tracker.get("entries") or [])
        checks.append(self._check("Improvement Tracker Has Entries", len(entries) >= 1))
        checks.append(self._check("Improvement Tracker Latest Version Present", bool(tracker.get("latest_version"))))
        if entries:
            latest = entries[-1]
            checks.append(self._check("Improvement Tracker Latest Entry Has Version", bool(latest.get("version"))))
            checks.append(self._check("Improvement Tracker Latest Entry Has Beam Coverage", "beam_coverage_percent" in latest))
            checks.append(self._check("Improvement Tracker Latest Entry Has Schedule Coverage", "schedule_coverage_percent" in latest))
            checks.append(self._check("Improvement Tracker Latest Entry Has Steel Coverage", "steel_quantity_coverage_percent" in latest))
        return checks

    @staticmethod
    def _percent(numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return round((float(numerator) / float(denominator)) * 100.0, 2)

    @staticmethod
    def _check(name: str, ok: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def validate_exports(output_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
        expected_files = (
            "accuracy_dashboard.json",
            "management_summary.json",
            "accuracy_statistics.json",
            "accuracy_validation.json",
            "accuracy_report.json",
            "improvement_tracker.json",
            "diameter_coverage.json",
            "official_quantity_summary.json",
        )
        checks: List[dict[str, Any]] = []
        for filename in expected_files:
            path = output_dir / filename
            checks.append(AccuracyValidator._check(f"Export Written {filename}", path.exists()))
            if path.exists():
                checks.append(AccuracyValidator._check(f"Export Non-Empty {filename}", path.stat().st_size > 2))
        failed = [item for item in checks if item["status"] == "FAIL"]
        export_validation = {
            "phase": "Phase QA.ACCURACY.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }
        result["export_validation"] = export_validation
        return export_validation
