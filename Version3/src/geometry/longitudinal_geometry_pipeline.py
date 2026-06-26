"""Phase D.4.2 — longitudinal geometry resolution pipeline."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from loguru import logger

from src.config.output_paths import OutputPaths
from src.geometry.longitudinal_geometry_debug_exporter import (
    LongitudinalGeometryDebugExporter,
)
from src.geometry.longitudinal_geometry_resolver import (
    LongitudinalGeometryResolver,
    load_rebar_geometry_config,
)
from src.geometry.longitudinal_geometry_validator import LongitudinalGeometryValidator
from src.geometry.rebar_locator import RebarLocator

DEFAULT_REINFORCEMENT_DXF = Path("data/reinforcement/Beam_ReinforcementDetails.dxf")
DEFAULT_CONFIG = Path("config/rebar_geometry.yaml")


class LongitudinalGeometryPipeline:
    """Run Phase D.4.2 geometry resolution between D.4 and D.4.1."""

    def __init__(
        self,
        output_paths: OutputPaths,
        dxf_path: Path | str = DEFAULT_REINFORCEMENT_DXF,
        config_path: Path | str = DEFAULT_CONFIG,
    ) -> None:
        self._outputs = output_paths
        self._dxf_path = Path(dxf_path)
        self._config_path = Path(config_path)

    def run(self) -> Dict[str, Any]:
        config = load_rebar_geometry_config(self._config_path)
        objects = self._read_json(self._outputs.engineering_objects)
        locator = RebarLocator(str(self._dxf_path))
        region_unions = self._build_region_unions(objects)
        sketch_bbox_lookup = self._build_sketch_bbox_lookup()
        resolver = LongitudinalGeometryResolver(
            locator, config, region_unions, sketch_bbox_lookup
        )
        enriched, resolutions = resolver.resolve_all(objects)
        validation = LongitudinalGeometryValidator().validate(enriched, resolutions)
        summary = self._build_summary(enriched, resolutions, validation)

        self._outputs.phase_d42_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(
            self._outputs.longitudinal_geometry_resolution, resolutions
        )
        self._write_json(self._outputs.engineering_objects_enriched, enriched)
        self._write_json(self._outputs.phase_d42_summary, summary)
        self._write_json(self._outputs.phase_d42_validation, validation)

        if config.get("enable_debug_layers", True):
            LongitudinalGeometryDebugExporter(locator).export(
                enriched, self._outputs.phase_d42_debug_dxf, config
            )

        logger.info("Phase D.4.2 complete — validation {}", validation["status"])
        return {
            "enriched": enriched,
            "resolutions": resolutions,
            "validation": validation,
            "summary": summary,
        }

    def _build_summary(
        self,
        enriched: List[dict[str, Any]],
        resolutions: List[dict[str, Any]],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        longitudinal = [
            o
            for o in enriched
            if o.get("engineering_type") == "LONGITUDINAL_BAR"
            and o.get("parser_status") == "SUCCESS"
        ]
        resolved = [
            o for o in longitudinal if o.get("resolved_position") is not None
        ]
        attached = [
            o
            for o in longitudinal
            if (o.get("geometry_resolution") or {}).get("attached_entity_id")
        ]
        leader_attach = sum(
            1
            for o in longitudinal
            if (o.get("geometry_resolution") or {}).get("attachment_method")
            == "LEADER_ENDPOINT"
        )
        nearest_attach = sum(
            1
            for o in longitudinal
            if (o.get("geometry_resolution") or {}).get("attachment_method")
            == "NEAREST_LINE"
        )
        top = sum(1 for o in longitudinal if o.get("resolved_position") == "TOP")
        bottom = sum(
            1 for o in longitudinal if o.get("resolved_position") == "BOTTOM"
        )
        continuous = sum(
            1 for o in longitudinal if o.get("resolved_continuity") == "CONTINUOUS"
        )
        partial = sum(
            1 for o in longitudinal if o.get("resolved_continuity") == "PARTIAL"
        )
        return {
            "longitudinal_bar_count": len(longitudinal),
            "resolved_count": len(resolved),
            "geometry_attached_count": len(attached),
            "leader_attachment_count": leader_attach,
            "nearest_line_attachment_count": nearest_attach,
            "top_bar_count": top,
            "bottom_bar_count": bottom,
            "continuous_count": continuous,
            "partial_count": partial,
            "failure_count": validation.get("failure_count", 0),
            "validation_status": validation["status"],
        }

    def _build_region_unions(
        self, objects: List[dict[str, Any]]
    ) -> dict[tuple[str, str], dict[str, float]]:
        buckets: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
        sketch_by_mark: dict[str, list[dict[str, float]]] = defaultdict(list)
        region_bbox_by_id: dict[str, dict[str, float]] = {}
        sketches_path = self._outputs.beam_sketches_debug
        regions_path = self._outputs.detail_regions
        if regions_path.exists():
            for region in self._read_json(regions_path):
                region_id = str(region.get("region_id", ""))
                bbox = region.get("bbox")
                if region_id and bbox:
                    region_bbox_by_id[region_id] = bbox
        if sketches_path.exists():
            for sketch in self._read_json(sketches_path):
                mark = str(sketch.get("beam_mark", ""))
                bbox = sketch.get("bbox")
                if mark and bbox:
                    sketch_by_mark[mark].append(bbox)

        for obj in objects:
            if obj.get("engineering_type") != "LONGITUDINAL_BAR":
                continue
            bbox = obj.get("sketch_bbox")
            if bbox:
                key = (
                    str(obj.get("detail_region_id", "")),
                    str(obj.get("resolved_beam_mark", "")),
                )
                buckets[key].append(bbox)
            mark = str(obj.get("resolved_beam_mark", ""))
            if mark in sketch_by_mark:
                key = (
                    str(obj.get("detail_region_id", "")),
                    mark,
                )
                buckets[key].extend(sketch_by_mark[mark])
            region_id = str(obj.get("detail_region_id", ""))
            if region_id in region_bbox_by_id:
                key = (region_id, str(obj.get("resolved_beam_mark", "")))
                buckets[key].append(region_bbox_by_id[region_id])

        unions: dict[tuple[str, str], dict[str, float]] = {}
        for key, bboxes in buckets.items():
            unions[key] = {
                "xmin": min(float(b["xmin"]) for b in bboxes),
                "ymin": min(float(b["ymin"]) for b in bboxes),
                "xmax": max(float(b["xmax"]) for b in bboxes),
                "ymax": max(float(b["ymax"]) for b in bboxes),
            }
        return unions

    def _build_sketch_bbox_lookup(self) -> dict[str, dict[str, float]]:
        lookup: dict[str, dict[str, float]] = {}
        sketches_path = self._outputs.beam_sketches_debug
        if not sketches_path.exists():
            return lookup
        for sketch in self._read_json(sketches_path):
            sketch_id = str(sketch.get("sketch_id", ""))
            bbox = sketch.get("bbox")
            if sketch_id and bbox:
                lookup[sketch_id] = bbox
        return lookup

    @staticmethod
    def _read_json(path: Path) -> List[dict[str, Any]]:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
