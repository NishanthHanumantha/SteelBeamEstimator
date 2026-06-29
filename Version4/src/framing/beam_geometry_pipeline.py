"""Phase F.1–F.7 — Framing plan geometry through project workspace."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from src.config.output_paths import OutputPaths
from src.framing.beam_centerline_extractor import BeamCenterlineExtractor
from src.framing.beam_dimension_resolver import BeamDimensionResolver
from src.framing.beam_dimension_validator import BeamDimensionValidator
from src.framing.beam_geometry_builder import BeamGeometryBuilder
from src.framing.beam_geometry_debug_exporter import BeamGeometryDebugExporter
from src.framing.beam_geometry_validator import BeamGeometryValidator
from src.framing.beam_length_builder import BeamLengthBuilder
from src.framing.beam_section_builder import BeamSectionBuilder
from src.framing.beam_section_validator import BeamSectionValidator
from src.framing.beam_support_detector import BeamSupportDetector
from src.framing.beam_support_resolver import BeamSupportResolver
from src.framing.engineering_context_builder import EngineeringContextBuilder
from src.framing.engineering_context_validator import EngineeringContextValidator
from src.framing.engineering_graph_validator import EngineeringGraphValidator
from src.framing.engineering_length_validator import EngineeringLengthValidator
from src.framing.framing_config import DEFAULT_CONFIG, load_framing_config
from src.framing.knowledge_graph_builder import KnowledgeGraphBuilder
from src.project.workspace_manager import WorkspaceManager
from src.project.workspace_validator import WorkspaceValidator

DEFAULT_INPUT = Path("data/framing")


class BeamGeometryPipeline:
    """Extract beam geometry through engineering length model and knowledge graph."""

    def __init__(
        self,
        output_paths: OutputPaths,
        input_path: Optional[Path | str] = None,
        config_path: Path | str = DEFAULT_CONFIG,
    ) -> None:
        self._outputs = output_paths
        self._input_path = Path(input_path) if input_path else DEFAULT_INPUT
        self._config_path = Path(config_path)

    def run(self) -> Dict[str, Any]:
        config = load_framing_config(self._config_path)
        centerline_extractor = BeamCenterlineExtractor(config)
        builder = BeamGeometryBuilder(config)

        if self._input_path.is_file():
            records = centerline_extractor.extract_from_dxf(self._input_path)
            source_files = [self._input_path]
            segment_root = self._input_path.parent
        else:
            records = centerline_extractor.extract_from_directory(self._input_path)
            source_files = sorted(self._input_path.glob("*.dxf"))
            segment_root = self._input_path

        all_segments = centerline_extractor.extract_all_segments_from_directory(segment_root)
        if not all_segments:
            all_segments = [
                record.segment for record in records if record.segment is not None
            ]

        structural_context: dict[str, Any] = {"columns": [], "walls": [], "entities": []}
        if source_files:
            structural_context = BeamSupportDetector(config).load_structural_context(
                source_files[0]
            )

        model = builder.build(records, all_segments, structural_context)
        f1_supports = list(model.get("supports", []))
        f1_validation = BeamGeometryValidator().validate(model)
        split = builder.split_outputs(model)

        resolver = BeamDimensionResolver(config)
        model = resolver.resolve_model(model, records, all_segments)
        dimension_validation = BeamDimensionValidator(config).validate(model)
        resolved_export = resolver.build_resolved_export(model)

        support_resolver = BeamSupportResolver(config)
        model = support_resolver.resolve_model(
            model, records, structural_context, self._f1_support_records(f1_supports)
        )
        support_validation = support_resolver.validate_supports(model)

        section_builder = BeamSectionBuilder(config)
        model = section_builder.build_model(model)
        section_validation = BeamSectionValidator(config).validate(model)

        length_builder = BeamLengthBuilder(config)
        model = length_builder.build_model(model, structural_context)
        length_validation = EngineeringLengthValidator().validate(model)

        graph_builder = KnowledgeGraphBuilder(config)
        model = graph_builder.build_model(model)
        graph_validation = EngineeringGraphValidator().validate(model)

        context_builder = EngineeringContextBuilder(config, self._outputs.root)
        model = context_builder.build_model(model)
        model["source_files"] = [str(p) for p in source_files]
        context_validation = EngineeringContextValidator().validate(model)

        workspace_manager = WorkspaceManager()
        model = workspace_manager.load(model, self._outputs.root, config)
        workspace_validation = WorkspaceValidator().validate(model)

        summary = self._build_summary(
            model,
            f1_validation,
            dimension_validation,
            support_validation,
            section_validation,
            length_validation,
            graph_validation,
            context_validation,
            workspace_validation,
            resolver.stats,
            support_resolver.stats,
            section_builder.stats,
            length_builder.stats,
            graph_builder.stats,
            context_builder.stats,
            source_files,
        )

        self._outputs.ensure_phase_f_subdirs()
        self._write_json(self._outputs.beam_geometry_model, model)
        self._write_json(self._outputs.beam_centerlines, split["beam_centerlines"])
        self._write_json(self._outputs.beam_dimensions, self._beam_dimensions_export(model))
        self._write_json(self._outputs.beam_connectivity, model.get("connectivity_graph", {}))
        self._write_json(self._outputs.beam_supports, self._beam_supports_export(model))
        self._write_json(self._outputs.beam_dimensions_resolved, resolved_export)
        self._write_json(self._outputs.beam_sections, self._beam_sections_export(model))
        self._write_json(self._outputs.support_graph, model.get("support_graph", {}))
        self._write_json(self._outputs.structural_nodes, model.get("structural_nodes", []))
        self._write_json(self._outputs.phase_f_summary, summary)
        self._write_json(self._outputs.phase_f_validation, f1_validation)
        self._write_json(self._outputs.phase_f_dimension_validation, dimension_validation)
        self._write_json(self._outputs.phase_f_support_validation, support_validation)
        self._write_json(self._outputs.phase_f_section_validation, section_validation)
        self._write_json(self._outputs.beam_length_model, self._length_model_export(model))
        self._write_json(self._outputs.clear_spans, self._clear_spans_export(model))
        self._write_json(self._outputs.effective_spans, self._effective_spans_export(model))
        self._write_json(self._outputs.bearing_lengths, self._bearing_lengths_export(model))
        self._write_json(self._outputs.phase_f_length_validation, length_validation)
        self._write_json(self._outputs.framing_knowledge_graph, model.get("framing_knowledge_graph", {}))
        self._write_json(
            self._outputs.engineering_coordinate_system,
            {"phase": "Phase F.5", "systems": model.get("engineering_coordinate_systems", [])},
        )
        self._write_json(
            self._outputs.beam_stationing,
            {"phase": "Phase F.5", "beams": model.get("beam_stationing_export", [])},
        )
        self._write_json(self._outputs.beam_relationships, model.get("beam_relationships", {}))
        self._write_json(
            self._outputs.engineering_status_registry,
            {"phase": "Phase F.6", "entries": model.get("engineering_status_registry", [])},
        )
        self._write_json(self._outputs.phase_f_graph_validation, graph_validation)
        self._write_json(
            self._outputs.beam_engineering_context,
            {
                "phase": model.get("phase", "Phase F.7"),
                "context_count": len(model.get("beam_engineering_contexts", [])),
                "contexts": model.get("beam_engineering_contexts", []),
            },
        )
        self._write_json(
            self._outputs.engineering_context_registry,
            model.get("engineering_context_registry", {}),
        )
        self._write_json(
            self._outputs.engineering_dependency_graph,
            model.get("engineering_dependency_graph", {}),
        )
        self._write_json(
            self._outputs.engineering_dependency_registry,
            model.get("engineering_dependency_registry", {}),
        )
        self._write_json(
            self._outputs.project_engineering_graph,
            model.get("project_engineering_graph", {}),
        )
        self._write_json(self._outputs.phase_f_context_validation, context_validation)
        self._write_json(self._outputs.project_workspace, model.get("project_workspace", {}))
        self._write_json(self._outputs.project_registry, model.get("project_registry", {}))
        self._write_json(self._outputs.floor_registry, model.get("floor_registry", {}))
        self._write_json(
            self._outputs.engineering_services_registry,
            model.get("engineering_services_registry", {}),
        )
        self._write_json(self._outputs.workspace_manager, model.get("workspace_manager", {}))
        self._write_json(self._outputs.phase_f_workspace_validation, workspace_validation)

        if config.get("generate_debug_dxf", True):
            dr = config.get("dimension_resolution", {})
            sr = config.get("support_resolution", {})
            bs = config.get("beam_section", {})
            el = config.get("engineering_length", {})
            kg = config.get("knowledge_graph", {})
            ec = config.get("engineering_context", {})
            ws = config.get("workspace", {})
            BeamGeometryDebugExporter().export(
                model,
                self._outputs.phase_f_debug_dxf,
                show_dimensions=bool(dr.get("generate_debug_dimensions", True)),
                show_supports=bool(sr.get("generate_debug_supports", True)),
                show_section=bool(bs.get("generate_debug_section", True)),
                show_structural_nodes=True,
                show_engineering_lengths=bool(el.get("generate_debug_lengths", True)),
                show_graph=bool(kg.get("generate_debug_graph", True)),
                show_engineering_context=bool(ec.get("generate_debug_context", True)),
                show_dependencies=bool(ec.get("generate_debug_dependencies", True)),
                show_project_graph=bool(ec.get("generate_debug_project_graph", True)),
                show_workspace=bool(ws.get("generate_debug_workspace", True)),
            )

        logger.info(
            "Phase F complete — F.1 {}, F.2 {}, F.3 support {}, F.3 section {}, F.4 {}, F.5 {}, F.6 {}, F.7 {}",
            f1_validation["status"],
            dimension_validation["status"],
            support_validation["status"],
            section_validation["status"],
            length_validation["status"],
            graph_validation["status"],
            context_validation["status"],
            workspace_validation["status"],
        )
        return {
            "model": model,
            "f1_validation": f1_validation,
            "dimension_validation": dimension_validation,
            "support_validation": support_validation,
            "section_validation": section_validation,
            "length_validation": length_validation,
            "graph_validation": graph_validation,
            "context_validation": context_validation,
            "workspace_validation": workspace_validation,
            "summary": summary,
        }

    @staticmethod
    def _f1_support_records(f1_supports: list) -> list:
        from src.framing.beam_support_detector import BeamSupportRecord
        from src.framing.beam_geometry import Point2D

        records = []
        for item in f1_supports:
            if isinstance(item, BeamSupportRecord):
                records.append(item)
                continue
            point = item.get("point", {})
            records.append(
                BeamSupportRecord(
                    beam_id=item["beam_id"],
                    end=item["end"],
                    point=Point2D(point.get("x", 0.0), point.get("y", 0.0)),
                    support_type=item.get("support_type", "unknown"),
                    support_id=item.get("support_id"),
                    confidence=float(item.get("confidence", 0.0)),
                    distance_mm=float(item.get("distance_mm", 0.0)),
                )
            )
        return records

    def _beam_dimensions_export(self, model: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "beam_id": beam["beam_id"],
                "beam_mark": beam["beam_mark"],
                "dimensions": beam.get("dimensions", {}),
            }
            for beam in model.get("beams", [])
        ]

    def _beam_supports_export(self, model: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "beam_id": beam["beam_id"],
                "beam_mark": beam["beam_mark"],
                "supports": beam.get("supports", {}),
            }
            for beam in model.get("beams", [])
        ]

    def _beam_sections_export(self, model: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase F.3",
            "beam_count": len(model.get("beams", [])),
            "summary": model.get("beam_section_summary", {}),
            "beams": [
                {
                    "beam_id": beam["beam_id"],
                    "beam_mark": beam["beam_mark"],
                    "section": beam.get("beam_section", {}),
                }
                for beam in model.get("beams", [])
            ],
        }

    def _length_model_export(self, model: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase F.4",
            "beam_count": len(model.get("beams", [])),
            "summary": model.get("engineering_length_summary", {}),
            "beams": model.get("length_model_export", []),
        }

    def _clear_spans_export(self, model: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase F.4",
            "beams": [
                {
                    "beam_id": b["beam_id"],
                    "beam_mark": b["beam_mark"],
                    "clear_span": b.get("length_model", {}).get("clear_span", {}),
                    "governing_span": b.get("length_model", {}).get("governing_span", {}),
                }
                for b in model.get("beams", [])
            ],
        }

    def _effective_spans_export(self, model: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase F.4",
            "beams": [
                {
                    "beam_id": b["beam_id"],
                    "beam_mark": b["beam_mark"],
                    "effective_span": b.get("length_model", {}).get("effective_span", {}),
                    "design_span": b.get("length_model", {}).get("design_span", {}),
                }
                for b in model.get("beams", [])
            ],
        }

    def _bearing_lengths_export(self, model: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase F.4",
            "beams": [
                {
                    "beam_id": b["beam_id"],
                    "beam_mark": b["beam_mark"],
                    "bearing_length_left": b.get("length_model", {}).get("bearing_length_left", {}),
                    "bearing_length_right": b.get("length_model", {}).get("bearing_length_right", {}),
                    "support_face_length": b.get("length_model", {}).get("support_face_length", {}),
                }
                for b in model.get("beams", [])
            ],
        }

    def _build_summary(
        self,
        model: dict[str, Any],
        f1_validation: dict[str, Any],
        dimension_validation: dict[str, Any],
        support_validation: dict[str, Any],
        section_validation: dict[str, Any],
        length_validation: dict[str, Any],
        graph_validation: dict[str, Any],
        context_validation: dict[str, Any],
        workspace_validation: dict[str, Any],
        resolver_stats: dict[str, int],
        support_stats: dict[str, int],
        section_stats: dict[str, int],
        length_stats: dict[str, int],
        graph_stats: dict[str, int],
        context_stats: dict[str, int],
        source_files: list[Path],
    ) -> dict[str, Any]:
        beams = model.get("beams", [])
        orientations: dict[str, int] = {}
        for beam in beams:
            orientation = beam.get("geometry", {}).get("orientation", "unknown")
            orientations[orientation] = orientations.get(orientation, 0) + 1
        return {
            "phase": model.get("phase"),
            "model_version": model.get("model_version"),
            "source_files": [str(path) for path in source_files],
            "beam_count": len(beams),
            "beam_marks": [beam["beam_mark"] for beam in beams],
            "orientation_counts": orientations,
            "connectivity_edges": model.get("connectivity_graph", {}).get("edge_count", 0),
            "f1_validation_status": f1_validation["status"],
            "dimension_validation_status": dimension_validation["status"],
            "support_validation_status": support_validation["status"],
            "section_validation_status": section_validation["status"],
            "length_validation_status": length_validation["status"],
            "graph_validation_status": graph_validation["status"],
            "context_validation_status": context_validation["status"],
            "workspace_validation_status": workspace_validation["status"],
            "dimension_resolution": resolver_stats,
            "support_resolution": support_stats,
            "beam_section": section_stats,
            "engineering_length": length_stats,
            "knowledge_graph": graph_stats,
            "engineering_context": context_stats,
            "workspace": {
                "floor_count": model.get("floor_registry", {}).get("floor_count", 0),
                "services": model.get("engineering_services_registry", {}).get("service_count", 0),
            },
            "project_id": model.get("project_id"),
        }

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
