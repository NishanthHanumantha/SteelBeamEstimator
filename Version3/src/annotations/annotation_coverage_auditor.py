"""Phase D.1.6A — audit TEXT/MTEXT coverage inside ownership regions."""

import math
import re
from typing import Any, Dict, List, Literal, Tuple, TypedDict

from loguru import logger

from src.annotations.annotation_region_validator import AnnotationRegionValidator
from src.annotations.annotation_text_cleaner import AnnotationTextCleaner
from src.annotations.raw_annotation_extractor import RawAnnotationExtractor
from src.framing.beam_geometry import beam_mark_sort_key

MATCH_TOLERANCE_MM = 1.0

MissingType = Literal[
    "STIRRUP",
    "ANCHORAGE",
    "DIMENSION",
    "SIDE_FACE_REINF",
    "NOTE",
]


class RegionTextItem(TypedDict):
    raw_text: str
    clean_text: str
    x: float
    y: float


class MissingAnnotation(TypedDict):
    raw_text: str
    clean_text: str
    x: float
    y: float
    type: MissingType


class OccurrenceCoverageRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    region_text_count: int
    owned_annotation_count: int
    missing_annotation_count: int
    missing_annotations: List[MissingAnnotation]


class CoverageSummary(TypedDict):
    total_region_texts: int
    total_owned_annotations: int
    total_missing_annotations: int
    missing_by_type: Dict[str, int]
    dxf_text_entity_count: int
    dxf_stirrup_spacing_count: int
    dxf_anchorage_count: int
    dxf_dimension_count: int
    texts_outside_regions: int


class CoverageValidation(TypedDict):
    total_region_texts: int
    owned_annotations: int
    missing_annotations: int
    coverage_percent: float
    status: str


class AnnotationCoverageAuditor:
    """Compare DXF texts inside ownership regions against reassigned annotations."""

    def __init__(self) -> None:
        self._cleaner = AnnotationTextCleaner()
        self._text_loader = RawAnnotationExtractor()

    def audit(
        self,
        dxf_path: str,
        reassigned: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
    ) -> Tuple[
        List[OccurrenceCoverageRecord],
        CoverageSummary,
        CoverageValidation,
        List[MissingAnnotation],
    ]:
        region_validator = AnnotationRegionValidator()
        regions = region_validator.build_regions(
            ownership, occurrences, sketches, beam_cells
        )
        text_entities = self._text_loader._load_text_entities(dxf_path)
        owned_by_occurrence = self._owned_by_occurrence(reassigned)
        dxf_stats = self._dxf_text_stats(text_entities)

        occurrence_records: List[OccurrenceCoverageRecord] = []
        all_missing: List[MissingAnnotation] = []
        all_region_keys: set[Tuple[str, float, float]] = set()

        for key in sorted(
            regions.keys(),
            key=lambda item: (beam_mark_sort_key(item[0]), item[1]),
        ):
            beam_mark, occurrence_id = key
            region = regions[key]
            region_bbox = self._region_bbox(region)
            region_texts = self._texts_in_region(text_entities, region_bbox)
            for item in region_texts:
                all_region_keys.add(
                    (item["clean_text"], item["x"], item["y"])
                )
            owned_items = owned_by_occurrence.get(key, [])

            missing = self._find_missing(region_texts, owned_items)
            all_missing.extend(missing)

            occurrence_records.append(
                OccurrenceCoverageRecord(
                    beam_mark=beam_mark,
                    occurrence_id=occurrence_id,
                    region_text_count=len(region_texts),
                    owned_annotation_count=len(owned_items),
                    missing_annotation_count=len(missing),
                    missing_annotations=missing,
                )
            )

        summary = self._build_summary(
            occurrence_records, all_missing, text_entities, all_region_keys, dxf_stats
        )
        validation = self._build_validation(summary)

        logger.info(
            "Coverage audit: {} region texts, {} owned, {} missing, {:.1f}% coverage",
            summary["total_region_texts"],
            summary["total_owned_annotations"],
            summary["total_missing_annotations"],
            validation["coverage_percent"],
        )
        return occurrence_records, summary, validation, all_missing

    def build_report_text(
        self,
        occurrence_records: List[OccurrenceCoverageRecord],
        dxf_stats: Dict[str, int],
        limit: int = 50,
    ) -> str:
        missing_entries: List[Tuple[str, int, MissingAnnotation]] = []
        for record in occurrence_records:
            for item in record["missing_annotations"]:
                missing_entries.append(
                    (record["beam_mark"], record["occurrence_id"], item)
                )

        missing_entries.sort(
            key=lambda entry: (
                beam_mark_sort_key(entry[0]),
                entry[1],
                entry[2]["type"],
                -entry[2]["y"],
                entry[2]["x"],
            )
        )

        lines = [
            "======================================================================",
            "Annotation Coverage Audit Report (Phase D.1.6A)",
            "======================================================================",
            "",
            f"DXF TEXT/MTEXT entities (total): {dxf_stats['dxf_text_entity_count']}",
            f"Stirrup spacing patterns (@ / C/C) in DXF: {dxf_stats['dxf_stirrup_spacing_count']}",
            f"Anchorage patterns (Ld) in DXF: {dxf_stats['dxf_anchorage_count']}",
            f"Pure dimension texts in DXF: {dxf_stats['dxf_dimension_count']}",
            "",
            f"Top {min(limit, len(missing_entries))} Missing Annotations",
            "",
        ]

        current_beam = ""
        current_occ = -1
        for beam_mark, occurrence_id, item in missing_entries[:limit]:
            if beam_mark != current_beam or occurrence_id != current_occ:
                lines.append(f"Beam {beam_mark}  Occurrence {occurrence_id}")
                current_beam = beam_mark
                current_occ = occurrence_id
            display = item["clean_text"] or item["raw_text"]
            lines.append(f"  [{item['type']}] {display}  ({item['x']}, {item['y']})")

        lines.append("")
        lines.append("======================================================================")
        return "\n".join(lines) + "\n"

    def _owned_by_occurrence(
        self, reassigned: List[dict[str, Any]]
    ) -> Dict[Tuple[str, int], List[Tuple[str, float, float, str]]]:
        owned: Dict[Tuple[str, int], List[Tuple[str, float, float, str]]] = {}
        for occurrence_record in reassigned:
            beam_mark = str(occurrence_record["beam_mark"])
            occurrence_id = int(occurrence_record["occurrence_id"])
            key = (beam_mark, occurrence_id)
            items: List[Tuple[str, float, float, str]] = []
            for annotation in occurrence_record.get("annotations", []):
                raw_text = str(annotation["text"])
                clean_text = self._cleaner.clean(raw_text)
                x = round(float(annotation["x"]), 1)
                y = round(float(annotation["y"]), 1)
                items.append((clean_text, x, y, raw_text))
            owned[key] = items
        return owned

    def _texts_in_region(
        self,
        text_entities: List[Tuple[str, float, float]],
        bbox: Tuple[float, float, float, float],
    ) -> List[RegionTextItem]:
        xmin, ymin, xmax, ymax = bbox
        region_texts: List[RegionTextItem] = []
        for raw_text, x, y in text_entities:
            if xmin <= x <= xmax and ymin <= y <= ymax:
                clean_text = self._cleaner.clean(raw_text)
                region_texts.append(
                    RegionTextItem(
                        raw_text=raw_text,
                        clean_text=clean_text,
                        x=round(x, 1),
                        y=round(y, 1),
                    )
                )
        return region_texts

    def _find_missing(
        self,
        region_texts: List[RegionTextItem],
        owned_items: List[Tuple[str, float, float, str]],
    ) -> List[MissingAnnotation]:
        missing: List[MissingAnnotation] = []
        for region_item in region_texts:
            if not self._is_owned(region_item, owned_items):
                missing.append(
                    MissingAnnotation(
                        raw_text=region_item["raw_text"],
                        clean_text=region_item["clean_text"],
                        x=region_item["x"],
                        y=region_item["y"],
                        type=self._classify_missing(region_item["clean_text"]),
                    )
                )
        return missing

    def _is_owned(
        self,
        region_item: RegionTextItem,
        owned_items: List[Tuple[str, float, float, str]],
    ) -> bool:
        clean_text = region_item["clean_text"]
        x = region_item["x"]
        y = region_item["y"]
        for owned_clean, owned_x, owned_y, owned_raw in owned_items:
            if clean_text != owned_clean:
                continue
            if math.hypot(x - owned_x, y - owned_y) <= MATCH_TOLERANCE_MM:
                return True
            if clean_text and owned_clean == clean_text:
                if abs(x - owned_x) <= MATCH_TOLERANCE_MM and abs(y - owned_y) <= MATCH_TOLERANCE_MM:
                    return True
        return False

    @staticmethod
    def _classify_missing(clean_text: str) -> MissingType:
        normalized = clean_text.strip()
        upper = normalized.upper()

        if "@" in normalized or "C/C" in upper:
            return "STIRRUP"
        if "LD" in upper:
            return "ANCHORAGE"
        if re.fullmatch(r"\d+", normalized):
            return "DIMENSION"
        if "SIDE FACE" in upper or "SFR" in upper or "S.F.R" in upper:
            return "SIDE_FACE_REINF"
        return "NOTE"

    @staticmethod
    def _region_bbox(region: dict[str, Any]) -> Tuple[float, float, float, float]:
        return (
            float(region["xmin"]),
            float(region["ymin"]),
            float(region["xmax"]),
            float(region["ymax"]),
        )

    def _dxf_text_stats(
        self, text_entities: List[Tuple[str, float, float]]
    ) -> Dict[str, int]:
        stirrup = 0
        anchorage = 0
        dimension = 0
        for raw_text, _, _ in text_entities:
            clean = self._cleaner.clean(raw_text)
            missing_type = self._classify_missing(clean)
            if missing_type == "STIRRUP":
                stirrup += 1
            elif missing_type == "ANCHORAGE":
                anchorage += 1
            elif missing_type == "DIMENSION":
                dimension += 1
        return {
            "dxf_text_entity_count": len(text_entities),
            "dxf_stirrup_spacing_count": stirrup,
            "dxf_anchorage_count": anchorage,
            "dxf_dimension_count": dimension,
        }

    def _build_summary(
        self,
        occurrence_records: List[OccurrenceCoverageRecord],
        all_missing: List[MissingAnnotation],
        text_entities: List[Tuple[str, float, float]],
        all_region_keys: set[Tuple[str, float, float]],
        dxf_stats: Dict[str, int],
    ) -> CoverageSummary:
        total_region = sum(r["region_text_count"] for r in occurrence_records)
        total_owned = sum(r["owned_annotation_count"] for r in occurrence_records)
        missing_by_type: Dict[str, int] = {
            "STIRRUP": 0,
            "ANCHORAGE": 0,
            "DIMENSION": 0,
            "SIDE_FACE_REINF": 0,
            "NOTE": 0,
        }
        for item in all_missing:
            missing_by_type[item["type"]] += 1

        texts_outside = 0
        for raw_text, x, y in text_entities:
            clean = self._cleaner.clean(raw_text)
            key = (clean, round(x, 1), round(y, 1))
            if key not in all_region_keys:
                texts_outside += 1

        return CoverageSummary(
            total_region_texts=total_region,
            total_owned_annotations=total_owned,
            total_missing_annotations=len(all_missing),
            missing_by_type=missing_by_type,
            dxf_text_entity_count=dxf_stats["dxf_text_entity_count"],
            dxf_stirrup_spacing_count=dxf_stats["dxf_stirrup_spacing_count"],
            dxf_anchorage_count=dxf_stats["dxf_anchorage_count"],
            dxf_dimension_count=dxf_stats["dxf_dimension_count"],
            texts_outside_regions=texts_outside,
        )

    def _build_validation(self, summary: CoverageSummary) -> CoverageValidation:
        total = summary["total_region_texts"]
        owned = summary["total_owned_annotations"]
        missing = summary["total_missing_annotations"]
        if total:
            coverage_pct = round(((total - missing) / total) * 100.0, 1)
        else:
            coverage_pct = 100.0

        if coverage_pct >= 95.0:
            status = "PASS"
        elif coverage_pct >= 90.0:
            status = "WARN"
        else:
            status = "FAIL"

        return CoverageValidation(
            total_region_texts=total,
            owned_annotations=owned,
            missing_annotations=missing,
            coverage_percent=coverage_pct,
            status=status,
        )
