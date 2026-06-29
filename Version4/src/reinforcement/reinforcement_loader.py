"""Load reinforcement DXF files into ReinforcementWorkspace."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.framing.engineering_ids import floor_id
from src.parser.dxf_reader import DxfReader
from src.reinforcement.reinforcement_document import (
    DRAWING_TYPE_BEAM_REINFORCEMENT,
    ReinforcementDocument,
    STATUS_LOADED,
    STATUS_LOADING,
    STATUS_NOT_LOADED,
)
from src.reinforcement.reinforcement_registry import ReinforcementRegistry
from src.reinforcement.reinforcement_workspace import ReinforcementWorkspace
from src.reinforcement.reinforcement_validator import ReinforcementValidator


FLOOR_CONFIG_KEYS: Dict[str, str] = {
    "ground_floor": "GROUND_FLOOR",
    "first_floor": "FIRST_FLOOR",
    "second_floor": "SECOND_FLOOR",
    "third_floor": "THIRD_FLOOR",
    "roof": "ROOF",
    "basement": "BASEMENT",
}


def reinforcement_workspace_id(floor_slug: str) -> str:
    return f"RF_WORKSPACE::{floor_slug}"


def _identity_for_path(
    model: dict[str, Any],
    path: Path,
    drawing_type: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    target = Path(path).resolve()
    for item in model.get("drawing_identities", []):
        if drawing_type and item.get("drawing_type") != drawing_type:
            continue
        if Path(item.get("source_file", "")).resolve() == target:
            return item
    return None


class ReinforcementLoader:
    """Load reinforcement drawings and attach to floor workspaces."""

    def __init__(self, config: dict[str, Any], project_root: Optional[Path] = None) -> None:
        rl = config.get("reinforcement_loading", {})
        self._enabled = bool(rl.get("enable", True))
        self._drawings = dict(config.get("reinforcement_drawings", {}))
        if not self._drawings:
            self._drawings = dict(rl.get("drawings", {}))
        self._project_root = Path(project_root or Path.cwd())
        self._document_counter = 0
        self._stats: Dict[str, int] = {
            "floors_requested": 0,
            "floors_loaded": 0,
            "floors_skipped": 0,
        }

    def load(self, model: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Reinforcement loading disabled in config")
            return model

        workspaces: List[ReinforcementWorkspace] = []
        floor_lookup = self._floor_lookup(model)

        for config_key, path_str in self._drawings.items():
            source = self._resolve_path(path_str)
            identity = _identity_for_path(
                model,
                source,
                drawing_type=DRAWING_TYPE_BEAM_REINFORCEMENT,
            )
            if identity:
                floor_slug = str(identity.get("floor_slug", ""))
                fid = identity.get("floor_id", floor_id(floor_slug))
            else:
                floor_slug = FLOOR_CONFIG_KEYS.get(config_key, config_key.upper())
                fid = floor_id(floor_slug)

            floor_entry = floor_lookup.get(fid)
            if not floor_entry:
                logger.warning(
                    "No floor workspace for reinforcement key {} (floor_id={})",
                    config_key,
                    fid,
                )
                self._stats["floors_skipped"] += 1
                continue

            self._stats["floors_requested"] += 1
            if not source.exists():
                logger.error("Reinforcement DXF not found: {}", source)
                self._stats["floors_skipped"] += 1
                continue

            workspace = self._load_floor(source, fid, floor_slug)
            workspaces.append(workspace)
            floor_entry["reinforcement_workspace"] = workspace.to_dict()
            self._stats["floors_loaded"] += 1

        registry = ReinforcementRegistry.build(workspaces)

        model["reinforcement_workspaces"] = [ws.to_dict() for ws in workspaces]
        model["reinforcement_registry"] = registry
        validation = ReinforcementValidator().validate(model, workspaces)
        model["reinforcement_validation"] = validation
        model["reinforcement_loading_summary"] = dict(self._stats)
        model["phase_g"] = "Phase G.1"

        if model.get("project_workspace"):
            self._sync_project_workspace(model, workspaces)
        if model.get("floor_registry"):
            self._sync_floor_registry(model)

        manager = model.get("workspace_manager", {})
        manager["reinforcement_loaded"] = self._stats["floors_loaded"] > 0
        manager["reinforcement_workspace_count"] = len(workspaces)
        model["workspace_manager"] = manager

        logger.info(
            "Reinforcement loading — requested={}, loaded={}, skipped={}",
            self._stats["floors_requested"],
            self._stats["floors_loaded"],
            self._stats["floors_skipped"],
        )
        return model

    def _load_floor(
        self,
        source: Path,
        floor_id_val: str,
        floor_slug: str,
    ) -> ReinforcementWorkspace:
        self._document_counter += 1
        doc_id = f"RF-{self._document_counter:03d}"
        drawing_name = source.stem

        document = ReinforcementDocument(
            document_id=doc_id,
            source_file=str(source),
            drawing_name=drawing_name,
            drawing_type=DRAWING_TYPE_BEAM_REINFORCEMENT,
            status=STATUS_LOADING,
        )

        doc = DxfReader(source).read()
        msp = doc.modelspace()
        entity_count = sum(1 for _ in msp)
        layer_count = len(list(doc.layers))
        layout_count = len(doc.layouts)

        document.status = STATUS_LOADED
        document.entity_count = entity_count
        document.layer_count = layer_count
        document.metadata = {
            "dxf_version": doc.dxfversion,
            "layout_count": layout_count,
            "file_size_bytes": source.stat().st_size,
            "modelspace_entity_count": entity_count,
        }

        return ReinforcementWorkspace(
            workspace_id=reinforcement_workspace_id(floor_slug),
            document=document,
            floor_id=floor_id_val,
            floor_slug=floor_slug,
            status=STATUS_LOADED,
        )

    def _floor_lookup(self, model: dict[str, Any]) -> Dict[str, dict[str, Any]]:
        lookup: Dict[str, dict[str, Any]] = {}
        project = model.get("project_workspace", {})
        for floor in project.get("floors", []):
            fid = floor.get("floor_id")
            if fid:
                lookup[fid] = floor
        return lookup

    def _sync_project_workspace(
        self,
        model: dict[str, Any],
        workspaces: List[ReinforcementWorkspace],
    ) -> None:
        ws_by_floor = {ws.floor_id: ws for ws in workspaces}
        project = model["project_workspace"]
        for floor in project.get("floors", []):
            fid = floor.get("floor_id")
            if fid in ws_by_floor:
                floor["reinforcement_workspace"] = ws_by_floor[fid].to_dict()
                floor.pop("reinforcement_plan", None)

    def _sync_floor_registry(self, model: dict[str, Any]) -> None:
        registry = model.get("floor_registry", {})
        ws_status = {
            w.get("floor_id"): w.get("status", STATUS_LOADED)
            for w in model.get("reinforcement_workspaces", [])
        }
        for entry in registry.get("entries", []):
            fid = entry.get("floor_id")
            if fid in ws_status:
                entry["reinforcement"] = ws_status[fid]

    def _resolve_path(self, path_str: str) -> Path:
        path = Path(path_str)
        if path.is_absolute():
            return path
        return (self._project_root / path).resolve()

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)
