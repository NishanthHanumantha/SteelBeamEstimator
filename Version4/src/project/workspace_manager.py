"""Workspace manager — main entry for project + floor loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.framing.engineering_ids import (
    GENERAL_NOTES_DOC_ID,
    GENERAL_NOTES_ID,
    KNOWLEDGE_PROJECT_DEFAULTS,
    RULE_ESTIMATOR,
    RULE_PROJECT,
    SERVICES_ID,
    floor_id,
    floor_slug_from_name,
    project_id,
    slug_from_project_name,
)
from src.framing.engineering_state_machine import EngineeringStateMachine, STATE_READY
from src.project.drawing_identity import (
    DRAWING_TYPE_FRAMING_PLAN,
    framing_workspace_id,
)
from src.project.floor_workspace import FloorWorkspace
from src.project.project_registry import ProjectRegistry
from src.project.project_workspace import ProjectWorkspace
from src.services.engineering_services import EngineeringServices


class WorkspaceManager:
    """Load project, floors, contexts, and engineering services."""

    def __init__(self) -> None:
        self.project: Optional[ProjectWorkspace] = None
        self.floors: list[FloorWorkspace] = []
        self.services: Optional[EngineeringServices] = None
        self._knowledge_version = "1.0"
        self._floor_source = "config_default"

    def load(
        self,
        model: dict[str, Any],
        output_root: Path,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        ws_cfg = config.get("workspace", {})
        self._knowledge_version = str(
            config.get("engineering_context", {}).get("knowledge_version", "1.0")
        )
        output_root = Path(output_root)

        self.services = EngineeringServices.initialize(output_root, self._knowledge_version)
        project_slug, project_name = self._resolve_project_identity(output_root)
        pid = project_id(project_slug)

        framing_identities = [
            item for item in model.get("drawing_identities", [])
            if item.get("drawing_type") == DRAWING_TYPE_FRAMING_PLAN
        ]
        primary_floor_id = self._build_floors(
            model,
            ws_cfg,
            pid,
            framing_identities,
        )

        contexts = self._refine_contexts(model, pid, primary_floor_id)
        model["beam_engineering_contexts"] = contexts

        for floor_ws in self.floors:
            floor_ws.beam_contexts = [
                {
                    "context_id": c.get("context_id"),
                    "beam_id": c.get("beam_id"),
                    "beam_mark": c.get("beam_mark"),
                    "status": c.get("status"),
                }
                for c in contexts
            ]

        self.project = ProjectWorkspace(
            project_id=pid,
            project_name=project_name,
            general_notes={
                "document_id": GENERAL_NOTES_DOC_ID,
                "knowledge_id": GENERAL_NOTES_ID,
                "version": self._knowledge_version,
                "status": "LOADED",
            },
            engineering_rules={
                "rule_id": RULE_PROJECT,
                "knowledge_id": RULE_PROJECT,
                "version": self._knowledge_version,
            },
            floors=[f.to_dict() for f in self.floors],
            services=self.services.to_workspace_ref(),
            metadata={
                "phase": "Phase G.1.1",
                "floor_count": len(self.floors),
                "beam_context_count": len(contexts),
                "floor_source": self._floor_source,
            },
        )

        project_registry = ProjectRegistry.build(self.project)
        floor_registry = ProjectRegistry.build_floor_registry(self.project.floors)
        services_registry = self.services.registry()
        manager_snapshot = self._build_manager_snapshot(model)

        model["project_workspace"] = self.project.to_dict()
        model["project_registry"] = project_registry
        model["floor_registry"] = floor_registry
        model["engineering_services_registry"] = services_registry
        model["workspace_manager"] = manager_snapshot
        model["phase"] = "Phase G.1.1"
        model["model_version"] = "1.7"

        self._update_project_graph(model)
        self._update_beam_lifecycle(model)

        logger.info(
            "Workspace loaded — project={}, floors={}, contexts={}, services=5, floor_source={}",
            pid,
            len(self.floors),
            len(contexts),
            self._floor_source,
        )
        return model

    def _build_floors(
        self,
        model: dict[str, Any],
        ws_cfg: dict[str, Any],
        pid: str,
        framing_identities: List[dict[str, Any]],
    ) -> str:
        self.floors = []
        if framing_identities:
            self._floor_source = "drawing_identity"
            for identity in framing_identities:
                floor_slug = str(identity.get("floor_slug", ""))
                fid = identity.get("floor_id", floor_id(floor_slug))
                floor_name = str(identity.get("floor_name", floor_slug))
                self.floors.append(
                    FloorWorkspace(
                        floor_id=fid,
                        floor_name=floor_name,
                        framing_plan={
                            "workspace_id": framing_workspace_id(floor_slug),
                            "drawing_id": identity.get("drawing_id"),
                            "status": "LOADED",
                            "source": identity.get("source_file"),
                            "drawing_title": identity.get("drawing_title"),
                            "beam_count": len(model.get("beams", [])),
                            "phase": "Phase G.1.1",
                        },
                        beam_contexts=[],
                        metadata={
                            "project_id": pid,
                            "computation_state": STATE_READY,
                            "floor_slug": floor_slug,
                            "detection_source": identity.get("detection_source"),
                        },
                    )
                )
            return self.floors[0].floor_id

        self._floor_source = "config_default"
        floor_cfg = ws_cfg.get("default_floor", {})
        if not isinstance(floor_cfg, dict):
            floor_cfg = {"name": "Ground Floor", "slug": str(floor_cfg or "GROUND_FLOOR")}
        floor_name = str(floor_cfg.get("name", "Ground Floor"))
        floor_slug = str(floor_cfg.get("slug", floor_slug_from_name(floor_name)))
        fid = floor_id(floor_slug)

        framing_source = model.get("source_files", [])
        if not framing_source and model.get("beams"):
            framing_source = [str(ws_cfg.get("framing_plan", "data/framing/Beam_FramingPlan.dxf"))]

        self.floors = [
            FloorWorkspace(
                floor_id=fid,
                floor_name=floor_name,
                framing_plan={
                    "workspace_id": framing_workspace_id(floor_slug),
                    "status": "LOADED",
                    "source": framing_source[0] if framing_source else None,
                    "beam_count": len(model.get("beams", [])),
                    "phase": "Phase F.7",
                },
                beam_contexts=[],
                metadata={
                    "project_id": pid,
                    "computation_state": STATE_READY,
                    "floor_slug": floor_slug,
                },
            )
        ]
        return fid

    def _refine_contexts(
        self,
        model: dict[str, Any],
        project_id_val: str,
        floor_id_val: str,
    ) -> list[dict[str, Any]]:
        refined: list[dict[str, Any]] = []
        version = self._knowledge_version
        for ctx in model.get("beam_engineering_contexts", []):
            entry = dict(ctx)
            entry.pop("project_engineering_rules", None)
            entry.pop("estimator_rules", None)
            entry.pop("project_defaults", None)
            entry["project_id"] = project_id_val
            entry["floor_id"] = floor_id_val
            entry["rule_reference"] = {
                "rule_id": RULE_PROJECT,
                "knowledge_id": RULE_PROJECT,
                "version": version,
            }
            entry["estimator_rules_reference"] = {
                "rule_id": RULE_ESTIMATOR,
                "knowledge_id": RULE_ESTIMATOR,
                "version": version,
            }
            entry["project_defaults_reference"] = {
                "knowledge_id": KNOWLEDGE_PROJECT_DEFAULTS,
                "version": version,
            }
            entry["services"] = SERVICES_ID
            entry["metadata"] = {
                **(entry.get("metadata") or {}),
                "phase": "Phase G.1.1",
                "knowledge_references": [
                    RULE_PROJECT,
                    RULE_ESTIMATOR,
                    KNOWLEDGE_PROJECT_DEFAULTS,
                    GENERAL_NOTES_ID,
                ],
            }
            refined.append(entry)
        return refined

    def _resolve_project_identity(self, output_root: Path) -> tuple[str, str]:
        meta_path = output_root / "phase_e" / "project_metadata.json"
        name = "Sobha Galera Clubhouse"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            name = (
                meta.get("project_information", {})
                .get("project_name", {})
                .get("value", name)
            )
        return slug_from_project_name(name), name

    def _build_manager_snapshot(self, model: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase G.1.1",
            "status": STATE_READY,
            "project_id": self.project.project_id if self.project else None,
            "floor_count": len(self.floors),
            "beam_context_count": len(model.get("beam_engineering_contexts", [])),
            "services": SERVICES_ID,
            "services_initialized": self.services is not None,
            "floor_source": self._floor_source,
            "drawing_identity_count": len(model.get("drawing_identities", [])),
            "computation_state_machine": EngineeringStateMachine(STATE_READY).to_dict(),
            "ready_for_computation": True,
        }

    def _update_project_graph(self, model: dict[str, Any]) -> None:
        graph = model.get("project_engineering_graph", {})
        if not graph:
            return
        graph["phase"] = "Phase G.1.1"
        nodes = graph.get("nodes", [])
        pid = graph.get("project_id")
        edges = graph.get("edges", [])
        for floor_ws in self.floors:
            floor_node = {
                "id": floor_ws.floor_id,
                "type": "FLOOR",
                "parent": pid,
                "floor_name": floor_ws.floor_name,
            }
            if not any(n.get("id") == floor_ws.floor_id for n in nodes):
                nodes.append(floor_node)
                edges.append({
                    "from": pid,
                    "to": floor_ws.floor_id,
                    "relationship": "HAS_FLOOR",
                })
        graph["nodes"] = nodes
        graph["node_count"] = len(nodes)
        graph["edges"] = edges
        graph["edge_count"] = len(edges)
        model["project_engineering_graph"] = graph

    def _update_beam_lifecycle(self, model: dict[str, Any]) -> None:
        placeholder = EngineeringStateMachine.placeholder()
        for beam in model.get("beams", []):
            beam["reinforcement"] = dict(placeholder)
            beam["quantities"] = dict(placeholder)
            beam["boq"] = dict(placeholder)
            lifecycle = beam.get("lifecycle", {})
            for key in ("reinforcement", "quantities", "boq"):
                lifecycle[key] = dict(placeholder)
            beam["lifecycle"] = lifecycle
