"""Build drawing region analysis report."""

from collections import Counter, defaultdict
from typing import Any, Dict, List

from loguru import logger

from src.regions.anchor_detector import DrawingAnchor
from src.regions.constants import REGION_TYPES
from src.regions.text_normalizer import normalize_drawing_text

TOP_TEXT_LIMIT = 20


class RegionReportBuilder:
    """Generate summary report for drawing region detection."""

    def build(
        self,
        regions: List[dict],
        anchors: List[DrawingAnchor],
        entities: List[dict[str, Any]],
        assignments: Dict[str, str],
    ) -> dict[str, Any]:
        entity_lookup = {
            str(entity.get("handle", "")): entity for entity in entities
        }

        counts = Counter(assignments.values())
        region_names = sorted(
            {region["region_type"] for region in regions},
            key=lambda name: REGION_TYPES.index(name)
            if name in REGION_TYPES
            else len(REGION_TYPES),
        )

        texts_by_region: Dict[str, List[str]] = defaultdict(list)
        for handle, region in assignments.items():
            entity = entity_lookup.get(handle)
            if entity is None:
                continue
            if entity.get("entity_type") not in {"TEXT", "MTEXT"}:
                continue
            text = normalize_drawing_text(str(entity.get("clean_text", "")))
            if text:
                texts_by_region[region].append(text)

        top_texts: Dict[str, List[str]] = {}
        for region, texts in texts_by_region.items():
            frequency = Counter(texts)
            top_texts[region] = [
                text for text, _ in frequency.most_common(TOP_TEXT_LIMIT)
            ]

        report = {
            "total_regions": len(regions),
            "region_names": region_names,
            "entity_count_per_region": dict(counts),
            "top_texts_per_region": top_texts,
            "anchors_detected": len(anchors),
            "anchor_summary": [
                {
                    "anchor_type": anchor["anchor_type"],
                    "text": anchor["text"],
                    "confidence": anchor["confidence"],
                    "x": anchor["x"],
                    "y": anchor["y"],
                }
                for anchor in anchors
            ],
            "regions": regions,
        }

        logger.info("Report: {} regions, {} assigned entities", len(regions), len(assignments))
        return report
