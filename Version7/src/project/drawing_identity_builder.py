"""Build drawing identities from project drawings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.framing.engineering_ids import project_id, slug_from_project_name
from src.project.drawing_identity import (
    DISCIPLINE_STRUCTURAL,
    DRAWING_TYPE_BEAM_REINFORCEMENT,
    DRAWING_TYPE_FRAMING_PLAN,
    DRAWING_TYPE_GENERAL_NOTES,
    DrawingIdentity,
    drawing_id_for,
    STATUS_IDENTIFIED,
)
from src.project.drawing_identity_validator import DrawingIdentityValidator
from src.project.drawing_registry import DrawingRegistry
from src.project.floor_detector import FloorDetector


class DrawingIdentityBuilder:
    """Identify drawings and detect floors before workspace creation."""

    def __init__(self, config: dict[str, Any], project_root: Path) -> None:
        di = config.get("drawing_identity", {})
        self._enabled = bool(di.get("enable", True))
        self._project_root = Path(project_root)
        self._detector = FloorDetector(config)
        self._general_notes_path = di.get(
            "general_notes_path",
            "data/general_notes/SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf",
        )

    def build_model(
        self,
        model: dict[str, Any],
        framing_paths: List[Path],
        reinforcement_paths: List[Path],
        output_root: Path,
    ) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Drawing identity detection disabled in config")
            return model

        pid = self._resolve_project_id(output_root)
        identities: List[DrawingIdentity] = []
        floor_detections: List[dict[str, Any]] = []

        for path in framing_paths:
            identity, detection = self._identify(path, DRAWING_TYPE_FRAMING_PLAN, pid)
            identities.append(identity)
            floor_detections.append(detection.to_dict())

        for path in reinforcement_paths:
            identity, detection = self._identify(path, DRAWING_TYPE_BEAM_REINFORCEMENT, pid)
            identities.append(identity)
            floor_detections.append(detection.to_dict())

        gn_path = self._resolve_path(self._general_notes_path)
        if gn_path.exists():
            identity, detection = self._identify(gn_path, DRAWING_TYPE_GENERAL_NOTES, pid)
            identities.append(identity)
            floor_detections.append(detection.to_dict())

        registry = DrawingRegistry.build(identities)
        model["drawing_identities"] = [item.to_dict() for item in identities]
        model["drawing_registry"] = registry
        model["floor_detection"] = floor_detections
        model["phase_g"] = "Phase G.1.1"

        logger.info(
            "Drawing identity — identities={}, floors_detected={}",
            len(identities),
            len({d.get("floor_id") for d in floor_detections if d.get("floor_id")}),
        )
        return model

    def finalize_validation(self, model: dict[str, Any]) -> dict[str, Any]:
        validation = DrawingIdentityValidator().validate(model)
        model["drawing_identity_validation"] = validation
        return model

    def _identify(
        self,
        path: Path,
        expected_type: str,
        project_id_val: str,
    ) -> tuple[DrawingIdentity, Any]:
        path = Path(path).resolve()
        detection = self._detector.detect_from_dxf(path, expected_type=expected_type)

        floor_slug = detection.floor_slug
        floor_id_val = detection.floor_id
        floor_name = detection.floor_name

        if expected_type == DRAWING_TYPE_GENERAL_NOTES:
            floor_slug = None
            floor_id_val = None
            floor_name = None

        identity = DrawingIdentity(
            drawing_id=drawing_id_for(floor_slug, detection.drawing_type),
            drawing_type=detection.drawing_type,
            discipline=DISCIPLINE_STRUCTURAL,
            floor_id=floor_id_val,
            floor_name=floor_name,
            floor_slug=floor_slug,
            project_id=project_id_val,
            revision=detection.revision,
            sheet_number=detection.sheet_number,
            drawing_title=detection.drawing_title,
            status=STATUS_IDENTIFIED,
            confidence=detection.confidence,
            source_file=str(path),
            detection_source=detection.detection_source,
            metadata={
                "layout_names": detection.metadata.get("layout_names", []),
                "title_block_block": detection.metadata.get("title_block_block"),
                "title_block_layout": detection.metadata.get("title_block_layout"),
            },
        )
        return identity, detection

    def _resolve_project_id(self, output_root: Path) -> str:
        meta_path = Path(output_root) / "phase_e" / "project_metadata.json"
        name = "Sobha Galera Clubhouse"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            name = (
                meta.get("project_information", {})
                .get("project_name", {})
                .get("value", name)
            )
        return project_id(slug_from_project_name(name))

    def _resolve_path(self, path_str: str) -> Path:
        path = Path(path_str)
        if path.is_absolute():
            return path.resolve()
        return (self._project_root / path).resolve()

    @staticmethod
    def identity_for_path(
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
