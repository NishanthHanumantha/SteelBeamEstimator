"""Build engineering annotation context for duplicate comparison."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from src.duplicate_legitimacy_audit.duplicate_group_loader import COORDINATE_TOLERANCE


class AnnotationContextBuilder:
    """Enrich duplicate members with comparable engineering features."""

    COMPARISON_FIELDS = (
        "beam",
        "category",
        "role",
        "position",
        "specification",
        "diameter_mm",
        "quantity",
        "beam_station",
        "engineering_region",
        "support",
        "span",
        "coordinate",
        "association_source",
        "leader",
        "drawing_context",
        "object_signature",
        "normalization_result",
        "calculation_context_id",
    )

    def build_member_context(self, member: dict[str, Any], group: dict[str, Any]) -> dict[str, Any]:
        coordinates = member.get("coordinates") or {}
        text_object = member.get("text_object") or {}
        context = group.get("context") or {}
        bar = member.get("bar") or {}
        trace = (bar.get("traceability") or {}) if bar else {}
        return {
            "discovery_id": member.get("discovery_id"),
            "beam": member.get("beam_association") or group.get("beam_id"),
            "category": member.get("category"),
            "role": member.get("role"),
            "position": bar.get("position") or member.get("role"),
            "specification": trace.get("specification_id") or member.get("engineering_object_id"),
            "diameter_mm": member.get("diameter_mm"),
            "quantity": member.get("quantity"),
            "beam_station": self._estimate_station(coordinates, context),
            "engineering_region": member.get("region") or (text_object.get("ownership") or {}).get("owner_id"),
            "support": self._support_zone(coordinates, context),
            "span": context.get("clear_span_mm") or context.get("effective_span_mm"),
            "coordinate": coordinates,
            "association_source": member.get("association_source"),
            "leader": member.get("leader") or text_object.get("leader"),
            "drawing_context": {
                "layer": member.get("layer") or text_object.get("layer"),
                "geometry_id": member.get("geometry_id"),
                "text_source": member.get("text_source") or text_object.get("entity_type"),
            },
            "object_signature": group.get("signature"),
            "normalization_result": member.get("normalized_bar_id"),
            "calculation_context_id": context.get("context_id"),
            "suppressed": member.get("suppressed", False),
            "primary_rejection_code": (member.get("decision") or {}).get("primary_rejection_code"),
        }

    def build_group_context(self, group: dict[str, Any]) -> dict[str, Any]:
        members = group.get("members") or []
        contexts = [self.build_member_context(member, group) for member in members]
        return {
            "group_id": group.get("group_id"),
            "signature": group.get("signature"),
            "beam_id": group.get("beam_id"),
            "member_contexts": contexts,
            "comparison_matrix": self._comparison_matrix(contexts),
        }

    def _comparison_matrix(self, contexts: List[dict[str, Any]]) -> dict[str, Any]:
        matrix: dict[str, Any] = {}
        for field in self.COMPARISON_FIELDS:
            values = [self._normalize_value(item.get(field)) for item in contexts]
            unique_values = sorted({value for value in values if value is not None})
            matrix[field] = {
                "values": values,
                "unique_count": len(unique_values),
                "uniform": len(unique_values) <= 1,
            }
        return matrix

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, dict):
            if "x" in value and "y" in value:
                return (
                    round(float(value["x"]), 1),
                    round(float(value["y"]), 1),
                )
            return tuple(sorted(value.items()))
        if isinstance(value, float):
            return round(value, 3)
        return value

    @staticmethod
    def _estimate_station(coordinates: dict[str, Any], context: dict[str, Any]) -> Optional[float]:
        if not coordinates:
            return None
        span = context.get("effective_span_mm") or context.get("clear_span_mm")
        if not span:
            return round(float(coordinates.get("x") or 0.0), 1)
        x_value = float(coordinates.get("x") or 0.0)
        return round(x_value % float(span), 1)

    @staticmethod
    def _support_zone(coordinates: dict[str, Any], context: dict[str, Any]) -> str:
        station = coordinates.get("x")
        span = context.get("effective_span_mm") or context.get("clear_span_mm")
        if station is None or not span:
            return "UNKNOWN"
        ratio = float(station) / float(span)
        if ratio <= 0.15:
            return "LEFT_SUPPORT"
        if ratio >= 0.85:
            return "RIGHT_SUPPORT"
        if 0.4 <= ratio <= 0.6:
            return "CENTER"
        return "SPAN"

    @staticmethod
    def coordinate_distance(left: dict[str, Any], right: dict[str, Any]) -> float:
        if not left or not right:
            return float("inf")
        dx = float(left.get("x", 0.0)) - float(right.get("x", 0.0))
        dy = float(left.get("y", 0.0)) - float(right.get("y", 0.0))
        return math.hypot(dx, dy)

    @staticmethod
    def coordinates_equal(left: dict[str, Any], right: dict[str, Any], tolerance: float = COORDINATE_TOLERANCE) -> bool:
        return AnnotationContextBuilder.coordinate_distance(left, right) <= tolerance
