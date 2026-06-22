"""Geometry-driven reinforcement detail block extraction (Phase 3B.3)."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple, TypedDict

from ezdxf import recover
from loguru import logger

from src.extractor.annotation_owner import (
    assign_annotations,
    is_detail_complete,
    SketchTarget,
)
from src.extractor.beam_label_extractor import BEAM_LABEL_PATTERN
from src.extractor.detail_text_filter import (
    TextAnnotation,
    collect_annotation_pool,
    is_contaminant_for_beam,
)
from src.extractor.detail_validator import validate_detail_blocks
from src.extractor.sketch_validator import validate_sketch
from src.geometry.geometry_graph import GeometryGraphBuilder, expand_sketch_bbox
from src.utils.entities_loader import load_entities_json

DETAIL_LABEL_LAYER = "SEC TEXT"

DetailStatus = Literal["VALID", "SKETCH_NOT_FOUND", "INCOMPLETE_DETAIL"]


class DetailBbox(TypedDict):
    xmin: float
    ymin: float
    xmax: float
    ymax: float


class ReinforcementDetailBlock(TypedDict, total=False):
    beam_mark: str
    beam_width: int
    beam_depth: int
    status: DetailStatus
    bbox: DetailBbox
    annotation_count: int
    texts: List[TextAnnotation]


class ReinforcementDetailSummary(TypedDict):
    total_blocks: int
    total_annotations: int
    annotations_per_beam: Dict[str, int]


class ReinforcementDetailExtractor:
    """Extract reinforcement details with sketch validation and ownership assignment."""

    def __init__(self) -> None:
        self._geometry_builder = GeometryGraphBuilder()

    def extract(
        self,
        entities_path: Path,
        dxf_path: Path,
        beam_labels_path: Path | None = None,
    ) -> List[ReinforcementDetailBlock]:
        entities = load_entities_json(entities_path)
        doc = self._read_dxf(dxf_path)
        headers = self._find_headers(entities, beam_labels_path)

        sketch_targets: List[SketchTarget] = []
        marks_with_valid_sketch: set[str] = set()
        header_meta: Dict[str, dict[str, Any]] = {}
        sketch_bboxes: Dict[str, DetailBbox] = {}

        for header in headers:
            mark = header["beam_mark"]
            header_meta[mark] = header

            sketch = self._geometry_builder.build_sketch(
                doc, header["x"], header["y"]
            )
            valid, reason = validate_sketch(sketch)
            if not valid:
                logger.warning(
                    "Sketch validation failed for {} at ({}, {}): {}",
                    mark,
                    header["x"],
                    header["y"],
                    reason,
                )
                continue

            expanded = expand_sketch_bbox(sketch.bbox)

            sketch_targets.append(
                SketchTarget(
                    beam_mark=mark,
                    center_x=header["x"],
                    center_y=header["y"],
                    expanded_bbox=expanded,
                    header=header,
                )
            )
            marks_with_valid_sketch.add(mark)

            detail_bbox = DetailBbox(
                xmin=expanded[0],
                ymin=expanded[1],
                xmax=expanded[2],
                ymax=expanded[3],
            )
            if mark in sketch_bboxes:
                sketch_bboxes[mark] = self._merge_bbox(
                    sketch_bboxes[mark], detail_bbox
                )
            else:
                sketch_bboxes[mark] = detail_bbox

        annotation_pool = collect_annotation_pool(entities, doc=doc)
        assigned = assign_annotations(annotation_pool, sketch_targets)

        blocks_by_mark: Dict[str, ReinforcementDetailBlock] = {}

        for mark, header in header_meta.items():
            if mark not in marks_with_valid_sketch:
                blocks_by_mark[mark] = ReinforcementDetailBlock(
                    beam_mark=mark,
                    beam_width=header["beam_width"],
                    beam_depth=header["beam_depth"],
                    status="SKETCH_NOT_FOUND",
                    annotation_count=0,
                    texts=[],
                )
                continue

            texts = self._filter_assigned_texts(assigned.get(mark, []), mark)
            status: DetailStatus = (
                "VALID" if is_detail_complete([t["text"] for t in texts]) else "INCOMPLETE_DETAIL"
            )

            blocks_by_mark[mark] = ReinforcementDetailBlock(
                beam_mark=mark,
                beam_width=header["beam_width"],
                beam_depth=header["beam_depth"],
                status=status,
                bbox=sketch_bboxes[mark],
                annotation_count=len(texts),
                texts=texts,
            )

        blocks = sorted(
            blocks_by_mark.values(),
            key=lambda block: self._beam_mark_sort_key(block["beam_mark"]),
        )
        logger.info("Built {} detail block(s)", len(blocks))
        return blocks

    def _filter_assigned_texts(
        self, texts: List[TextAnnotation], beam_mark: str
    ) -> List[TextAnnotation]:
        filtered: List[TextAnnotation] = []
        for item in texts:
            if is_contaminant_for_beam(item["text"], beam_mark):
                continue
            filtered.append(item)
        return filtered

    def build_summary(
        self, blocks: List[ReinforcementDetailBlock]
    ) -> ReinforcementDetailSummary:
        return ReinforcementDetailSummary(
            total_blocks=len(blocks),
            total_annotations=sum(
                block.get("annotation_count", len(block.get("texts", [])))
                for block in blocks
            ),
            annotations_per_beam={
                block["beam_mark"]: block.get(
                    "annotation_count", len(block.get("texts", []))
                )
                for block in blocks
            },
        )

    def log_summary(self, summary: ReinforcementDetailSummary) -> None:
        logger.info("--- Detail Extraction Summary ---")
        logger.info("Total blocks: {}", summary["total_blocks"])
        logger.info("Total annotations: {}", summary["total_annotations"])
        for mark, count in sorted(
            summary["annotations_per_beam"].items(),
            key=lambda item: self._beam_mark_sort_key(item[0]),
        ):
            logger.info("  {}: {} annotation(s)", mark, count)

    def validate(self, blocks: List[ReinforcementDetailBlock]) -> dict:
        return validate_detail_blocks(blocks)

    def _read_dxf(self, dxf_path: Path) -> Any:
        path = Path(dxf_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"DXF file not found: {path}")
        doc, auditor = recover.readfile(str(path))
        if auditor.has_errors:
            logger.warning("DXF auditor reported errors in {}", path.name)
        return doc

    def _find_headers(
        self,
        entities: List[dict[str, Any]],
        beam_labels_path: Path | None,
    ) -> List[dict[str, Any]]:
        headers: List[dict[str, Any]] = []

        for entity in entities:
            if entity.get("entity_type") not in {"TEXT", "MTEXT"}:
                continue
            if entity.get("layer") != DETAIL_LABEL_LAYER:
                continue
            text = str(entity.get("clean_text", "")).strip()
            match = BEAM_LABEL_PATTERN.match(text)
            if not match:
                continue
            headers.append(
                {
                    "beam_mark": match.group(1).upper(),
                    "beam_width": int(match.group(2)),
                    "beam_depth": int(match.group(3)),
                    "x": float(entity["x"]),
                    "y": float(entity["y"]),
                    "handle": str(entity.get("handle", "")),
                }
            )

        if headers:
            logger.info("Found {} beam detail label(s) in entities", len(headers))
            return headers

        if beam_labels_path is None:
            logger.warning("No beam labels found in entities")
            return []

        path = Path(beam_labels_path).resolve()
        with path.open(encoding="utf-8") as fh:
            labels = json.load(fh)

        for label in labels:
            headers.append(
                {
                    "beam_mark": str(label["beam_mark"]).upper(),
                    "beam_width": int(label["width_mm"]),
                    "beam_depth": int(label["depth_mm"]),
                    "x": float(label["x"]),
                    "y": float(label["y"]),
                    "handle": "",
                }
            )

        logger.info("Loaded {} beam label(s) from {}", len(headers), path)
        return headers

    @staticmethod
    def _merge_bbox(first: DetailBbox, second: DetailBbox) -> DetailBbox:
        return DetailBbox(
            xmin=round(min(first["xmin"], second["xmin"]), 6),
            ymin=round(min(first["ymin"], second["ymin"]), 6),
            xmax=round(max(first["xmax"], second["xmax"]), 6),
            ymax=round(max(first["ymax"], second["ymax"]), 6),
        )

    @staticmethod
    def _beam_mark_sort_key(mark: str) -> Tuple[int, str]:
        match = re.match(r"^B(\d+)$", mark, re.IGNORECASE)
        if match:
            return (int(match.group(1)), mark)
        return (0, mark)
