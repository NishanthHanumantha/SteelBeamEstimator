"""Build drawing sets from identified drawings and enrich beam contexts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.project.drawing_identity import (
    DRAWING_TYPE_BEAM_REINFORCEMENT,
    DRAWING_TYPE_FRAMING_PLAN,
    DRAWING_TYPE_GENERAL_NOTES,
)
from src.project.drawing_set import (
    DrawingSet,
    drawing_set_id,
    STATUS_COMPLETE,
    STATUS_PARTIAL,
)
from src.project.drawing_set_registry import DrawingSetRegistry
from src.project.drawing_set_validator import DrawingSetValidator
from src.project.project_registry import ProjectRegistry


class DrawingSetBuilder:
    """Assemble drawing sets per engineering level and enrich project model."""

    def __init__(self, config: dict[str, Any]) -> None:
        ds_cfg = config.get("drawing_set", {})
        self._enabled = bool(ds_cfg.get("enable", True))

    def build_model(self, model: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Drawing set assembly disabled in config")
            return model

        identities = model.get("drawing_identities", [])
        general_notes_id = self._general_notes_id(identities)
        drawing_sets = self._assemble_sets(identities, general_notes_id)

        self._enrich_beam_contexts(model, drawing_sets, identities)
        self._enrich_floor_workspaces(model, drawing_sets)
        self._enrich_project_workspace(model, drawing_sets)
        self._update_project_registry(model)
        self._update_drawing_registry(model, drawing_sets)
        self._update_project_graph(model, drawing_sets, identities)

        registry = DrawingSetRegistry.build(drawing_sets)
        model["drawing_sets"] = [ds.to_dict() for ds in drawing_sets]
        validation = DrawingSetValidator().validate(model, drawing_sets)
        model["drawing_set_registry"] = registry
        model["drawing_set_validation"] = validation
        model["phase_g"] = "Phase G.1.2"

        manager = model.get("workspace_manager", {})
        manager["drawing_set_count"] = len(drawing_sets)
        manager["phase"] = "Phase G.1.2"
        model["workspace_manager"] = manager
        model["phase"] = "Phase G.1.2"
        model["model_version"] = "1.8"

        logger.info(
            "Drawing sets — count={}, complete={}",
            len(drawing_sets),
            sum(1 for ds in drawing_sets if ds.status == STATUS_COMPLETE),
        )
        return model

    def _general_notes_id(self, identities: List[dict[str, Any]]) -> Optional[str]:
        for item in identities:
            if item.get("drawing_type") == DRAWING_TYPE_GENERAL_NOTES:
                return item.get("drawing_id")
        return None

    def _assemble_sets(
        self,
        identities: List[dict[str, Any]],
        general_notes_id: Optional[str],
    ) -> List[DrawingSet]:
        floor_groups: Dict[str, List[dict[str, Any]]] = {}
        for item in identities:
            if item.get("drawing_type") == DRAWING_TYPE_GENERAL_NOTES:
                continue
            fid = item.get("floor_id")
            if not fid:
                continue
            floor_groups.setdefault(fid, []).append(item)

        drawing_sets: List[DrawingSet] = []
        for fid, group in floor_groups.items():
            floor_slug = str(group[0].get("floor_slug", ""))
            floor_name = str(group[0].get("floor_name", floor_slug))
            project_id_val = str(group[0].get("project_id", ""))

            framing_id = self._drawing_id_for_type(group, DRAWING_TYPE_FRAMING_PLAN)
            reinforcement_id = self._drawing_id_for_type(group, DRAWING_TYPE_BEAM_REINFORCEMENT)

            status = STATUS_COMPLETE if framing_id and reinforcement_id else STATUS_PARTIAL
            confidences = [float(item.get("confidence", 0.0)) for item in group]
            confidence = min(confidences) if confidences else 0.0

            drawing_sets.append(
                DrawingSet(
                    drawing_set_id=drawing_set_id(floor_slug),
                    floor_id=fid,
                    floor_name=floor_name,
                    project_id=project_id_val,
                    status=status,
                    drawings={
                        "framing": framing_id,
                        "reinforcement": reinforcement_id,
                        "general_notes": general_notes_id,
                    },
                    confidence=confidence if status == STATUS_COMPLETE else confidence * 0.9,
                    metadata={
                        "floor_slug": floor_slug,
                        "drawing_count": len(group),
                    },
                )
            )
        return drawing_sets

    def _drawing_id_for_type(
        self,
        group: List[dict[str, Any]],
        drawing_type: str,
    ) -> Optional[str]:
        for item in group:
            if item.get("drawing_type") == drawing_type:
                return item.get("drawing_id")
        return None

    def _enrich_beam_contexts(
        self,
        model: dict[str, Any],
        drawing_sets: List[DrawingSet],
        identities: List[dict[str, Any]],
    ) -> None:
        set_by_floor = {ds.floor_id: ds for ds in drawing_sets}
        framing_by_floor = {
            item["floor_id"]: item["drawing_id"]
            for item in identities
            if item.get("drawing_type") == DRAWING_TYPE_FRAMING_PLAN and item.get("floor_id")
        }
        reinforcement_by_floor = {
            item["floor_id"]: item["drawing_id"]
            for item in identities
            if item.get("drawing_type") == DRAWING_TYPE_BEAM_REINFORCEMENT and item.get("floor_id")
        }

        for ctx in model.get("beam_engineering_contexts", []):
            fid = ctx.get("floor_id")
            ds = set_by_floor.get(fid)
            if ds:
                ctx["drawing_set_id"] = ds.drawing_set_id
                ctx["drawing_id"] = framing_by_floor.get(fid) or ds.drawings.get("framing")
            else:
                ctx["drawing_set_id"] = ""
                ctx["drawing_id"] = ""

            ctx["reinforcement_drawing_id"] = reinforcement_by_floor.get(fid)
            ctx["reinforcement_context_id"] = None

            meta = dict(ctx.get("metadata") or {})
            meta["phase"] = "Phase G.1.2"
            ctx["metadata"] = meta

    def _enrich_floor_workspaces(
        self,
        model: dict[str, Any],
        drawing_sets: List[DrawingSet],
    ) -> None:
        set_by_floor = {ds.floor_id: ds for ds in drawing_sets}
        project = model.get("project_workspace", {})
        for floor in project.get("floors", []):
            fid = floor.get("floor_id")
            ds = set_by_floor.get(fid)
            if not ds:
                continue
            meta = dict(floor.get("metadata") or {})
            meta["drawing_set_id"] = ds.drawing_set_id
            floor["metadata"] = meta
            if floor.get("framing_plan"):
                floor["framing_plan"]["drawing_set_id"] = ds.drawing_set_id
            rw = floor.get("reinforcement_workspace")
            if rw:
                rw["drawing_set_id"] = ds.drawing_set_id

    def _enrich_project_workspace(
        self,
        model: dict[str, Any],
        drawing_sets: List[DrawingSet],
    ) -> None:
        project = model.get("project_workspace", {})
        if not project:
            return
        project["drawing_sets"] = [ds.drawing_set_id for ds in drawing_sets]
        meta = dict(project.get("metadata") or {})
        meta["phase"] = "Phase G.1.2"
        meta["drawing_set_count"] = len(drawing_sets)
        project["metadata"] = meta
        model["project_workspace"] = project

    def _update_project_registry(self, model: dict[str, Any]) -> None:
        project_ws = model.get("project_workspace", {})
        if not project_ws:
            return
        registry = dict(model.get("project_registry", {}))
        registry["phase"] = "Phase G.1.2"
        registry["drawing_sets"] = project_ws.get("drawing_sets", [])
        registry["drawing_set_count"] = len(project_ws.get("drawing_sets", []))
        model["project_registry"] = registry

    def _update_drawing_registry(
        self,
        model: dict[str, Any],
        drawing_sets: List[DrawingSet],
    ) -> None:
        set_by_drawing: Dict[str, str] = {}
        for ds in drawing_sets:
            for key, did in ds.drawings.items():
                if key == "general_notes" or not did:
                    continue
                set_by_drawing[did] = ds.drawing_set_id

        registry = dict(model.get("drawing_registry", {}))
        registry["phase"] = "Phase G.1.2"
        for entry in registry.get("drawings", []):
            did = entry.get("drawing_id")
            if did in set_by_drawing:
                entry["drawing_set_id"] = set_by_drawing[did]
        model["drawing_registry"] = registry

    def _update_project_graph(
        self,
        model: dict[str, Any],
        drawing_sets: List[DrawingSet],
        identities: List[dict[str, Any]],
    ) -> None:
        graph = model.get("project_engineering_graph", {})
        if not graph:
            return

        graph["phase"] = "Phase G.1.2"
        nodes = list(graph.get("nodes", []))
        edges = list(graph.get("edges", []))
        pid = graph.get("project_id")

        identity_by_id = {item["drawing_id"]: item for item in identities}

        for ds in drawing_sets:
            if not any(n.get("id") == ds.drawing_set_id for n in nodes):
                nodes.append(
                    {
                        "id": ds.drawing_set_id,
                        "type": "DRAWING_SET",
                        "parent": pid,
                        "floor_id": ds.floor_id,
                        "floor_name": ds.floor_name,
                        "status": ds.status,
                    }
                )
            if not any(
                e.get("from") == pid and e.get("to") == ds.drawing_set_id
                for e in edges
            ):
                edges.append({
                    "from": pid,
                    "to": ds.drawing_set_id,
                    "relationship": "HAS_DRAWING_SET",
                })

            edges.append({
                "from": ds.drawing_set_id,
                "to": ds.floor_id,
                "relationship": "HAS_FLOOR",
            })

            for slot, drawing_key in (
                ("framing", "framing"),
                ("reinforcement", "reinforcement"),
            ):
                did = ds.drawings.get(drawing_key)
                if not did:
                    continue
                identity = identity_by_id.get(did, {})
                rel = "HAS_FRAMING" if slot == "framing" else "HAS_REINFORCEMENT"
                if not any(n.get("id") == did for n in nodes):
                    nodes.append({
                        "id": did,
                        "type": "DRAWING",
                        "parent": ds.drawing_set_id,
                        "drawing_type": identity.get("drawing_type"),
                    })
                edges.append({"from": ds.drawing_set_id, "to": did, "relationship": rel})

            gn_id = ds.drawings.get("general_notes")
            if gn_id:
                edges.append({
                    "from": ds.drawing_set_id,
                    "to": gn_id,
                    "relationship": "REFERENCES_GENERAL_NOTES",
                })

            fp = model.get("project_workspace", {}).get("floors", [])
            for floor in fp:
                if floor.get("floor_id") != ds.floor_id:
                    continue
                framing_ws = floor.get("framing_plan", {}).get("workspace_id")
                if framing_ws:
                    edges.append({
                        "from": ds.drawing_set_id,
                        "to": framing_ws,
                        "relationship": "HAS_FRAMING_WORKSPACE",
                    })
                rw = floor.get("reinforcement_workspace", {})
                rf_ws = rw.get("workspace_id")
                if rf_ws:
                    edges.append({
                        "from": ds.drawing_set_id,
                        "to": rf_ws,
                        "relationship": "HAS_REINFORCEMENT_WORKSPACE",
                    })

        for ctx in model.get("beam_engineering_contexts", []):
            ds_id = ctx.get("drawing_set_id")
            cid = ctx.get("context_id")
            if ds_id and cid:
                edges.append({
                    "from": ds_id,
                    "to": cid,
                    "relationship": "HAS_BEAM_CONTEXT",
                })

        graph["nodes"] = nodes
        graph["node_count"] = len(nodes)
        graph["edges"] = edges
        graph["edge_count"] = len(edges)
        model["project_engineering_graph"] = graph
