"""Property parser summary — Phase G.5.3.1."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Set

from src.property_parser.property_parser_types import (
    PARSE_STATUS_PARSED,
    PARSE_STATUS_UNPARSED,
)


class PropertyParserSummary:
    """Build project-level property parser summary."""

    @staticmethod
    def build(
        candidates: List[dict[str, Any]],
        properties: List[dict[str, Any]],
        unparsed_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        by_type: Dict[str, int] = {}
        parsed_count = 0
        unparsed_count = 0
        confidences: List[float] = []
        object_ids: Set[str] = set()
        candidate_ids: Set[str] = set()
        pattern_counter: Counter[str] = Counter()

        for prop in properties:
            ptype = str(prop.get("property_type", "UNKNOWN"))
            by_type[ptype] = by_type.get(ptype, 0) + 1
            if prop.get("parse_status") == PARSE_STATUS_PARSED:
                parsed_count += 1
            else:
                unparsed_count += 1
            confidences.append(float(prop.get("confidence", 0.0)))
            object_ids.add(str(prop.get("engineering_object_id", "")))
            candidate_ids.add(str(prop.get("candidate_id", "")))
            if prop.get("parse_status") == PARSE_STATUS_PARSED:
                text = str(prop.get("source_text", "")).strip()
                if text:
                    pattern_counter[text] += 1

        unique_candidates = len({c.get("candidate_id") for c in candidates})
        avg_per_candidate = len(properties) / unique_candidates if unique_candidates else 0.0
        avg_per_object = len(properties) / len(object_ids) if object_ids else 0.0

        top_patterns = pattern_counter.most_common(10)

        return {
            "phase": "Phase G.5.3.1",
            "status": "PROPERTIES_PARSED",
            "engineering_object_count": len(object_ids),
            "candidates_processed": len(candidates),
            "properties_created": len(properties),
            "properties_by_type": by_type,
            "parsed_count": parsed_count,
            "unparsed_count": unparsed_count,
            "unparsed_candidate_records": len(unparsed_records),
            "average_parse_confidence": round(
                sum(confidences) / len(confidences) if confidences else 0.0, 4
            ),
            "average_properties_per_candidate": round(avg_per_candidate, 2),
            "average_properties_per_engineering_object": round(avg_per_object, 2),
            "most_common_reinforcement_patterns": [
                {"pattern": pattern, "occurrences": count} for pattern, count in top_patterns
            ],
            "registry_counts": {
                "property_count": registry.get("property_count", 0),
                "candidates_processed": registry.get("candidates_processed", 0),
            },
            "validation_result": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
