"""Beam label extraction from parsed DXF entities."""

import re
from collections import Counter
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple, TypedDict

from loguru import logger

from src.utils.entities_loader import EntitiesLoadError, load_entities_json

BEAM_LABEL_PATTERN = re.compile(r"^(B\d+)\((\d+)X(\d+)\)$", re.IGNORECASE)

MIN_BEAM_DIMENSION_MM = 1
MAX_BEAM_DIMENSION_MM = 5000


class BeamLabel(TypedDict):
    """Single beam label with plan position."""

    beam_mark: str
    width_mm: int
    depth_mm: int
    x: float
    y: float


class BeamLabelSummary(TypedDict):
    """Aggregated statistics for extracted beam labels."""

    total_beams_found: int
    unique_beam_sizes: List[str]
    beam_count_by_size: dict[str, int]


class BeamLabelValidationError(EntitiesLoadError):
    """Raised when input entities data is invalid or unreadable."""


class BeamLabelExtractor:
    """Identify beam labels in entities.json using cleaned text only."""

    def __init__(self, pattern: re.Pattern[str] = BEAM_LABEL_PATTERN) -> None:
        self._pattern = pattern

    def load_entities(self, entities_path: Path) -> List[dict[str, Any]]:
        """Load and validate the entities JSON payload."""
        return load_entities_json(entities_path)

    def extract_from_entities(
        self, entities: List[dict[str, Any]]
    ) -> List[BeamLabel]:
        """Parse beam labels from entity records."""
        labels: List[BeamLabel] = []
        skipped_empty = 0
        skipped_no_match = 0

        for index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                logger.warning("Skipping non-dict entity at index {}", index)
                continue

            clean_text = entity.get("clean_text")
            if clean_text is None:
                logger.warning(
                    "Entity at index {} missing 'clean_text' field — skipped",
                    index,
                )
                continue

            text = str(clean_text).strip()
            if not text:
                skipped_empty += 1
                continue

            match = self._pattern.match(text)
            if not match:
                skipped_no_match += 1
                continue

            beam_mark = match.group(1).upper()
            width_mm = int(match.group(2))
            depth_mm = int(match.group(3))

            if not self._validate_dimensions(beam_mark, width_mm, depth_mm):
                continue

            x = self._parse_coordinate(entity, "x", index)
            y = self._parse_coordinate(entity, "y", index)

            labels.append(
                BeamLabel(
                    beam_mark=beam_mark,
                    width_mm=width_mm,
                    depth_mm=depth_mm,
                    x=x,
                    y=y,
                )
            )

        logger.info(
            "Matched {} beam labels ({} empty, {} non-matching text entities)",
            len(labels),
            skipped_empty,
            skipped_no_match,
        )
        return labels

    def extract(self, entities_path: Path) -> List[BeamLabel]:
        """Load entities and return deduplicated beam labels."""
        entities = self.load_entities(entities_path)
        labels = self.extract_from_entities(entities)
        labels = self.deduplicate(labels)
        self._validate_mark_conflicts(labels)
        return labels

    def deduplicate(self, labels: List[BeamLabel]) -> List[BeamLabel]:
        """Remove duplicate labels with identical mark, size, and position."""
        seen: Set[Tuple[str, int, int, float, float]] = set()
        unique: List[BeamLabel] = []

        for label in labels:
            key = (
                label["beam_mark"],
                label["width_mm"],
                label["depth_mm"],
                label["x"],
                label["y"],
            )
            if key in seen:
                logger.debug(
                    "Duplicate beam label removed: {} ({}x{}) at ({}, {})",
                    label["beam_mark"],
                    label["width_mm"],
                    label["depth_mm"],
                    label["x"],
                    label["y"],
                )
                continue
            seen.add(key)
            unique.append(label)

        removed = len(labels) - len(unique)
        if removed:
            logger.info("Removed {} duplicate beam label(s)", removed)

        return unique

    def build_summary(self, labels: List[BeamLabel]) -> BeamLabelSummary:
        """Build summary statistics from deduplicated labels."""
        size_counts = Counter(
            f"{label['width_mm']}X{label['depth_mm']}" for label in labels
        )
        unique_sizes = sorted(size_counts.keys(), key=self._size_sort_key)

        return BeamLabelSummary(
            total_beams_found=len(labels),
            unique_beam_sizes=unique_sizes,
            beam_count_by_size=dict(size_counts),
        )

    def log_summary(self, summary: BeamLabelSummary) -> None:
        """Log human-readable extraction summary."""
        logger.info("--- Beam Label Extraction Summary ---")
        logger.info("Total Beams Found: {}", summary["total_beams_found"])
        logger.info(
            "Unique Beam Sizes: {}",
            ", ".join(summary["unique_beam_sizes"]) or "none",
        )
        logger.info("Beam Count by Size:")
        for size, count in sorted(
            summary["beam_count_by_size"].items(),
            key=lambda item: self._size_sort_key(item[0]),
        ):
            logger.info("  {}: {}", size, count)

    def _validate_dimensions(
        self, beam_mark: str, width_mm: int, depth_mm: int
    ) -> bool:
        if not (
            MIN_BEAM_DIMENSION_MM <= width_mm <= MAX_BEAM_DIMENSION_MM
            and MIN_BEAM_DIMENSION_MM <= depth_mm <= MAX_BEAM_DIMENSION_MM
        ):
            logger.warning(
                "Invalid beam dimensions for {}: {}x{} mm — skipped",
                beam_mark,
                width_mm,
                depth_mm,
            )
            return False
        return True

    def _validate_mark_conflicts(self, labels: List[BeamLabel]) -> None:
        """Warn when the same beam mark appears with different section sizes."""
        mark_sizes: dict[str, set[str]] = {}
        for label in labels:
            size = f"{label['width_mm']}X{label['depth_mm']}"
            mark_sizes.setdefault(label["beam_mark"], set()).add(size)

        for mark, sizes in sorted(mark_sizes.items()):
            if len(sizes) > 1:
                logger.warning(
                    "Beam mark {} has conflicting sizes: {}",
                    mark,
                    ", ".join(sorted(sizes)),
                )

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

    @staticmethod
    def _size_sort_key(size: str) -> Tuple[int, int]:
        parts = size.upper().split("X", maxsplit=1)
        if len(parts) != 2:
            return (0, 0)
        try:
            return (int(parts[0]), int(parts[1]))
        except ValueError:
            return (0, 0)
