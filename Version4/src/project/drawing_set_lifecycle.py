"""Drawing Set lifecycle states and G.1.3 enrichment orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.project.beam_index_builder import BeamIndexBuilder
from src.project.drawing_set_state_validator import DrawingSetStateValidator
from src.project.drawing_set_version_builder import DrawingSetVersionBuilder
from src.project.drawing_set_state_machine import (
    BOQ_NOT_STARTED,
    ENGINEERING_NOT_STARTED,
    LOADING_READY,
    MATCHING_NOT_STARTED,
    PARSING_NOT_STARTED,
    QUANTITY_NOT_STARTED,
)


FUTURE_PLACEHOLDERS: dict[str, Any] = {
    "beam_matching_context": None,
    "reinforcement_contexts": [],
    "engineering_results": None,
}


@dataclass
class DrawingSetLifecycle:
    """Orchestration lifecycle for a drawing set (not EngineeringStatus)."""

    loading_state: str = LOADING_READY
    matching_state: str = MATCHING_NOT_STARTED
    parsing_state: str = PARSING_NOT_STARTED
    engineering_state: str = ENGINEERING_NOT_STARTED
    quantity_state: str = QUANTITY_NOT_STARTED
    boq_state: str = BOQ_NOT_STARTED

    def to_dict(self) -> dict[str, str]:
        return {
            "loading_state": self.loading_state,
            "matching_state": self.matching_state,
            "parsing_state": self.parsing_state,
            "engineering_state": self.engineering_state,
            "quantity_state": self.quantity_state,
            "boq_state": self.boq_state,
        }


def initial_lifecycle_for_set(drawing_set: dict[str, Any]) -> DrawingSetLifecycle:
    """Derive loading state from drawing set attachment status."""
    loading = LOADING_READY
    drawings = drawing_set.get("drawings", {})
    if not drawings.get("framing") or not drawings.get("reinforcement"):
        from src.project.drawing_set_state_machine import LOADING_NOT_LOADED
        loading = LOADING_NOT_LOADED
    return DrawingSetLifecycle(loading_state=loading)


class DrawingSetLifecycleBuilder:
    """Enrich drawing sets with lifecycle, version, beam index, and graph updates."""

    def __init__(self, config: dict[str, Any]) -> None:
        ls_cfg = config.get("drawing_set_lifecycle", {})
        self._enabled = bool(ls_cfg.get("enable", True))

    def build_model(
        self,
        model: dict[str, Any],
        output_root: Optional[Path] = None,
    ) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Drawing set lifecycle enrichment disabled in config")
            return model

        identities = model.get("drawing_identities", [])
        contexts = model.get("beam_engineering_contexts", [])
        version_builder = DrawingSetVersionBuilder()
        index_builder = BeamIndexBuilder()
        previous_version_path = None
        if output_root:
            previous_version_path = (
                Path(output_root) / "phase_g" / "g_1_3_drawing_set_state" / "drawing_set_version.json"
            )

        enriched_sets: List[dict[str, Any]] = []
        beam_indices: List[dict[str, Any]] = []
        lookup_registry: List[dict[str, Any]] = []
        versions_export: List[dict[str, Any]] = []

        for ds in model.get("drawing_sets", []):
            enriched = dict(ds)
            lifecycle = initial_lifecycle_for_set(enriched)
            lifecycle_dict = lifecycle.to_dict()

            version = version_builder.build(
                enriched,
                identities,
                previous_versions_path=previous_version_path,
            )
            floor_slug = str(enriched.get("metadata", {}).get("floor_slug", ""))
            version_dict = version.to_dict()
            version_dict["floor_slug"] = floor_slug
            versions_export.append(version_dict)

            beam_index = index_builder.build(enriched["drawing_set_id"], contexts)
            beam_indices.append(beam_index.to_dict())
            lookup_registry.extend([
                {**entry, "drawing_set_id": enriched["drawing_set_id"]}
                for entry in beam_index.lookup_registry()
            ])

            enriched.update(lifecycle_dict)
            enriched["drawing_set_version"] = version_dict
            enriched["beam_index"] = beam_index.to_dict()["index"]
            enriched["beam_index_meta"] = {
                "drawing_set_id": beam_index.drawing_set_id,
                "beam_count": beam_index.count(),
                "marks": beam_index.list_marks(),
            }
            enriched.update(FUTURE_PLACEHOLDERS)
            enriched_sets.append(enriched)

        model["drawing_sets"] = enriched_sets
        model["beam_indices"] = beam_indices
        model["beam_lookup_registry"] = lookup_registry
        model["drawing_set_versions"] = versions_export

        self._enrich_project_workspace(model, enriched_sets)
        self._update_project_graph(model, enriched_sets, beam_indices)
        self._update_drawing_set_registry(model, enriched_sets)

        validation = DrawingSetStateValidator().validate(model, enriched_sets)
        model["drawing_set_state_validation"] = validation
        model["phase_g"] = "Phase G.1.3"

        manager = model.get("workspace_manager", {})
        manager["phase"] = "Phase G.1.3"
        manager["drawing_set_lifecycle_enabled"] = True
        model["workspace_manager"] = manager
        model["phase"] = "Phase G.1.3"
        model["model_version"] = "1.9"

        logger.info(
            "Drawing set lifecycle — sets={}, beams_indexed={}",
            len(enriched_sets),
            sum(len(b.get("index", {})) for b in beam_indices),
        )
        return model

    def _enrich_project_workspace(
        self,
        model: dict[str, Any],
        drawing_sets: List[dict[str, Any]],
    ) -> None:
        project = model.get("project_workspace", {})
        if not project:
            return

        project["drawing_sets"] = [
            ds.get("drawing_set_id") for ds in drawing_sets
        ]
        project["drawing_set_details"] = [
            {
                "drawing_set_id": ds.get("drawing_set_id"),
                "drawing_set_version": ds.get("drawing_set_version"),
                "beam_index": ds.get("beam_index"),
                "beam_index_meta": ds.get("beam_index_meta"),
                "states": {
                    "loading_state": ds.get("loading_state"),
                    "matching_state": ds.get("matching_state"),
                    "parsing_state": ds.get("parsing_state"),
                    "engineering_state": ds.get("engineering_state"),
                    "quantity_state": ds.get("quantity_state"),
                    "boq_state": ds.get("boq_state"),
                },
                "status": ds.get("status"),
            }
            for ds in drawing_sets
        ]
        meta = dict(project.get("metadata") or {})
        meta["phase"] = "Phase G.1.3"
        project["metadata"] = meta
        model["project_workspace"] = project

        registry = dict(model.get("project_registry", {}))
        registry["phase"] = "Phase G.1.3"
        registry["drawing_set_details"] = project.get("drawing_set_details", [])
        model["project_registry"] = registry

    def _update_drawing_set_registry(
        self,
        model: dict[str, Any],
        drawing_sets: List[dict[str, Any]],
    ) -> None:
        registry = dict(model.get("drawing_set_registry", {}))
        registry["phase"] = "Phase G.1.3"
        for entry in registry.get("drawing_sets", []):
            ds_id = entry.get("drawing_set_id")
            match = next((ds for ds in drawing_sets if ds.get("drawing_set_id") == ds_id), None)
            if match:
                entry["version"] = match.get("drawing_set_version", {}).get("drawing_set_version")
                entry["version_hash"] = match.get("drawing_set_version", {}).get("version_hash")
                entry["beam_count"] = match.get("beam_index_meta", {}).get("beam_count", 0)
                entry["loading_state"] = match.get("loading_state")
        model["drawing_set_registry"] = registry

    def _update_project_graph(
        self,
        model: dict[str, Any],
        drawing_sets: List[dict[str, Any]],
        beam_indices: List[dict[str, Any]],
    ) -> None:
        graph = model.get("project_engineering_graph", {})
        if not graph:
            return

        graph["phase"] = "Phase G.1.3"
        nodes = list(graph.get("nodes", []))
        edges = list(graph.get("edges", []))

        index_by_set = {b.get("drawing_set_id"): b for b in beam_indices}

        for ds in drawing_sets:
            ds_id = ds.get("drawing_set_id", "")
            version = ds.get("drawing_set_version", {})
            version_id = version.get("version_id")
            index_meta = ds.get("beam_index_meta", {})
            index_node_id = f"BEAM_INDEX::{ds_id.replace('DRAWING_SET::', '')}"

            if version_id and not any(n.get("id") == version_id for n in nodes):
                nodes.append({
                    "id": version_id,
                    "type": "DRAWING_SET_VERSION",
                    "parent": ds_id,
                    "version": version.get("drawing_set_version"),
                    "version_hash": version.get("version_hash"),
                })
                edges.append({
                    "from": ds_id,
                    "to": version_id,
                    "relationship": "HAS_VERSION",
                })

            if not any(n.get("id") == index_node_id for n in nodes):
                nodes.append({
                    "id": index_node_id,
                    "type": "BEAM_INDEX",
                    "parent": ds_id,
                    "beam_count": index_meta.get("beam_count", 0),
                })
                edges.append({
                    "from": ds_id,
                    "to": index_node_id,
                    "relationship": "HAS_BEAM_INDEX",
                })

            index_data = index_by_set.get(ds_id, {})
            for mark, cid in index_data.get("index", {}).items():
                edges.append({
                    "from": index_node_id,
                    "to": cid,
                    "relationship": "INDEXES",
                    "beam_mark": mark,
                })

        graph["nodes"] = nodes
        graph["node_count"] = len(nodes)
        graph["edges"] = edges
        graph["edge_count"] = len(edges)
        model["project_engineering_graph"] = graph
