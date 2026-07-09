"""Excel export engine — Phase I.17."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.excel_export.excel_export_builder import ExcelExportBuilder, TemplateMapper
from src.excel_export.excel_export_registry import ExcelExportRegistry
from src.excel_export.excel_export_types import OUTPUT_WORKBOOK_FILENAME, default_template_path
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class ExcelExportEngine:
    """Populate presentation workbook from EngineeringReport registry only."""

    def __init__(
        self,
        rules_path: Path | None = None,
        dependency_graph: CalculationDependencyGraph | None = None,
        template_path: Path | None = None,
        output_dir: Path | None = None,
    ) -> None:
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self._cache = EngineeringRuleCache.get_instance(path)
        self._dependency_graph = dependency_graph or CalculationDependencyGraph.from_spec()
        self._template_path = template_path
        self._output_dir = output_dir

    def determine(
        self,
        report_records: List[dict[str, Any]],
        report_registry: dict[str, Any] | None = None,
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
        output_dir: Path | None = None,
        template_path: Path | None = None,
        generation_timestamp: str | None = None,
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        _ = (report_registry, self._cache, self._dependency_graph)
        timestamp = generation_timestamp or datetime.now(timezone.utc).isoformat()
        resolved_output_dir = Path(output_dir or self._output_dir or Path("data/output/phase_i/i_17_excel_export"))
        resolved_template = Path(template_path or self._template_path or default_template_path())
        output_path = resolved_output_dir / OUTPUT_WORKBOOK_FILENAME

        export_record = ExcelExportBuilder.build_export(
            report_records,
            output_path,
            template_path=resolved_template,
            generation_timestamp=timestamp,
        )

        registry = ExcelExportRegistry()
        registry.register(export_record)

        primary = drawing_models[0] if drawing_models else {}
        project_registry = ExcelExportRegistry.build_project_registry(
            [export_record],
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        project_registry["worksheet_name"] = TemplateMapper.WORKSHEET_NAME
        return [export_record], {
            "excel_export_results": [export_record],
            "excel_export_registry": project_registry,
        }

    @staticmethod
    def build_project_exports(
        export_records: List[dict[str, Any]],
        export_registry: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "excel_export_results": export_records,
            "excel_export_registry": export_registry,
        }
