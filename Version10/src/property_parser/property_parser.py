"""Main Engineering Property Parser — Phase G.5.3.1."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from src.property_parser.engineering_property import build_engineering_property
from src.property_parser.property_parser_registry import PropertyParserRegistry
from src.property_parser.property_parser_types import (
    NON_TEXT_SOURCE_TYPES,
    PARSE_STATUS_PARSED,
    PARSE_STATUS_UNPARSED,
    PROP_CALLOUT,
    PROP_NOTE,
    PROP_TEXT,
    PROP_UNKNOWN,
    PARSER_NAME_TEXT,
    PARSER_VERSION,
    REINFORCEMENT_PARSE_TYPES,
    TEXT_SOURCE_TYPES,
    UNIT_NONE,
)
from src.property_parser.text_property_parser import TextPropertyParser


class PropertyParser:
    """Convert property candidates into normalized engineering properties."""

    def build(
        self,
        candidates: List[dict[str, Any]],
        entity_text_index: Dict[str, str],
    ) -> Tuple[List[dict[str, Any]], PropertyParserRegistry, List[dict[str, Any]]]:
        registry = PropertyParserRegistry()
        all_properties: List[dict[str, Any]] = []
        unparsed_records: List[dict[str, Any]] = []
        text_cache: Dict[str, Any] = {}

        for candidate in candidates:
            cid = candidate.get("candidate_id", "")
            registry.mark_candidate_processed(cid)
            props = self._process_candidate(candidate, entity_text_index, text_cache)
            for prop in props:
                registry.register(prop)
                all_properties.append(prop)
                if prop.get("parse_status") == PARSE_STATUS_UNPARSED:
                    unparsed_records.append(
                        {
                            "candidate_id": cid,
                            "engineering_object_id": candidate.get("engineering_object_id"),
                            "candidate_type": candidate.get("candidate_type"),
                            "source_entity_id": candidate.get("source_entity_id"),
                            "source_text": prop.get("source_text", ""),
                            "reason": prop.get("unparsed_reason", ""),
                            "property_id": prop.get("property_id"),
                        }
                    )

        return all_properties, registry, unparsed_records

    @staticmethod
    def build_project_exports(
        candidates: List[dict[str, Any]],
        registry: PropertyParserRegistry,
        properties: List[dict[str, Any]],
        unparsed_records: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
    ) -> dict[str, Any]:
        primary = drawing_models[0] if drawing_models else {}
        parser_registry = PropertyParserRegistry.build_project_registry(
            properties,
            candidates,
            registry.processed_candidate_ids(),
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        return {
            "engineering_properties": properties,
            "property_parser_registry": parser_registry,
            "unparsed_candidates": unparsed_records,
        }

    @staticmethod
    def build_entity_text_index(model: dict[str, Any]) -> Dict[str, str]:
        """Resolve source text from already-extracted drawing model entities."""
        index: Dict[str, str] = {}
        for dm in model.get("reinforcement_drawing_models", []):
            for text_obj in dm.get("text_objects", []):
                gid = text_obj.get("geometry_id")
                if gid:
                    index[str(gid)] = str(text_obj.get("text", "")).strip()
        for role in model.get("engineering_semantic_role_registry", {}).get("roles", []):
            for text_id in role.get("text_asset_ids", []):
                if text_id in index:
                    continue
        return index

    def _process_candidate(
        self,
        candidate: dict[str, Any],
        entity_text_index: Dict[str, str],
        text_cache: Dict[str, Any],
    ) -> List[dict[str, Any]]:
        candidate_type = str(candidate.get("candidate_type", PROP_UNKNOWN))
        source_type = str(candidate.get("candidate_source_type", ""))
        entity_id = str(candidate.get("source_entity_id", ""))
        base_kwargs = {
            "engineering_object_id": candidate.get("engineering_object_id", ""),
            "candidate_id": candidate.get("candidate_id", ""),
            "source_entity_id": entity_id,
            "confidence": float(candidate.get("confidence", 0.0)),
            "source_role_id": candidate.get("source_role_id", ""),
            "owner_context_id": candidate.get("owner_context_id", ""),
            "metadata": {
                "candidate_type": candidate_type,
                "candidate_source_type": source_type,
                "discovery_method": candidate.get("discovery_method"),
            },
        }

        if source_type in NON_TEXT_SOURCE_TYPES or (
            source_type not in TEXT_SOURCE_TYPES and entity_id.startswith(("SKETCH::", "LDR::", "BLOCK::"))
        ):
            return [
                self._unparsed(
                    candidate_type=candidate_type,
                    reason="non_text_source_entity",
                    source_text="",
                    **base_kwargs,
                )
            ]

        source_text = entity_text_index.get(entity_id, "")
        base_kwargs["source_text"] = source_text

        if not source_text:
            return [
                self._unparsed(
                    candidate_type=candidate_type,
                    reason="no_source_text",
                    **base_kwargs,
                )
            ]

        if entity_id not in text_cache:
            text_cache[entity_id] = TextPropertyParser.parse(source_text)
        parsed = text_cache[entity_id]

        if candidate_type == PROP_TEXT:
            return self._properties_for_text_candidate(parsed, **base_kwargs)

        if candidate_type in (PROP_NOTE, PROP_CALLOUT):
            return [
                self._parsed_property(
                    property_type=candidate_type,
                    parsed_value=source_text,
                    normalized_value=source_text.strip(),
                    unit=UNIT_NONE,
                    parse_confidence=0.85 if parsed.parse_success else 0.6,
                    **base_kwargs,
                )
            ]

        if candidate_type in REINFORCEMENT_PARSE_TYPES:
            field = parsed.get_for_type(candidate_type)
            if field:
                return [
                    self._parsed_property(
                        property_type=candidate_type,
                        parsed_value=field["parsed_value"],
                        normalized_value=field["normalized_value"],
                        unit=field.get("unit", UNIT_NONE),
                        parse_confidence=0.95 if parsed.parse_success else 0.5,
                        **base_kwargs,
                    )
                ]
            return [
                self._unparsed(
                    candidate_type=candidate_type,
                    reason=f"no_{candidate_type.lower()}_in_text",
                    **base_kwargs,
                )
            ]

        return [
            self._unparsed(
                candidate_type=candidate_type,
                reason="unsupported_candidate_type",
                **base_kwargs,
            )
        ]

    def _properties_for_text_candidate(
        self,
        parsed: Any,
        **base_kwargs: Any,
    ) -> List[dict[str, Any]]:
        props: List[dict[str, Any]] = [
            self._parsed_property(
                property_type=PROP_TEXT,
                parsed_value=base_kwargs.get("source_text", ""),
                normalized_value=str(base_kwargs.get("source_text", "")).strip(),
                unit=UNIT_NONE,
                parse_confidence=0.9,
                **base_kwargs,
            )
        ]
        if parsed.parse_success:
            for ptype, field in parsed.as_properties().items():
                props.append(
                    self._parsed_property(
                        property_type=ptype,
                        parsed_value=field["parsed_value"],
                        normalized_value=field["normalized_value"],
                        unit=field.get("unit", UNIT_NONE),
                        parse_confidence=0.95,
                        **base_kwargs,
                    )
                )
        return props

    def _parsed_property(
        self,
        property_type: str,
        parsed_value: Any,
        normalized_value: Any,
        unit: str,
        parse_confidence: float,
        **base_kwargs: Any,
    ) -> dict[str, Any]:
        candidate_confidence = float(base_kwargs.pop("confidence", 0.0))
        confidence = round(candidate_confidence * parse_confidence, 4)
        return build_engineering_property(
            property_id="",
            property_type=property_type,
            parsed_value=parsed_value,
            normalized_value=normalized_value,
            unit=unit,
            parse_status=PARSE_STATUS_PARSED,
            confidence=confidence,
            parser_name=PARSER_NAME_TEXT,
            parser_version=PARSER_VERSION,
            **base_kwargs,
        )

    def _unparsed(
        self,
        candidate_type: str,
        reason: str,
        **base_kwargs: Any,
    ) -> dict[str, Any]:
        return build_engineering_property(
            property_id="",
            property_type=candidate_type if candidate_type else PROP_UNKNOWN,
            parsed_value=None,
            normalized_value=None,
            unit=UNIT_NONE,
            parse_status=PARSE_STATUS_UNPARSED,
            confidence=round(float(base_kwargs.pop("confidence", 0.0)) * 0.4, 4),
            unparsed_reason=reason,
            parser_name=PARSER_NAME_TEXT,
            parser_version=PARSER_VERSION,
            **base_kwargs,
        )
