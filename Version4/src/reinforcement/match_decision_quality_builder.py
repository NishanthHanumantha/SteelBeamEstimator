"""Add quality and algorithm metadata to match decisions."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from loguru import logger

from src.reinforcement.match_decision_quality import (
    ALGORITHM_VERSION,
    DecisionAlgorithmInfo,
    SHARED_ALGORITHM_ID,
    confidence_level_from_value,
    format_decision_quality_id,
    quality_status_from_level,
)


class MatchDecisionQualityBuilder:
    """Enrich match decisions with confidence level and algorithm versioning."""

    def build(
        self,
        decisions: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]]]:
        enriched: List[dict[str, Any]] = []
        relationships: List[dict[str, Any]] = []

        for decision in decisions:
            decision_copy = dict(decision)
            confidence = decision_copy.get("confidence")
            level = confidence_level_from_value(
                float(confidence) if confidence is not None else None
            )
            quality_status = quality_status_from_level(level)
            manual_review = bool(decision_copy.get("requires_manual_review", False))

            algorithm_name = str(decision_copy.get("decision_reason", "DIRECT_LABEL_MATCH"))
            algorithm_info = DecisionAlgorithmInfo(algorithm_name=algorithm_name).to_dict()

            decision_copy["confidence_level"] = level
            decision_copy["algorithm_info"] = algorithm_info
            decision_copy["decision_quality"] = {
                "confidence": confidence,
                "confidence_level": level,
                "quality_status": quality_status,
                "requires_manual_review": manual_review,
            }
            enriched.append(decision_copy)

            decision_id = str(decision_copy.get("decision_id", ""))
            quality_id = format_decision_quality_id(decision_id)
            relationships.append(
                self._rel(decision_id, quality_id, "MATCH_DECISION_HAS_QUALITY")
            )
            relationships.append(
                self._rel(decision_id, SHARED_ALGORITHM_ID, "MATCH_DECISION_GENERATED_BY")
            )

        logger.info("Match decision quality enriched — decisions={}", len(enriched))
        return enriched, relationships

    def _rel(self, source_id: str, target_id: str, relationship: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "type": "ENGINEERING",
        }
