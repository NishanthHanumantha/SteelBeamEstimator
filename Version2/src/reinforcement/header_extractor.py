"""Phase B — extract beam header labels from reinforcement detail DXF."""

from pathlib import Path
from typing import List, Optional, TypedDict

from loguru import logger

from src.extractor.beam_label_extractor import BEAM_LABEL_PATTERN, BeamLabelExtractor
from src.framing.beam_geometry import beam_mark_sort_key
from src.parser.dxf_reader import DxfReader
from src.parser.entity_extractor import EntityExtractor

TEXT_ENTITY_TYPES = frozenset({"TEXT", "MTEXT"})


class ReinforcementHeader(TypedDict):
    beam_mark: str
    width_mm: int
    depth_mm: int
    x: float
    y: float


class ReinforcementHeaderExtractor:
    """Detect B{n}(WxD) headers in reinforcement detail drawings."""

    def __init__(self) -> None:
        self._label_extractor = BeamLabelExtractor()

    def extract_from_dxf(self, dxf_path: Path) -> List[ReinforcementHeader]:
        reader = DxfReader(dxf_path)
        doc = reader.read()
        modelspace = reader.get_modelspace(doc)
        if modelspace is None:
            return []

        entities = EntityExtractor().extract(modelspace)
        return self.extract_from_entities(entities)

    def extract_from_entities(
        self, entities: List[dict]
    ) -> List[ReinforcementHeader]:
        raw_labels = self._label_extractor.extract_from_entities(entities)
        headers = [
            ReinforcementHeader(
                beam_mark=label["beam_mark"],
                width_mm=label["width_mm"],
                depth_mm=label["depth_mm"],
                x=label["x"],
                y=label["y"],
            )
            for label in raw_labels
        ]
        return headers

    def extract_from_directory(self, reinforcement_dir: Path) -> List[ReinforcementHeader]:
        dxf_files = sorted(reinforcement_dir.glob("*.dxf"))
        if not dxf_files:
            logger.warning("No DXF files in {}", reinforcement_dir)
            return []

        all_headers: List[ReinforcementHeader] = []
        for dxf_path in dxf_files:
            logger.info("Extracting reinforcement headers from {}", dxf_path.name)
            all_headers.extend(self.extract_from_dxf(dxf_path))

        return all_headers

    def dedupe_headers(
        self, headers: List[ReinforcementHeader]
    ) -> List[ReinforcementHeader]:
        """Keep one header per beam mark (leftmost x, then lowest y)."""
        by_mark: dict[str, ReinforcementHeader] = {}
        for header in headers:
            mark = header["beam_mark"]
            if mark not in by_mark:
                by_mark[mark] = header
                continue
            existing = by_mark[mark]
            if (header["x"], header["y"]) < (existing["x"], existing["y"]):
                by_mark[mark] = header

        return sorted(by_mark.values(), key=lambda h: beam_mark_sort_key(h["beam_mark"]))

    def to_output_records(
        self, headers: List[ReinforcementHeader], *, dedupe: bool = True
    ) -> List[ReinforcementHeader]:
        if dedupe:
            return self.dedupe_headers(headers)
        return sorted(headers, key=lambda h: beam_mark_sort_key(h["beam_mark"]))
