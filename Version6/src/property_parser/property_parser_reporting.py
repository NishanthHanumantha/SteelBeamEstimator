"""Property parser reporting consistency — Phase G.5.3.1."""

from __future__ import annotations

from typing import Any

from src.property_parser.property_parser_summary import PropertyParserSummary


class PropertyParserReporting:
    """Single source of truth for property parser validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        model["property_parser_validation"] = validation
        model["property_parser_summary"] = PropertyParserSummary.build(
            model.get("property_candidates", []),
            model.get("engineering_properties", []),
            model.get("unparsed_candidates", []),
            model.get("property_parser_registry", {}),
            validation,
        )
