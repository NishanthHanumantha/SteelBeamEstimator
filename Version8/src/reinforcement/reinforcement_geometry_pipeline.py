"""Phase G.2 — Reinforcement drawing geometry intelligence pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from src.parser.dxf_reader import DxfReader
from src.reinforcement.block_extractor import BlockExtractor
from src.reinforcement.drawing_relationship_builder import DrawingRelationshipBuilder
from src.reinforcement.leader_extractor import LeaderExtractor
from src.reinforcement.reinforcement_detail_view_builder import EngineeringDetailViewBuilder
from src.reinforcement.reinforcement_drawing_builder import ReinforcementDrawingBuilder
from src.reinforcement.reinforcement_region_detector import ReinforcementRegionDetector
from src.reinforcement.reinforcement_sketch_detector import ReinforcementSketchDetector
from src.reinforcement.reinforcement_text_extractor import ReinforcementTextExtractor


class ReinforcementGeometryPipeline:
    """Extract immutable geometry intelligence from loaded reinforcement drawings."""

    def __init__(self, config: dict[str, Any], project_root: Path | None = None) -> None:
        g2 = config.get("reinforcement_geometry", {})
        self._enabled = bool(g2.get("enable", True))
        self._project_root = Path(project_root or Path.cwd())
        self._config = config

    def build_model(self, model: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Reinforcement geometry pipeline disabled in config")
            return model

        payloads: List[dict[str, Any]] = []
        for workspace in model.get("reinforcement_workspaces", []):
            payload = self._process_workspace(workspace)
            if payload:
                payloads.append(payload)

        model["reinforcement_geometry_payloads"] = payloads
        return ReinforcementDrawingBuilder(self._config).build_model(model)

    def _process_workspace(self, workspace: dict[str, Any]) -> Dict[str, Any]:
        document = workspace.get("document", {})
        source_file = Path(str(document.get("source_file", "")))
        if not source_file.exists():
            resolved = (self._project_root / source_file).resolve()
            if resolved.exists():
                source_file = resolved
            else:
                logger.error("Reinforcement source missing for geometry extraction: {}", source_file)
                return {}

        doc = DxfReader(source_file).read()
        entities = list(doc.modelspace())

        text_extractor = ReinforcementTextExtractor()
        leader_extractor = LeaderExtractor(self._config)
        block_extractor = BlockExtractor()

        text_objects = text_extractor.extract(entities)
        leaders = leader_extractor.extract(entities)
        blocks = block_extractor.extract(entities)

        region_detector = ReinforcementRegionDetector(self._config)
        regions = region_detector.detect(entities, text_objects, leaders, blocks)

        sketch_detector = ReinforcementSketchDetector(self._config)
        sketches = sketch_detector.detect(entities, regions)

        view_builder = EngineeringDetailViewBuilder(self._config)
        detail_views = view_builder.build(
            regions,
            text_objects,
            leaders,
            blocks,
            sketches,
        )

        relationships = DrawingRelationshipBuilder().build(
            regions,
            sketches,
            text_objects,
            leaders,
            blocks,
        )

        logger.info(
            "Reinforcement geometry — floor={} regions={} views={} sketches={} text={} leaders={} blocks={}",
            workspace.get("floor_slug"),
            len(regions),
            len(detail_views),
            len(sketches),
            len(text_objects),
            len(leaders),
            len(blocks),
        )

        return {
            "floor_id": workspace.get("floor_id", ""),
            "floor_slug": workspace.get("floor_slug", ""),
            "workspace_id": workspace.get("workspace_id", ""),
            "source_file": str(source_file),
            "regions": regions,
            "detail_views": detail_views,
            "sketches": sketches,
            "text_objects": text_objects,
            "leaders": leaders,
            "blocks": blocks,
            "relationships": relationships,
        }
