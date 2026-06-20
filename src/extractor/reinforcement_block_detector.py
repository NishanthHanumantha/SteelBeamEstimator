"""Detect reinforcement detail blocks using nearest-neighbour header assignment."""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, TypedDict

from loguru import logger

from src.extractor.beam_label_extractor import BEAM_LABEL_PATTERN
from src.utils.entities_loader import load_entities_json

TEXT_ENTITY_TYPES = frozenset({"TEXT", "MTEXT"})

MIN_BEAM_DIMENSION_MM = 1
MAX_BEAM_DIMENSION_MM = 5000


class HeaderPosition(TypedDict):
    """Plan position of a beam label header occurrence."""

    x: float
    y: float


class BlockEntity(TypedDict):
    """TEXT / MTEXT entity assigned to a beam reinforcement block."""

    entity_type: str
    layer: str
    clean_text: str
    handle: str
    x: float
    y: float


class ReinforcementBlock(TypedDict):
    """Merged reinforcement detail block for one unique beam mark."""

    beam_mark: str
    beam_width: int
    beam_depth: int
    header_positions: List[HeaderPosition]
    entities: List[BlockEntity]


class ReinforcementBlockSummary(TypedDict):
    """Summary statistics for reinforcement block detection."""

    total_unique_beam_marks: int
    total_reinforcement_blocks: int
    duplicate_beam_marks_removed: int
    entities_assigned_per_beam: Dict[str, int]


@dataclass(frozen=True)
class BeamHeader:
    """Single beam label header occurrence in the drawing."""

    beam_mark: str
    beam_width: int
    beam_depth: int
    x: float
    y: float
    handle: str


@dataclass
class BeamTypeGroup:
    """All header occurrences merged under one beam mark."""

    beam_mark: str
    beam_width: int
    beam_depth: int
    header_positions: List[HeaderPosition] = field(default_factory=list)


class ReinforcementBlockDetector:
    """
    Assign TEXT / MTEXT entities to beams by nearest header position,
    then merge into one block per unique beam mark.
    """

    def __init__(
        self,
        header_pattern: re.Pattern[str] = BEAM_LABEL_PATTERN,
    ) -> None:
        self._header_pattern = header_pattern

    def detect(self, entities_path: Path) -> List[ReinforcementBlock]:
        """Load entities and build merged reinforcement blocks."""
        entities = load_entities_json(entities_path)
        text_entities = self._collect_text_entities(entities)
        headers = self._find_headers(entities)

        if not headers:
            logger.warning("No beam detail headers found in entities")

        beam_groups = self._group_headers_by_mark(headers)
        assignments = self._assign_entities_nearest_neighbor(text_entities, headers)
        blocks = self._build_merged_blocks(beam_groups, assignments)
        self._validate_blocks(blocks, len(headers), len(beam_groups))
        return blocks

    def build_summary(
        self,
        blocks: List[ReinforcementBlock],
        total_header_occurrences: int,
    ) -> ReinforcementBlockSummary:
        entities_per_beam = {
            block["beam_mark"]: len(block["entities"]) for block in blocks
        }
        unique_marks = len(blocks)
        duplicate_removed = max(total_header_occurrences - unique_marks, 0)

        return ReinforcementBlockSummary(
            total_unique_beam_marks=unique_marks,
            total_reinforcement_blocks=len(blocks),
            duplicate_beam_marks_removed=duplicate_removed,
            entities_assigned_per_beam=entities_per_beam,
        )

    def log_summary(self, summary: ReinforcementBlockSummary) -> None:
        logger.info("--- Reinforcement Block Detection Summary ---")
        logger.info("Total unique beam marks: {}", summary["total_unique_beam_marks"])
        logger.info(
            "Total reinforcement blocks: {}",
            summary["total_reinforcement_blocks"],
        )
        logger.info(
            "Duplicate beam marks removed: {}",
            summary["duplicate_beam_marks_removed"],
        )
        logger.info("Entities assigned per beam:")
        for mark in sorted(
            summary["entities_assigned_per_beam"],
            key=self._beam_mark_sort_key,
        ):
            logger.info(
                "  {}: {}",
                mark,
                summary["entities_assigned_per_beam"][mark],
            )

    def _group_headers_by_mark(
        self, headers: List[BeamHeader]
    ) -> Dict[str, BeamTypeGroup]:
        groups: Dict[str, BeamTypeGroup] = {}

        for header in headers:
            if header.beam_mark not in groups:
                groups[header.beam_mark] = BeamTypeGroup(
                    beam_mark=header.beam_mark,
                    beam_width=header.beam_width,
                    beam_depth=header.beam_depth,
                )
            else:
                group = groups[header.beam_mark]
                if (
                    group.beam_width != header.beam_width
                    or group.beam_depth != header.beam_depth
                ):
                    logger.warning(
                        "Beam mark {} has conflicting section sizes: "
                        "{}x{} vs {}x{} — keeping first occurrence",
                        header.beam_mark,
                        group.beam_width,
                        group.beam_depth,
                        header.beam_width,
                        header.beam_depth,
                    )

            groups[header.beam_mark].header_positions.append(
                HeaderPosition(x=header.x, y=header.y)
            )

        logger.info(
            "Grouped {} header occurrence(s) into {} unique beam mark(s)",
            len(headers),
            len(groups),
        )
        return groups

    def _assign_entities_nearest_neighbor(
        self,
        text_entities: List[dict[str, Any]],
        headers: List[BeamHeader],
    ) -> Dict[str, List[BlockEntity]]:
        assignments: Dict[str, List[BlockEntity]] = {
            mark: [] for mark in {header.beam_mark for header in headers}
        }

        if not headers:
            return assignments

        for entity in text_entities:
            text_x = float(entity["x"])
            text_y = float(entity["y"])

            nearest_header = min(
                headers,
                key=lambda header: self._distance(
                    text_x, text_y, header.x, header.y
                ),
            )

            block_entity = self._to_block_entity(entity)
            if self._is_beam_header_text(block_entity["clean_text"]):
                logger.debug(
                    "Skipping beam header text '{}' at ({}, {})",
                    block_entity["clean_text"],
                    text_x,
                    text_y,
                )
                continue

            assignments[nearest_header.beam_mark].append(block_entity)

        for mark, entities in assignments.items():
            entities.sort(key=lambda item: (item["y"], item["x"], item["handle"]))
            logger.debug(
                "Nearest-neighbour assignment: {} → {} reinforcement entit(y/ies)",
                mark,
                len(entities),
            )

        return assignments

    def _build_merged_blocks(
        self,
        beam_groups: Dict[str, BeamTypeGroup],
        assignments: Dict[str, List[BlockEntity]],
    ) -> List[ReinforcementBlock]:
        blocks: List[ReinforcementBlock] = []

        for mark in sorted(beam_groups.keys(), key=self._beam_mark_sort_key):
            group = beam_groups[mark]
            blocks.append(
                ReinforcementBlock(
                    beam_mark=group.beam_mark,
                    beam_width=group.beam_width,
                    beam_depth=group.beam_depth,
                    header_positions=group.header_positions,
                    entities=assignments.get(mark, []),
                )
            )

        return blocks

    def _collect_text_entities(
        self, entities: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        text_entities: List[dict[str, Any]] = []

        for index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                logger.warning("Skipping non-dict entity at index {}", index)
                continue

            entity_type = entity.get("entity_type")
            if entity_type not in TEXT_ENTITY_TYPES:
                continue

            x = self._parse_coordinate(entity, "x", index)
            y = self._parse_coordinate(entity, "y", index)
            entity_copy = dict(entity)
            entity_copy["x"] = x
            entity_copy["y"] = y
            text_entities.append(entity_copy)

        logger.info(
            "Collected {} TEXT / MTEXT entities for nearest-neighbour assignment",
            len(text_entities),
        )
        return text_entities

    def _find_headers(self, entities: List[dict[str, Any]]) -> List[BeamHeader]:
        headers: List[BeamHeader] = []

        for index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                continue

            if entity.get("entity_type") not in TEXT_ENTITY_TYPES:
                continue

            clean_text = entity.get("clean_text")
            if clean_text is None:
                logger.warning(
                    "TEXT/MTEXT entity at index {} missing 'clean_text' — skipped",
                    index,
                )
                continue

            text = str(clean_text).strip()
            match = self._header_pattern.match(text)
            if not match:
                continue

            beam_mark = match.group(1).upper()
            beam_width = int(match.group(2))
            beam_depth = int(match.group(3))

            if not self._validate_dimensions(beam_mark, beam_width, beam_depth):
                continue

            headers.append(
                BeamHeader(
                    beam_mark=beam_mark,
                    beam_width=beam_width,
                    beam_depth=beam_depth,
                    x=self._parse_coordinate(entity, "x", index),
                    y=self._parse_coordinate(entity, "y", index),
                    handle=str(entity.get("handle", "")),
                )
            )

        logger.info("Found {} beam detail header occurrence(s)", len(headers))
        return headers

    def _is_beam_header_text(self, clean_text: str) -> bool:
        return bool(self._header_pattern.match(str(clean_text).strip()))

    def _to_block_entity(self, entity: dict[str, Any]) -> BlockEntity:
        clean_text = entity.get("clean_text")
        return BlockEntity(
            entity_type=str(entity.get("entity_type", "")),
            layer=str(entity.get("layer", "")),
            clean_text=str(clean_text) if clean_text is not None else "",
            handle=str(entity.get("handle", "")),
            x=float(entity["x"]),
            y=float(entity["y"]),
        )

    def _validate_dimensions(
        self, beam_mark: str, beam_width: int, beam_depth: int
    ) -> bool:
        if not (
            MIN_BEAM_DIMENSION_MM <= beam_width <= MAX_BEAM_DIMENSION_MM
            and MIN_BEAM_DIMENSION_MM <= beam_depth <= MAX_BEAM_DIMENSION_MM
        ):
            logger.warning(
                "Invalid beam dimensions for header {}: {}x{} mm — skipped",
                beam_mark,
                beam_width,
                beam_depth,
            )
            return False
        return True

    def _validate_blocks(
        self,
        blocks: List[ReinforcementBlock],
        total_headers: int,
        unique_marks: int,
    ) -> None:
        empty_blocks = [block["beam_mark"] for block in blocks if not block["entities"]]
        if empty_blocks:
            logger.warning(
                "{} block(s) have no assigned reinforcement entities: {}",
                len(empty_blocks),
                ", ".join(empty_blocks),
            )

        logger.info(
            "Merged {} header occurrence(s) into {} block(s) "
            "({} duplicate mark occurrence(s) removed)",
            total_headers,
            len(blocks),
            max(total_headers - unique_marks, 0),
        )

        for block in blocks:
            header_texts = [
                entity["clean_text"]
                for entity in block["entities"]
                if self._is_beam_header_text(entity["clean_text"])
            ]
            if header_texts:
                logger.error(
                    "Block {} still contains beam header text(s): {}",
                    block["beam_mark"],
                    header_texts,
                )

    @staticmethod
    def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
        return math.hypot(x1 - x2, y1 - y2)

    @staticmethod
    def _beam_mark_sort_key(mark: str) -> Tuple[int, str]:
        match = re.match(r"^B(\d+)$", mark, re.IGNORECASE)
        if match:
            return (int(match.group(1)), mark)
        return (0, mark)

    def _parse_coordinate(
        self, entity: dict[str, Any], field: str, index: int
    ) -> float:
        value = entity.get(field)
        if value is None:
            logger.warning(
                "Entity at index {} missing '{}' — using 0.0",
                index,
                field,
            )
            return 0.0

        try:
            return round(float(value), 6)
        except (TypeError, ValueError):
            logger.warning(
                "Entity at index {} has invalid '{}' value: {} — using 0.0",
                index,
                field,
                value,
            )
            return 0.0
