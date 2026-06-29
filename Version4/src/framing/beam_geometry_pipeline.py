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
from src.project.drawing_identity_builder import DrawingIdentityBuilder
from src.project.drawing_set_builder import DrawingSetBuilder
from src.project.drawing_set_lifecycle import DrawingSetLifecycleBuilder
from src.reinforcement.reinforcement_loader import ReinforcementLoader

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

        project_root = self._outputs.root.parent.parent
        reinforcement_cfg = dict(config.get("reinforcement_drawings", {}))
        reinforcement_paths = [
            (project_root / path_str).resolve()
            if not Path(path_str).is_absolute()
            else Path(path_str).resolve()
            for path_str in reinforcement_cfg.values()
        ]
        reinforcement_path_set = {path.resolve() for path in reinforcement_paths}
        framing_identity_paths = [
            Path(p).resolve()
            for p in source_files
            if Path(p).resolve() not in reinforcement_path_set
        ]
        if not framing_identity_paths and source_files:
            framing_identity_paths = [Path(source_files[0]).resolve()]

        identity_builder = DrawingIdentityBuilder(config, project_root)
        model = identity_builder.build_model(
            model,
            framing_identity_paths,
            reinforcement_paths,
            self._outputs.root,
        )

        workspace_manager = WorkspaceManager()
        model = workspace_manager.load(model, self._outputs.root, config)
        workspace_validation = WorkspaceValidator().validate(model)

        model = identity_builder.finalize_validation(model)
        drawing_identity_validation = model.get("drawing_identity_validation", {})

        project_root = self._outputs.root.parent.parent
        reinforcement_loader = ReinforcementLoader(config, project_root)
        model = reinforcement_loader.load(model)
        reinforcement_validation = model.get("reinforcement_validation", {})

        model = DrawingSetBuilder(config).build_model(model)
        drawing_set_validation = model.get("drawing_set_validation", {})

        model = DrawingSetLifecycleBuilder(config).build_model(model, self._outputs.root)
        drawing_set_state_validation = model.get("drawing_set_state_validation", {})

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
            reinforcement_validation,
            drawing_identity_validation,
            drawing_set_validation,
            drawing_set_state_validation,
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
                "phase": model.get("phase", "Phase G.1.2"),
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

        self._outputs.ensure_phase_g_subdirs()
        phase_g_summary = self._build_phase_g_summary(model, reinforcement_validation)
        self._write_json(self._outputs.phase_g_summary, phase_g_summary)
        self._write_json(
            self._outputs.reinforcement_workspace_export,
            {
                "phase": "Phase G.1",
                "workspace_count": len(model.get("reinforcement_workspaces", [])),
                "workspaces": model.get("reinforcement_workspaces", []),
            },
        )
        self._write_json(
            self._outputs.reinforcement_document_export,
            {
                "phase": "Phase G.1",
                "documents": [
                    ws.get("document")
                    for ws in model.get("reinforcement_workspaces", [])
                ],
            },
        )
        self._write_json(self._outputs.reinforcement_registry, model.get("reinforcement_registry", {}))
        self._write_json(self._outputs.reinforcement_validation, reinforcement_validation)
        self._write_json(self._outputs.phase_g_workspace_manager, model.get("workspace_manager", {}))
        self._write_json(self._outputs.project_workspace, model.get("project_workspace", {}))
        self._write_json(self._outputs.floor_registry, model.get("floor_registry", {}))

        self._write_json(
            self._outputs.drawing_identity_export,
            {
                "phase": "Phase G.1.1",
                "identity_count": len(model.get("drawing_identities", [])),
                "identities": model.get("drawing_identities", []),
            },
        )
        self._write_json(self._outputs.drawing_registry_export, model.get("drawing_registry", {}))
        self._write_json(self._outputs.drawing_identity_validation, drawing_identity_validation)
        self._write_json(
            self._outputs.floor_detection_export,
            {
                "phase": "Phase G.1.1",
                "detections": model.get("floor_detection", []),
            },
        )
        self._write_json(self._outputs.phase_g_1_1_workspace_manager, model.get("workspace_manager", {}))
        self._write_json(self._outputs.phase_g_1_1_project_workspace, model.get("project_workspace", {}))
        self._write_json(self._outputs.phase_g_1_1_floor_registry, model.get("floor_registry", {}))
        self._write_json(
            self._outputs.phase_g_1_1_reinforcement_workspace,
            {
                "phase": "Phase G.1.1",
                "workspace_count": len(model.get("reinforcement_workspaces", [])),
                "workspaces": model.get("reinforcement_workspaces", []),
            },
        )

        self._write_json(
            self._outputs.drawing_set_export,
            {
                "phase": "Phase G.1.2",
                "drawing_set_count": len(model.get("drawing_sets", [])),
                "drawing_sets": model.get("drawing_sets", []),
            },
        )
        self._write_json(
            self._outputs.drawing_set_registry_export,
            model.get("drawing_set_registry", {}),
        )
        self._write_json(self._outputs.drawing_set_validation, drawing_set_validation)
        self._write_json(
            self._outputs.phase_g_1_2_beam_engineering_context,
            {
                "phase": "Phase G.1.2",
                "context_count": len(model.get("beam_engineering_contexts", [])),
                "contexts": model.get("beam_engineering_contexts", []),
            },
        )
        self._write_json(
            self._outputs.phase_g_1_2_project_workspace,
            model.get("project_workspace", {}),
        )
        self._write_json(
            self._outputs.phase_g_1_2_project_registry,
            model.get("project_registry", {}),
        )
        self._write_json(
            self._outputs.phase_g_1_2_project_engineering_graph,
            model.get("project_engineering_graph", {}),
        )
        self._write_json(
            self._outputs.phase_g_1_2_drawing_registry,
            model.get("drawing_registry", {}),
        )
        self._write_json(
            self._outputs.phase_g_1_2_workspace_manager,
            model.get("workspace_manager", {}),
        )

        self._write_json(
            self._outputs.beam_engineering_context,
            {
                "phase": model.get("phase", "Phase G.1.2"),
                "context_count": len(model.get("beam_engineering_contexts", [])),
                "contexts": model.get("beam_engineering_contexts", []),
            },
        )
        self._write_json(self._outputs.project_workspace, model.get("project_workspace", {}))
        self._write_json(self._outputs.project_registry, model.get("project_registry", {}))
        self._write_json(
            self._outputs.project_engineering_graph,
            model.get("project_engineering_graph", {}),
        )
        self._write_json(self._outputs.workspace_manager, model.get("workspace_manager", {}))

        self._write_json(
            self._outputs.drawing_set_state_export,
            {
                "phase": "Phase G.1.3",
                "drawing_set_count": len(model.get("drawing_sets", [])),
                "drawing_sets": model.get("drawing_sets", []),
            },
        )
        self._write_json(
            self._outputs.beam_index_export,
            {
                "phase": "Phase G.1.3",
                "indices": model.get("beam_indices", []),
            },
        )
        self._write_json(
            self._outputs.beam_lookup_registry_export,
            {
                "phase": "Phase G.1.3",
                "entries": model.get("beam_lookup_registry", []),
            },
        )
        self._write_json(
            self._outputs.drawing_set_version_export,
            {
                "phase": "Phase G.1.3",
                "versions": model.get("drawing_set_versions", []),
            },
        )
        self._write_json(
            self._outputs.drawing_set_state_validation,
            drawing_set_state_validation,
        )
        self._write_json(
            self._outputs.drawing_set_export,
            {
                "phase": "Phase G.1.3",
                "drawing_set_count": len(model.get("drawing_sets", [])),
                "drawing_sets": model.get("drawing_sets", []),
            },
        )
        self._write_json(
            self._outputs.drawing_set_registry_export,
            model.get("drawing_set_registry", {}),
        )
        self._write_json(
            self._outputs.beam_engineering_context,
            {
                "phase": model.get("phase", "Phase G.1.3"),
                "context_count": len(model.get("beam_engineering_contexts", [])),
                "contexts": model.get("beam_engineering_contexts", []),
            },
        )
        self._write_json(self._outputs.project_workspace, model.get("project_workspace", {}))
        self._write_json(self._outputs.project_registry, model.get("project_registry", {}))
        self._write_json(
            self._outputs.project_engineering_graph,
            model.get("project_engineering_graph", {}),
        )

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
            rl = config.get("reinforcement_loading", {})
            if bool(rl.get("generate_debug_reinforcement", True)):
                BeamGeometryDebugExporter().export_reinforcement(
                    model,
                    self._outputs.phase_g_debug_dxf,
                )
            di = config.get("drawing_identity", {})
            if bool(di.get("generate_debug_drawing_identity", True)):
                BeamGeometryDebugExporter().export_drawing_identity(
                    model,
                    self._outputs.phase_g_debug_dxf,
                )
            ds_cfg = config.get("drawing_set", {})
            if bool(ds_cfg.get("generate_debug_drawing_set", True)):
                BeamGeometryDebugExporter().export_drawing_set(
                    model,
                    self._outputs.phase_g_debug_dxf,
                )
            ls_cfg = config.get("drawing_set_lifecycle", {})
            if bool(ls_cfg.get("generate_debug_drawing_set_state", True)):
                BeamGeometryDebugExporter().export_drawing_set_state(
                    model,
                    self._outputs.phase_g_debug_dxf,
                )

        logger.info(
            "Phase F complete — F.1 {}, F.2 {}, F.3 support {}, F.3 section {}, F.4 {}, F.5 {}, F.6 {}, F.7 {}, G.1 {}, G.1.1 {}, G.1.2 {}, G.1.3 {}",
            f1_validation["status"],
            dimension_validation["status"],
            support_validation["status"],
            section_validation["status"],
            length_validation["status"],
            graph_validation["status"],
            context_validation["status"],
            workspace_validation["status"],
            reinforcement_validation.get("status", "SKIP"),
            drawing_identity_validation.get("status", "SKIP"),
            drawing_set_validation.get("status", "SKIP"),
            drawing_set_state_validation.get("status", "SKIP"),
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
            "reinforcement_validation": reinforcement_validation,
            "drawing_identity_validation": drawing_identity_validation,
            "drawing_set_validation": drawing_set_validation,
            "drawing_set_state_validation": drawing_set_state_validation,
            "summary": summary,
            "phase_g_summary": phase_g_summary,
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
        reinforcement_validation: dict[str, Any],
        drawing_identity_validation: dict[str, Any],
        drawing_set_validation: dict[str, Any],
        drawing_set_state_validation: dict[str, Any],
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
            "reinforcement_validation_status": reinforcement_validation.get("status", "SKIP"),
            "drawing_identity_validation_status": drawing_identity_validation.get("status", "SKIP"),
            "drawing_set_validation_status": drawing_set_validation.get("status", "SKIP"),
            "drawing_set_state_validation_status": drawing_set_state_validation.get("status", "SKIP"),
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

    def _build_phase_g_summary(
        self,
        model: dict[str, Any],
        reinforcement_validation: dict[str, Any],
    ) -> dict[str, Any]:
        reg = model.get("reinforcement_registry", {})
        drawing_reg = model.get("drawing_registry", {})
        set_reg = model.get("drawing_set_registry", {})
        return {
            "phase": "Phase G.1.3",
            "description": "Drawing Set Lifecycle, Beam Index & Versioning",
            "reinforcement_validation_status": reinforcement_validation.get("status", "SKIP"),
            "drawing_identity_validation_status": model.get(
                "drawing_identity_validation", {}
            ).get("status", "SKIP"),
            "drawing_set_validation_status": model.get(
                "drawing_set_validation", {}
            ).get("status", "SKIP"),
            "drawing_set_state_validation_status": model.get(
                "drawing_set_state_validation", {}
            ).get("status", "SKIP"),
            "workspace_count": len(model.get("reinforcement_workspaces", [])),
            "document_count": reg.get("document_count", 0),
            "drawing_count": drawing_reg.get("drawing_count", 0),
            "drawing_set_count": set_reg.get("drawing_set_count", 0),
            "beam_index_count": len(model.get("beam_indices", [])),
            "floors_loaded": model.get("reinforcement_loading_summary", {}).get("floors_loaded", 0),
            "floor_source": model.get("workspace_manager", {}).get("floor_source"),
            "project_id": model.get("project_workspace", {}).get("project_id"),
        }

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
