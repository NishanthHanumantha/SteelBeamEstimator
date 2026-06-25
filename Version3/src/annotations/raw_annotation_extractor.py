"""Phase D.1 — extract raw TEXT/MTEXT inside owned sketch regions."""

import math
from typing import Any, Dict, List, Tuple, TypedDict

from ezdxf.entities.dxfgfx import DXFGraphic
from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.grid.beam_cell_builder import ROW_Y_TOLERANCE_MM
from src.parser.dxf_flattener import flatten_entities
from src.parser.dxf_reader import DxfReader

BBOX_MARGIN_MM = 300.0
ROW_EDGE_MARGIN_MM = 5000.0
_TEXT_TYPES = frozenset({"TEXT", "MTEXT"})
_EXCLUDED_LAYERS = frozenset({"SEC TEXT"})


class RawTextItem(TypedDict):
    text: str
    x: float
    y: float


class RawAnnotationRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    annotation_count: int
    texts: List[RawTextItem]


class OwnedSketchRef(TypedDict):
    beam_mark: str
    occurrence_id: int
    sketch_id: str


class _SketchContext(TypedDict):
    ref: OwnedSketchRef
    sketch: dict[str, Any]
    centroid_x: float
    centroid_y: float


class RawAnnotationExtractor:
    """Collect raw TEXT/MTEXT for each owned sketch."""

    def extract_from_dxf(
        self,
        dxf_path: str,
        ownership: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
    ) -> List[RawAnnotationRecord]:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}
        owned_refs = self._owned_sketch_refs(ownership)
        occurrence_columns = self._occurrence_column_bounds(occurrences)
        text_entities = self._load_text_entities(dxf_path)

        occurrence_groups = self._group_by_occurrence(owned_refs, sketch_lookup)
        texts_by_sketch: Dict[str, List[RawTextItem]] = {
            ref["sketch_id"]: [] for ref in owned_refs
        }

        for group_key, contexts in occurrence_groups.items():
            mark, occurrence_id = group_key
            col_bounds = occurrence_columns.get(group_key)
            if col_bounds is None or not contexts:
                continue

            search_bbox = self._occurrence_search_bbox(contexts, col_bounds)
            candidates = self._texts_in_bbox(text_entities, search_bbox)
            for text, x, y in candidates:
                nearest = min(
                    contexts,
                    key=lambda ctx: self._distance(ctx["centroid_x"], ctx["centroid_y"], x, y),
                )
                texts_by_sketch[nearest["ref"]["sketch_id"]].append(
                    RawTextItem(text=text, x=x, y=y)
                )

        records: List[RawAnnotationRecord] = []
        for ref in owned_refs:
            texts = texts_by_sketch[ref["sketch_id"]]
            texts.sort(key=lambda item: (-item["y"], item["x"], item["text"]))
            records.append(
                RawAnnotationRecord(
                    beam_mark=ref["beam_mark"],
                    occurrence_id=ref["occurrence_id"],
                    sketch_id=ref["sketch_id"],
                    annotation_count=len(texts),
                    texts=texts,
                )
            )

        logger.info(
            "Extracted {} raw annotation(s) across {} owned sketch(es)",
            sum(record["annotation_count"] for record in records),
            len(records),
        )
        return records

    def _group_by_occurrence(
        self,
        owned_refs: List[OwnedSketchRef],
        sketch_lookup: Dict[str, dict[str, Any]],
    ) -> Dict[Tuple[str, int], List[_SketchContext]]:
        groups: Dict[Tuple[str, int], List[_SketchContext]] = {}
        for ref in owned_refs:
            sketch = sketch_lookup.get(ref["sketch_id"])
            if sketch is None:
                continue
            bbox = sketch["bbox"]
            cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
            cy = (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0
            key = (ref["beam_mark"], ref["occurrence_id"])
            groups.setdefault(key, []).append(
                _SketchContext(
                    ref=ref,
                    sketch=sketch,
                    centroid_x=cx,
                    centroid_y=cy,
                )
            )
        return groups

    def _occurrence_search_bbox(
        self,
        contexts: List[_SketchContext],
        col_bounds: Tuple[float, float],
    ) -> Tuple[float, float, float, float]:
        col_xmin, col_xmax = col_bounds
        sketch_xmin = min(float(ctx["sketch"]["bbox"]["xmin"]) for ctx in contexts)
        sketch_xmax = max(float(ctx["sketch"]["bbox"]["xmax"]) for ctx in contexts)
        sketch_ymin = min(float(ctx["sketch"]["bbox"]["ymin"]) for ctx in contexts)
        sketch_ymax = max(float(ctx["sketch"]["bbox"]["ymax"]) for ctx in contexts)
        header_y = min(float(ctx["sketch"].get("header_y", sketch_ymin)) for ctx in contexts)

        xmin = min(sketch_xmin - BBOX_MARGIN_MM, col_xmin - BBOX_MARGIN_MM)
        xmax = max(sketch_xmax + BBOX_MARGIN_MM, col_xmax + BBOX_MARGIN_MM)
        ymin = min(sketch_ymin - BBOX_MARGIN_MM, header_y - BBOX_MARGIN_MM)
        ymax = sketch_ymax + BBOX_MARGIN_MM
        return xmin, ymin, xmax, ymax

    def _occurrence_column_bounds(
        self, occurrences: List[dict[str, Any]]
    ) -> Dict[Tuple[str, int], Tuple[float, float]]:
        rows = self._cluster_occurrence_rows(occurrences)
        bounds: Dict[Tuple[str, int], Tuple[float, float]] = {}

        for row in rows:
            sorted_row = sorted(row, key=lambda occ: occ["x"])
            for index, occurrence in enumerate(sorted_row):
                if index == 0:
                    xmin = occurrence["x"] - ROW_EDGE_MARGIN_MM
                else:
                    xmin = (sorted_row[index - 1]["x"] + occurrence["x"]) / 2.0

                if index == len(sorted_row) - 1:
                    xmax = occurrence["x"] + ROW_EDGE_MARGIN_MM
                else:
                    xmax = (occurrence["x"] + sorted_row[index + 1]["x"]) / 2.0

                key = (occurrence["beam_mark"], int(occurrence["occurrence_id"]))
                bounds[key] = (xmin, xmax)

        return bounds

    def _cluster_occurrence_rows(
        self, occurrences: List[dict[str, Any]]
    ) -> List[List[dict[str, Any]]]:
        sorted_occurrences = sorted(
            occurrences,
            key=lambda occ: (-float(occ["y"]), float(occ["x"])),
        )
        rows: List[List[dict[str, Any]]] = []
        for occurrence in sorted_occurrences:
            placed = False
            for row in rows:
                row_y = sum(float(item["y"]) for item in row) / len(row)
                if abs(float(occurrence["y"]) - row_y) <= ROW_Y_TOLERANCE_MM:
                    row.append(occurrence)
                    placed = True
                    break
            if not placed:
                rows.append([occurrence])
        return rows

    def _owned_sketch_refs(
        self, ownership: List[dict[str, Any]]
    ) -> List[OwnedSketchRef]:
        refs: List[OwnedSketchRef] = []
        for record in ownership:
            mark = str(record["beam_mark"])
            occurrence_id = int(record["occurrence_id"])
            for owned in record.get("owned_sketches", []):
                if isinstance(owned, dict):
                    sketch_id = str(owned["sketch_id"])
                else:
                    sketch_id = str(owned)
                refs.append(
                    OwnedSketchRef(
                        beam_mark=mark,
                        occurrence_id=occurrence_id,
                        sketch_id=sketch_id,
                    )
                )
        refs.sort(
            key=lambda ref: (
                beam_mark_sort_key(ref["beam_mark"]),
                ref["occurrence_id"],
                self._sketch_sort_key(ref["sketch_id"]),
            )
        )
        return refs

    def _load_text_entities(self, dxf_path: str) -> List[Tuple[str, float, float]]:
        doc = DxfReader(dxf_path).read()
        flat = flatten_entities(doc.modelspace())
        entities: List[Tuple[str, float, float]] = []

        for entity in flat:
            try:
                item = self._text_entity_to_tuple(entity)
                if item is not None:
                    entities.append(item)
            except Exception as exc:
                handle = getattr(entity.dxf, "handle", "unknown")
                logger.warning(
                    "Skipped text entity handle={} type={}: {}",
                    handle,
                    entity.dxftype(),
                    exc,
                )

        logger.info(
            "Loaded {} TEXT/MTEXT entity(ies) from DXF (INSERT blocks expanded)",
            len(entities),
        )
        return entities

    def _text_entity_to_tuple(self, entity: DXFGraphic) -> Tuple[str, float, float] | None:
        entity_type = entity.dxftype()
        if entity_type not in _TEXT_TYPES:
            return None

        layer = str(entity.dxf.layer)
        if layer in _EXCLUDED_LAYERS:
            return None

        insert = entity.dxf.insert
        x = round(float(insert.x), 1)
        y = round(float(insert.y), 1)

        if entity_type == "TEXT":
            text = str(entity.dxf.text)
        else:
            text = str(entity.text)

        if not text:
            return None
        return text, x, y

    def _texts_in_bbox(
        self,
        text_entities: List[Tuple[str, float, float]],
        bbox: Tuple[float, float, float, float],
    ) -> List[Tuple[str, float, float]]:
        xmin, ymin, xmax, ymax = bbox
        matches: List[Tuple[str, float, float]] = []
        for text, x, y in text_entities:
            if xmin <= x <= xmax and ymin <= y <= ymax:
                matches.append((text, x, y))
        return matches

    @staticmethod
    def _distance(cx: float, cy: float, x: float, y: float) -> float:
        return math.hypot(cx - x, cy - y)

    @staticmethod
    def _sketch_sort_key(sketch_id: str) -> Tuple[str, int]:
        if "_S" in sketch_id:
            mark, suffix = sketch_id.rsplit("_S", maxsplit=1)
            try:
                return (mark, int(suffix))
            except ValueError:
                pass
        return (sketch_id, 0)
