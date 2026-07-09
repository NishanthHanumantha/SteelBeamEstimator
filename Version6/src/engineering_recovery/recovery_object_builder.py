"""Build recovered engineering objects, specifications, and contexts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from src.engineering_objects.engineering_object import build_engineering_object
from src.engineering_objects.engineering_object_types import (
    CLASSIFICATION_SOURCE_SEMANTIC_GRAPH,
    ENGINEERING_STATUS_OBJECT_CREATED,
    LIFECYCLE_OBJECT_CREATED,
    OBJECT_TOP_REINFORCEMENT,
)
from src.engineering_specifications.engineering_specification import build_engineering_specification
from src.engineering_specifications.specification_types import STATUS_PARTIAL


ROLE_TO_OBJECT_TYPE = {
    "TOP_MAIN": OBJECT_TOP_REINFORCEMENT,
    "BOTTOM_MAIN": "BOTTOM_REINFORCEMENT",
    "EXTRA_TOP": "TOP_REINFORCEMENT",
    "EXTRA_BOTTOM": "BOTTOM_REINFORCEMENT",
    "STIRRUP": "STIRRUP",
    "LINK_BAR": "LINK",
    "SIDE_BAR": "SIDE_FACE_REINFORCEMENT",
}

ROLE_TO_SPECIFICATION_TYPE = {
    "TOP_MAIN": "TOP_MAIN_REINFORCEMENT",
    "BOTTOM_MAIN": "BOTTOM_MAIN_REINFORCEMENT",
    "EXTRA_TOP": "EXTRA_TOP_REINFORCEMENT",
    "EXTRA_BOTTOM": "EXTRA_BOTTOM_REINFORCEMENT",
    "STIRRUP": "STIRRUP",
    "LINK_BAR": "LINK",
    "SIDE_BAR": "EDGE_BAR",
    "STARTER": "STARTER_BAR",
}


class RecoveryObjectBuilder:
    """Create recovered engineering artifacts from approved decisions."""

    def __init__(self, id_counters: dict[str, int]) -> None:
        self._counters = dict(id_counters)

    def build_all(
        self,
        approved_decisions: List[dict[str, Any]],
        contexts_by_beam: dict[str, dict[str, Any]],
        project_workspace: dict[str, Any],
    ) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        recovered_objects: List[dict[str, Any]] = []
        recovered_specs: List[dict[str, Any]] = []
        recovered_contexts: List[dict[str, Any]] = []
        engineering_objects: List[dict[str, Any]] = []
        specifications: List[dict[str, Any]] = []
        contexts: List[dict[str, Any]] = []

        for decision in approved_decisions:
            built = self._build_one(decision, contexts_by_beam, project_workspace, timestamp)
            recovered_objects.append(built["recovered_object"])
            recovered_specs.append(built["specification"])
            recovered_contexts.append(built["context"])
            engineering_objects.append(built["engineering_object"])
            specifications.append(built["specification"])
            contexts.append(built["context"])

        return {
            "recovered_objects": recovered_objects,
            "recovered_specifications": recovered_specs,
            "recovered_contexts": recovered_contexts,
            "engineering_objects": engineering_objects,
            "specifications": specifications,
            "contexts": contexts,
            "id_counters": self._counters,
        }

    def normalize_recovered(
        self,
        specifications: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]], Any]:
        from src.reinforcement_calculation.reinforcement_builder import ReinforcementBuilder
        from src.reinforcement_calculation.reinforcement_registry import ReinforcementRegistry

        registry = ReinforcementRegistry()
        registry._bar_sequence = self._counters.get("rebar", 0)
        registry._group_sequence = self._counters.get("rebar_group", 0)
        builder = ReinforcementBuilder()
        bars: List[dict[str, Any]] = []
        groups: List[dict[str, Any]] = []
        context_by_spec = {str(item.get("specification_id")): item for item in contexts}
        for spec in sorted(specifications, key=lambda item: str(item.get("specification_id"))):
            context = context_by_spec.get(str(spec.get("specification_id")), {})
            bar, group = builder._normalize_specification(spec, context, registry)
            traceability = dict(bar.get("traceability") or {})
            traceability.update(spec.get("traceability") or {})
            bar["traceability"] = traceability
            group["traceability"] = traceability
            bars.append(bar)
            groups.append(group)
        self._counters["rebar"] = registry._bar_sequence
        self._counters["rebar_group"] = registry._group_sequence
        return bars, groups, registry

    def _build_one(
        self,
        decision: dict[str, Any],
        contexts_by_beam: dict[str, dict[str, Any]],
        project_workspace: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        inventory = decision.get("inventory") or {}
        discovery_id = str(decision.get("discovery_id"))
        beam_id = str(decision.get("beam_id") or inventory.get("beam_association") or "UNKNOWN")
        role = str(inventory.get("role") or "TOP_MAIN")
        reinforcement_type = ROLE_TO_SPECIFICATION_TYPE.get(role, "TOP_MAIN_REINFORCEMENT")
        object_type = ROLE_TO_OBJECT_TYPE.get(role, OBJECT_TOP_REINFORCEMENT)

        self._counters["recovery"] += 1
        self._counters["engineering_object"] += 1
        self._counters["specification"] += 1
        self._counters["calculation_context"] += 1

        recovery_id = f"RECOVERY::{self._counters['recovery']:06d}"
        engineering_object_id = f"ENG_OBJ::{self._counters['engineering_object']:06d}"
        specification_id = f"SPEC::{self._counters['specification']:06d}"
        context_id = f"CALC_CTX::{self._counters['calculation_context']:06d}"

        beam_template = contexts_by_beam.get(beam_id, {})
        context = self._build_context(
            context_id,
            specification_id,
            engineering_object_id,
            beam_id,
            beam_template,
            project_workspace,
            inventory,
            timestamp,
        )
        traceability = {
            "discovery_id": discovery_id,
            "geometry_id": inventory.get("geometry_id"),
            "recovery_id": recovery_id,
            "recovery_source": "QA.COVERAGE.5",
            "qa_coverage_4_rejection": decision.get("primary_rejection_code"),
            "qa_coverage_5_legitimacy": decision.get("legitimacy_class"),
            "recovery_confidence": decision.get("confidence_score"),
            "recovery_reason": decision.get("recovery_reason"),
            "original_suppression_reason": decision.get("primary_rejection_code"),
            "coordinates": inventory.get("coordinates"),
            "engineering_region": inventory.get("region"),
            "support": context.get("support_zone"),
            "beam_station": context.get("station_mm"),
        }
        engineering_object = build_engineering_object(
            object_id=engineering_object_id,
            object_type=object_type,
            owner_context_id=str(inventory.get("region") or f"ERC::{beam_id}"),
            source_role_id=str(inventory.get("geometry_id") or discovery_id),
            detail_context_id=str(inventory.get("geometry_id") or ""),
            drawing_id=str(beam_template.get("drawing_id") or ""),
            drawing_set_id=str(beam_template.get("drawing_set_id") or ""),
            classification_source=CLASSIFICATION_SOURCE_SEMANTIC_GRAPH,
            confidence=float(decision.get("confidence_score") or 0.0),
            engineering_status=ENGINEERING_STATUS_OBJECT_CREATED,
            lifecycle=LIFECYCLE_OBJECT_CREATED,
            notes=f"Recovered from {discovery_id}",
            metadata={
                "recovery_source": "QA.COVERAGE.5",
                "recovery_id": recovery_id,
                "discovery_id": discovery_id,
            },
        )
        specification = build_engineering_specification(
            specification_id=specification_id,
            engineering_object_id=engineering_object_id,
            beam_id=beam_id,
            reinforcement_role=role,
            reinforcement_type=reinforcement_type,
            specification_status=STATUS_PARTIAL,
            resolved_property_ids=[],
            resolved_properties=[],
            property_lifecycle_summary={},
            property_status_summary={},
            resolution_summary={},
            traceability=traceability,
            quantity=inventory.get("quantity"),
            diameter=inventory.get("diameter_mm"),
            bar_type="MAIN_BAR",
            level="TOP" if "TOP" in role else None,
            zone=role,
            callout=inventory.get("original_text"),
            created_timestamp=timestamp,
        )
        recovered_object = {
            "recovered_object_id": engineering_object_id,
            "recovery_id": recovery_id,
            "source_discovery_id": discovery_id,
            "beam": beam_id,
            "category": inventory.get("category"),
            "role": role,
            "diameter_mm": inventory.get("diameter_mm"),
            "quantity": inventory.get("quantity"),
            "engineering_region": inventory.get("region"),
            "coordinates": inventory.get("coordinates"),
            "support": context.get("support_zone"),
            "station": context.get("station_mm"),
            "specification_id": specification_id,
            "recovery_source": "QA.COVERAGE.5",
            "recovery_confidence": decision.get("confidence_score"),
            "recovery_version": "5.26.0",
            "recovery_timestamp": timestamp,
            "original_suppression_reason": decision.get("primary_rejection_code"),
            "recovery_justification": decision.get("recovery_reason"),
            "legitimacy_class": decision.get("legitimacy_class"),
            "context_id": context_id,
        }
        return {
            "recovered_object": recovered_object,
            "engineering_object": engineering_object,
            "specification": specification,
            "context": context,
        }

    @staticmethod
    def _build_context(
        context_id: str,
        specification_id: str,
        engineering_object_id: str,
        beam_id: str,
        template: dict[str, Any],
        project_workspace: dict[str, Any],
        inventory: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        coordinates = inventory.get("coordinates") or {}
        span = float(template.get("effective_span_mm") or template.get("clear_span_mm") or 0.0)
        station_mm = round(float(coordinates.get("x") or 0.0) % span, 3) if span else None
        support_zone = RecoveryObjectBuilder._support_zone(coordinates, template)
        context = dict(template)
        context.update(
            {
                "context_id": context_id,
                "specification_id": specification_id,
                "engineering_object_id": engineering_object_id,
                "beam_id": beam_id,
                "phase": "Phase I.1",
                "recovery_source": "QA.COVERAGE.5",
                "discovery_id": inventory.get("discovery_id"),
                "geometry_id": inventory.get("geometry_id"),
                "coordinates": coordinates,
                "station_mm": station_mm,
                "support_zone": support_zone,
                "created_timestamp": timestamp,
            }
        )
        if not context.get("project_id"):
            context["project_id"] = project_workspace.get("project_id", "")
        return context

    @staticmethod
    def _support_zone(coordinates: dict[str, Any], template: dict[str, Any]) -> str:
        station = coordinates.get("x")
        span = template.get("effective_span_mm") or template.get("clear_span_mm")
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
