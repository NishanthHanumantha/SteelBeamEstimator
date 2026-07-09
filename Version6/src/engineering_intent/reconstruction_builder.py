"""Build reconstructed engineering intent objects."""

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
}

INTENT_ROLE_SUFFIX = {
    "SUPPLEMENTARY_DEVELOPMENT_LENGTH": "DEV_LENGTH",
    "SUPPLEMENTARY_ANCHORAGE": "ANCHORAGE",
    "SUPPLEMENTARY_HOOK": "HOOK",
    "SUPPLEMENTARY_CONTINUATION": "CONTINUATION",
    "SUPPLEMENTARY_CURTAILMENT": "CURTAILMENT",
    "SUPPLEMENTARY_SUPPORT_BAR": "SUPPORT_BAR",
    "SUPPLEMENTARY_REINFORCEMENT": "REINFORCEMENT",
    "SUPPLEMENTARY_TERMINATION": "TERMINATION",
}


class ReconstructionBuilder:
    """Create intent objects with full lineage and production artifacts."""

    def __init__(self, id_counters: dict[str, int]) -> None:
        self._counters = dict(id_counters)

    def build_all(
        self,
        approved: List[dict[str, Any]],
        contexts_by_beam: dict[str, dict[str, Any]],
        project_workspace: dict[str, Any],
    ) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        intent_objects: List[dict[str, Any]] = []
        traces: List[dict[str, Any]] = []
        engineering_objects: List[dict[str, Any]] = []
        specifications: List[dict[str, Any]] = []
        contexts: List[dict[str, Any]] = []
        registry_entries: List[dict[str, Any]] = []

        for candidate in approved:
            built = self._build_one(candidate, contexts_by_beam, project_workspace, timestamp)
            intent_objects.append(built["intent_object"])
            traces.append(built["intent_trace"])
            engineering_objects.append(built["engineering_object"])
            specifications.append(built["specification"])
            contexts.append(built["context"])
            registry_entries.append(built["registry_entry"])

        return {
            "intent_objects": intent_objects,
            "intent_traces": traces,
            "engineering_objects": engineering_objects,
            "specifications": specifications,
            "contexts": contexts,
            "registry_entries": registry_entries,
            "id_counters": self._counters,
        }

    def normalize_reconstructed(
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
        candidate: dict[str, Any],
        contexts_by_beam: dict[str, dict[str, Any]],
        project_workspace: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        context_data = candidate.get("context") or {}
        beam_id = str(candidate.get("beam_id") or context_data.get("beam_id") or "")
        role = str(context_data.get("role") or "TOP_MAIN")
        intent_type = str(candidate.get("intent_type") or "UNKNOWN")
        suffix = INTENT_ROLE_SUFFIX.get(intent_type, "INTENT")
        supplementary_role = f"{role}_{suffix}"

        self._counters["intent"] += 1
        self._counters["engineering_object"] += 1
        self._counters["specification"] += 1
        self._counters["calculation_context"] += 1

        intent_id = f"INTENT::{self._counters['intent']:06d}"
        engineering_object_id = f"ENG_OBJ::{self._counters['engineering_object']:06d}"
        specification_id = f"SPEC::{self._counters['specification']:06d}"
        context_id = f"CALC_CTX::{self._counters['calculation_context']:06d}"

        beam_template = contexts_by_beam.get(beam_id, context_data.get("calculation_context") or {})
        context = self._build_context(
            context_id,
            specification_id,
            engineering_object_id,
            beam_id,
            beam_template,
            project_workspace,
            candidate,
            timestamp,
        )

        evidence = {
            "intent_id": intent_id,
            "source_engineering_object_id": candidate.get("source_engineering_object_id"),
            "source_bar_id": candidate.get("source_bar_id"),
            "beam_id": beam_id,
            "general_note_id": candidate.get("general_note_id"),
            "development_length_rule": candidate.get("development_length_rule"),
            "development_length_mm": candidate.get("development_length_mm"),
            "engineering_rule": candidate.get("engineering_rule"),
            "geometry_reference": candidate.get("geometry_reference"),
            "support_reference": candidate.get("support_reference"),
            "engineering_graph_node": candidate.get("engineering_graph_node"),
            "calculation_context_id": candidate.get("calculation_context_id"),
            "evidence_confidence": candidate.get("evidence_confidence", 100.0),
            "intent_category": intent_type,
            "engineering_justification": candidate.get("engineering_justification"),
        }

        traceability = {
            "intent_id": intent_id,
            "intent_source": "Phase K.1",
            "intent_type": intent_type,
            "intent_key": candidate.get("intent_key"),
            "source_bar_id": candidate.get("source_bar_id"),
            "source_engineering_object_id": candidate.get("source_engineering_object_id"),
            "engineering_rule": candidate.get("engineering_rule"),
            "general_note_id": candidate.get("general_note_id"),
            "support_zone": candidate.get("support_zone"),
            "support_reference": candidate.get("support_reference"),
            "development_length_mm": candidate.get("development_length_mm"),
            "intent_version": "6.0.0",
            "intent_justification": candidate.get("engineering_justification"),
            "evidence": evidence,
        }

        engineering_object = build_engineering_object(
            object_id=engineering_object_id,
            object_type=ROLE_TO_OBJECT_TYPE.get(role, OBJECT_TOP_REINFORCEMENT),
            owner_context_id=f"ERC::{beam_id}",
            source_role_id=str(candidate.get("source_engineering_object_id") or ""),
            detail_context_id=str(candidate.get("geometry_reference") or ""),
            drawing_id=str(beam_template.get("drawing_id") or ""),
            drawing_set_id=str(beam_template.get("drawing_set_id") or ""),
            classification_source=CLASSIFICATION_SOURCE_SEMANTIC_GRAPH,
            confidence=100.0,
            engineering_status=ENGINEERING_STATUS_OBJECT_CREATED,
            lifecycle=LIFECYCLE_OBJECT_CREATED,
            notes=f"Intent reconstruction {intent_type} from {candidate.get('source_bar_id')}",
            metadata={
                "intent_source": "Phase K.1",
                "intent_id": intent_id,
                "intent_type": intent_type,
                "source_bar_id": candidate.get("source_bar_id"),
            },
        )

        specification = build_engineering_specification(
            specification_id=specification_id,
            engineering_object_id=engineering_object_id,
            beam_id=beam_id,
            reinforcement_role=supplementary_role,
            reinforcement_type=f"INTENT_{intent_type}",
            specification_status=STATUS_PARTIAL,
            resolved_property_ids=[],
            resolved_properties=[],
            property_lifecycle_summary={},
            property_status_summary={},
            resolution_summary={},
            traceability=traceability,
            quantity=context_data.get("quantity"),
            diameter=context_data.get("diameter_mm"),
            bar_type="MAIN_BAR",
            level="TOP" if "TOP" in role else "BOTTOM",
            zone=candidate.get("support_zone"),
            callout=f"INTENT::{intent_type}",
            created_timestamp=timestamp,
        )

        intent_object = {
            "intent_id": intent_id,
            "intent_key": candidate.get("intent_key"),
            "intent_type": intent_type,
            "reconstructed_object_id": engineering_object_id,
            "source_bar_id": candidate.get("source_bar_id"),
            "source_engineering_object_id": candidate.get("source_engineering_object_id"),
            "beam_id": beam_id,
            "support_zone": candidate.get("support_zone"),
            "specification_id": specification_id,
            "context_id": context_id,
            "intent_source": "Phase K.1",
            "intent_version": "6.0.0",
            "evidence": evidence,
            "engineering_justification": candidate.get("engineering_justification"),
        }

        intent_trace = {
            "intent_id": intent_id,
            "intent_key": candidate.get("intent_key"),
            "lineage": [
                "Engineering Intent Reconstruction",
                "Engineering Rule",
                "General Notes",
                "Source Engineering Object",
                "Beam",
                "Calculation Context",
            ],
            "source_bar_id": candidate.get("source_bar_id"),
            "source_engineering_object_id": candidate.get("source_engineering_object_id"),
            "engineering_rule": candidate.get("engineering_rule"),
            "general_note_id": candidate.get("general_note_id"),
            "development_length_rule": candidate.get("development_length_rule"),
            "beam_id": beam_id,
            "support_reference": candidate.get("support_reference"),
            "calculation_context_id": context_id,
            "reconstructed_object_id": engineering_object_id,
            "evidence": evidence,
        }

        registry_entry = {
            "intent_id": intent_id,
            "intent_key": candidate.get("intent_key"),
            "intent_type": intent_type,
            "source_bar_id": candidate.get("source_bar_id"),
            "source_engineering_object_id": candidate.get("source_engineering_object_id"),
            "reconstructed_object_id": engineering_object_id,
            "normalized_bar_id": None,
            "specification_id": specification_id,
            "context_id": context_id,
            "beam_id": beam_id,
            "engineering_rule": candidate.get("engineering_rule"),
            "general_note_id": candidate.get("general_note_id"),
            "engineering_justification": candidate.get("engineering_justification"),
            "intent_status": "SUCCESS",
            "evidence_confidence": candidate.get("evidence_confidence", 100.0),
        }

        return {
            "intent_object": intent_object,
            "intent_trace": intent_trace,
            "engineering_object": engineering_object,
            "specification": specification,
            "context": context,
            "registry_entry": registry_entry,
        }

    @staticmethod
    def _build_context(
        context_id: str,
        specification_id: str,
        engineering_object_id: str,
        beam_id: str,
        template: dict[str, Any],
        project_workspace: dict[str, Any],
        candidate: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        context = dict(template)
        context.update(
            {
                "context_id": context_id,
                "specification_id": specification_id,
                "engineering_object_id": engineering_object_id,
                "beam_id": beam_id,
                "phase": "Phase I.1",
                "intent_source": "Phase K.1",
                "intent_id": candidate.get("intent_key"),
                "intent_type": candidate.get("intent_type"),
                "source_bar_id": candidate.get("source_bar_id"),
                "support_zone": candidate.get("support_zone"),
                "support_reference": candidate.get("support_reference"),
                "development_length_mm": candidate.get("development_length_mm"),
                "created_timestamp": timestamp,
            }
        )
        if not context.get("project_id"):
            context["project_id"] = project_workspace.get("project_id", "")
        return context

    @staticmethod
    def patch_registry_bar_ids(
        registry_entries: List[dict[str, Any]],
        normalized_bars: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        bar_by_intent = {}
        for bar in normalized_bars:
            trace = bar.get("traceability") or {}
            intent_key = trace.get("intent_key")
            if intent_key:
                bar_by_intent[str(intent_key)] = bar.get("bar_id")
        for entry in registry_entries:
            intent_key = str(entry.get("intent_key") or "")
            if intent_key in bar_by_intent:
                entry["normalized_bar_id"] = bar_by_intent[intent_key]
        return registry_entries
