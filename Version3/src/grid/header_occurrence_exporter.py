"""Phase C.5 — capture all reinforcement header occurrences (no deduplication)."""

from pathlib import Path
from typing import Any, List, TypedDict

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.parser.dxf_reader import DxfReader
from src.parser.entity_extractor import EntityExtractor
from src.extractor.reinforcement_detail_extractor import ReinforcementDetailExtractor


class HeaderOccurrenceRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    x: float
    y: float


class HeaderOccurrenceExporter:
    """Export every SEC TEXT beam label occurrence from reinforcement DXF."""

    def extract_from_dxf(self, dxf_path: Path) -> List[HeaderOccurrenceRecord]:
        reader = DxfReader(dxf_path)
        doc = reader.read()
        modelspace = reader.get_modelspace(doc)
        if modelspace is None:
            return []

        entities = EntityExtractor().extract(modelspace)
        raw_headers = ReinforcementDetailExtractor()._find_headers(entities, None)
        return self.build_occurrences(raw_headers)

    def build_occurrences(
        self, raw_headers: List[dict[str, Any]]
    ) -> List[HeaderOccurrenceRecord]:
        """Assign occurrence_id per beam mark (1..N), sorted top-to-bottom then left-to-right."""
        sorted_headers = sorted(
            raw_headers,
            key=lambda item: (
                -float(item["y"]),
                float(item["x"]),
                beam_mark_sort_key(str(item["beam_mark"])),
            ),
        )

        per_mark_counter: dict[str, int] = {}
        records: List[HeaderOccurrenceRecord] = []

        for header in sorted_headers:
            mark = str(header["beam_mark"]).upper()
            per_mark_counter[mark] = per_mark_counter.get(mark, 0) + 1
            records.append(
                HeaderOccurrenceRecord(
                    beam_mark=mark,
                    occurrence_id=per_mark_counter[mark],
                    x=round(float(header["x"]), 3),
                    y=round(float(header["y"]), 3),
                )
            )

        logger.info(
            "Captured {} header occurrence(s) across {} beam mark(s)",
            len(records),
            len(per_mark_counter),
        )
        return records

    def extract_from_entities(
        self, entities: List[dict[str, Any]]
    ) -> List[HeaderOccurrenceRecord]:
        raw_headers = ReinforcementDetailExtractor()._find_headers(entities, None)
        return self.build_occurrences(raw_headers)
