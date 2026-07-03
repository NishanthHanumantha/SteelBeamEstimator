"""Phase E.3 — General Notes Intelligence Engine pipeline."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.config.output_paths import OutputPaths
from src.estimation.estimator_rule_loader import EstimatorRuleLoader
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_rule_extractor import EngineeringRuleExtractor
from src.general_notes.engineering_rule_validator import EngineeringRuleValidator
from src.general_notes.general_notes_debug_exporter import GeneralNotesDebugExporter
from src.general_notes.general_notes_parser import (
    GeneralNotesParser,
    load_general_notes_config,
    TextAnnotation,
)
from src.general_notes.engineering_value import engineering_value_numeric
from src.general_notes.project_knowledge_builder import (
    metadata_value,
    ProjectKnowledgeBuilder,
)
from src.general_notes.provenance_enricher import ProvenanceEnricher
from src.general_notes.traceability_builder import TraceabilityBuilder

DEFAULT_CONFIG = Path("config/general_notes.yaml")
DEFAULT_ESTIMATOR_CONFIG = Path("config/estimator_rules.yaml")
DEFAULT_INPUT = Path("data/general_notes")


class GeneralNotesPipeline:
    """Parse General Notes once per project and cache engineering rules."""

    def __init__(
        self,
        output_paths: OutputPaths,
        input_path: Optional[Path | str] = None,
        config_path: Path | str = DEFAULT_CONFIG,
        estimator_config_path: Path | str = DEFAULT_ESTIMATOR_CONFIG,
    ) -> None:
        self._outputs = output_paths
        self._input_path = Path(input_path) if input_path else DEFAULT_INPUT
        self._config_path = Path(config_path)
        self._estimator_config_path = Path(estimator_config_path)

    def run(self) -> Dict[str, Any]:
        config = load_general_notes_config(self._config_path)
        parser = GeneralNotesParser(config)
        document = parser.parse(self._input_path if self._input_path.exists() else None)
        project_info = parser.extract_project_information(document)

        estimator_loader = EstimatorRuleLoader.get_instance(self._estimator_config_path)
        estimator_rules = estimator_loader.load(self._estimator_config_path)
        estimator_model = estimator_loader.to_knowledge_model()
        estimator_defaults = estimator_loader.get_estimator_defaults()

        extractor = EngineeringRuleExtractor(config)
        extracted = extractor.extract(document)

        knowledge_builder = ProjectKnowledgeBuilder()
        metadata = knowledge_builder.build_metadata()
        knowledge = knowledge_builder.build_knowledge(
            project_info,
            extracted,
            extracted.get("ld_selection", {}),
            metadata,
            estimator_model,
            estimator_defaults,
        )
        knowledge = ProvenanceEnricher().enrich(knowledge)

        traceability_builder = TraceabilityBuilder()
        decision_trail = traceability_builder.build_decision_trail(knowledge)
        value_registry = traceability_builder.build_value_registry(knowledge)
        traceability_report = traceability_builder.build_traceability_report(knowledge)
        knowledge["engineering_decision_trail"] = decision_trail
        knowledge["engineering_value_registry"] = value_registry
        knowledge["engineering_traceability_report"] = traceability_report

        engineering_report = knowledge_builder.build_engineering_report(
            knowledge,
            traceability=traceability_report,
        )
        project_metadata = knowledge_builder.build_project_metadata_export(knowledge)
        split = extractor.split_outputs(knowledge)

        self._outputs.phase_e_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self._outputs.general_notes_engineering_rules, knowledge)
        self._write_json(self._outputs.development_length_table, split["development_length_table"])
        self._write_json(self._outputs.cover_table, split["cover_table"])
        self._write_json(self._outputs.material_specifications, split["material_specifications"])
        self._write_json(self._outputs.engineering_constants, split["engineering_constants"])
        self._write_json(self._outputs.project_defaults, split["project_defaults"])
        self._write_json(self._outputs.project_engineering_report, engineering_report)
        self._write_json(self._outputs.estimator_rules, estimator_model)
        self._write_json(self._outputs.project_metadata, project_metadata)
        self._write_json(self._outputs.engineering_value_registry, value_registry)
        self._write_json(
            self._outputs.engineering_traceability_report, traceability_report
        )

        cache: Optional[EngineeringRuleCache] = None
        if config.get("cache_rules", True):
            EngineeringRuleCache.reset()
            EstimatorRuleLoader.reset()
            cache = EngineeringRuleCache.get_instance(
                self._outputs.general_notes_engineering_rules,
                estimator_config_path=self._estimator_config_path,
            )

        validation = EngineeringRuleValidator().validate(knowledge, cache=cache)
        summary = self._build_summary(document, knowledge, validation)
        self._write_json(self._outputs.phase_e_summary, summary)
        self._write_json(self._outputs.phase_e_validation, validation)

        if config.get("debug", True):
            rule_highlights = self._collect_rule_highlights(document.texts)
            normalized_cover = [
                {
                    "normalized_member_type": row.get("normalized_member_type"),
                    "original_member_type": row.get("original_member_type"),
                    "y_position": row.get("y_position"),
                }
                for row in knowledge.get("cover_tables", [])
            ]
            GeneralNotesDebugExporter().export(
                document.texts,
                extracted.get("_ld_grids", []),
                extracted.get("_cover_rows", []),
                rule_highlights,
                self._outputs.phase_e_debug_dxf,
                active_ld_grid=extracted.get("_active_ld_grid"),
                project_defaults=knowledge.get("project_defaults"),
                normalized_cover=normalized_cover,
            )

        logger.info("Phase E.3 complete — validation {}", validation["status"])
        return {
            "model": knowledge,
            "validation": validation,
            "summary": summary,
            "engineering_report": engineering_report,
        }

    def _collect_rule_highlights(self, texts: List[TextAnnotation]) -> List[TextAnnotation]:
        keywords = (
            "SPACER",
            "BEND",
            "LAP",
            "SPLICE",
            "COUPLER",
            "LD FOR",
            "CLEAR COVER",
            "TABLE 2",
            "GRADE OF STEEL",
        )
        highlights: List[TextAnnotation] = []
        for ann in texts:
            upper = ann.text.upper()
            if any(keyword in upper for keyword in keywords):
                highlights.append(ann)
        return highlights[:80]

    def _build_summary(
        self,
        document: Any,
        model: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        ld_tables = model.get("development_tables") or model.get(
            "development_length_tables", {}
        )
        ld_cell_count = sum(
            len(diameter_map)
            for grade_table in ld_tables.values()
            if isinstance(grade_table, dict)
            for diameter_map in grade_table.values()
            if isinstance(diameter_map, dict)
        )
        defaults = model.get("project_defaults", {})
        project_info = model.get("project_information", {})
        structural = model.get("structural_detailing_rules", {})
        return {
            "phase": model.get("metadata", {}).get("phase"),
            "knowledge_version": model.get("metadata", {}).get("knowledge_version"),
            "source_file": str(document.source_path),
            "source_format": document.source_format,
            "project_name": metadata_value(project_info.get("project_name")),
            "project_name_source": project_info.get("project_name", {}).get("source"),
            "sheet_count": len(document.sheets),
            "sheet_ids": [s.sheet_id for s in document.sheets],
            "layout_names": document.layouts,
            "text_entity_count": len(document.texts),
            "steel_grade_count": len(model.get("materials", {}).get("steel_grades", [])),
            "concrete_grade_count": len(
                model.get("materials", {}).get("concrete_grades", [])
            ),
            "development_length_steel_grades": list(ld_tables.keys()),
            "development_length_entry_count": ld_cell_count,
            "active_development_table": model.get("matched_development_table_key"),
            "active_steel_grade": engineering_value_numeric(defaults.get("default_steel_grade")),
            "default_concrete_grade": engineering_value_numeric(
                defaults.get("default_concrete_grade")
            ),
            "structural_spacer_diameter_mm": defaults.get("structural_spacer_diameter_mm"),
            "estimator_spacer_diameter_mm": defaults.get("default_spacer_diameter_mm"),
            "estimator_spacer_spacing_mm": defaults.get("default_spacer_spacing_mm"),
            "cover_row_count": len(model.get("cover_tables", [])),
            "bend_rule_count": len(structural.get("bend_rules", model.get("bend_rules", []))),
            "anchorage_rule_count": len(
                structural.get("anchorage_rules", model.get("anchorage_rules", []))
            ),
            "fabrication_rule_count": len(
                structural.get("fabrication_rules", model.get("fabrication_rules", []))
            ),
            "validation_status": validation["status"],
        }

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
