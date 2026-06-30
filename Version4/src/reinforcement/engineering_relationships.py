"""Engineering object relationship schema — architecture for G.5+."""

from __future__ import annotations

from typing import Any, FrozenSet, List

REL_BELONGS_TO = "BELONGS_TO"
REL_REFERENCES = "REFERENCES"
REL_CONTAINS = "CONTAINS"
REL_DERIVED_FROM = "DERIVED_FROM"
REL_ANNOTATED_BY = "ANNOTATED_BY"

VALID_RELATIONSHIPS: FrozenSet[str] = frozenset({
    REL_BELONGS_TO,
    REL_REFERENCES,
    REL_CONTAINS,
    REL_DERIVED_FROM,
    REL_ANNOTATED_BY,
})

# Documented future relationship patterns (metadata only)
RELATIONSHIP_PATTERNS: list[dict[str, str]] = [
    {"from_type": "BAR", "relationship": REL_BELONGS_TO, "to_type": "ERC"},
    {"from_type": "BAR", "relationship": REL_REFERENCES, "to_type": "TEXT"},
    {"from_type": "BAR", "relationship": REL_REFERENCES, "to_type": "LEADER"},
    {"from_type": "BAR", "relationship": REL_REFERENCES, "to_type": "SKETCH"},
    {"from_type": "STIRRUP", "relationship": REL_REFERENCES, "to_type": "SKETCH"},
    {"from_type": "HOOK", "relationship": REL_DERIVED_FROM, "to_type": "BAR"},
    {"from_type": "LAP_SPLICE", "relationship": REL_REFERENCES, "to_type": "BAR"},
    {"from_type": "DEVELOPMENT_LENGTH", "relationship": REL_ANNOTATED_BY, "to_type": "TEXT"},
    {"from_type": "ANCHORAGE", "relationship": REL_REFERENCES, "to_type": "SKETCH"},
    {"from_type": "COVER", "relationship": REL_CONTAINS, "to_type": "ZONE"},
]


class EngineeringRelationships:
    """Build relationship export — empty until G.5 populates."""

    @staticmethod
    def build_relationship(
        source_id: str,
        target_id: str,
        relationship: str,
        source_type: str = "",
        target_type: str = "",
    ) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "source_type": source_type,
            "target_type": target_type,
        }

    @staticmethod
    def build_export(
        relationships: List[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "namespace": "ENGINEERING_RELATIONSHIP",
            "phase": "Phase G.4.2",
            "relationship_count": len(relationships or []),
            "relationships": list(relationships or []),
            "patterns": list(RELATIONSHIP_PATTERNS),
        }
