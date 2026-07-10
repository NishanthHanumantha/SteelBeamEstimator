"""Build deterministic decision context for intent resolution groups."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class DecisionContextBuilder:
    """Construct per-group engineering decision context from K.1 intents."""

    def build_groups(self, snapshot: dict[str, Any]) -> List[dict[str, Any]]:
        intents = list(snapshot.get("intent_objects") or [])
        grouped: Dict[Tuple[str, str, str], List[dict[str, Any]]] = {}
        for intent in intents:
            beam_id = str(intent.get("beam_id") or "UNKNOWN")
            source_bar_id = str(intent.get("source_bar_id") or "UNKNOWN")
            support_zone = str(intent.get("support_zone") or "UNKNOWN")
            key = (beam_id, source_bar_id, support_zone)
            grouped.setdefault(key, []).append(intent)

        contexts: List[dict[str, Any]] = []
        for (beam_id, source_bar_id, support_zone), group_intents in sorted(grouped.items()):
            contexts.append(self.build_one(beam_id, source_bar_id, support_zone, group_intents, snapshot))
        return contexts

    def build_one(
        self,
        beam_id: str,
        source_bar_id: str,
        support_zone: str,
        intents: List[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        calc_context = (snapshot.get("contexts_by_beam") or {}).get(beam_id) or {}
        support_refs = self._support_refs(beam_id, snapshot)
        support_id = self._support_id(support_zone, support_refs)
        engineering_object_id = next(
            (str(item.get("source_engineering_object_id")) for item in intents if item.get("source_engineering_object_id")),
            "",
        )
        intent_types = sorted({str(item.get("intent_type")) for item in intents if item.get("intent_type")})
        return {
            "decision_group_key": f"{beam_id}::{source_bar_id}::{support_zone}",
            "beam_id": beam_id,
            "source_bar_id": source_bar_id,
            "support_zone": support_zone,
            "support_id": support_id,
            "support_refs": support_refs,
            "engineering_object_id": engineering_object_id,
            "span": calc_context.get("clear_span_mm") or calc_context.get("span_mm"),
            "support_width": calc_context.get("support_width_mm"),
            "concrete_grade": calc_context.get("concrete_grade"),
            "steel_grade": calc_context.get("steel_grade"),
            "calculation_context_id": calc_context.get("context_id"),
            "calculation_status": calc_context.get("calculation_status"),
            "development_length_mm": calc_context.get("development_length_mm"),
            "anchorage_rule": calc_context.get("anchorage_rule"),
            "hook_rule": calc_context.get("hook_rule"),
            "lap_rule": calc_context.get("lap_rule"),
            "intent_ids": [str(item.get("intent_id")) for item in intents if item.get("intent_id")],
            "intent_types": intent_types,
            "intents": intents,
            "general_notes_present": bool(snapshot.get("engineering_rules")),
            "engineering_graph_present": bool(snapshot.get("project_engineering_graph")),
            "existing_reinforcement_count": len(
                ((snapshot.get("reinforcement_objects") or {}).get("bars") or [])
            ),
        }

    @staticmethod
    def _support_refs(beam_id: str, snapshot: dict[str, Any]) -> List[str]:
        beam_supports = snapshot.get("beam_supports") or {}
        refs: List[str] = []
        beams = beam_supports.get("beams") if isinstance(beam_supports, dict) else None
        if isinstance(beams, list):
            for beam in beams:
                if str(beam.get("beam_id") or beam.get("id") or "") != beam_id:
                    continue
                for key in ("left_support_id", "right_support_id", "support_id"):
                    value = beam.get(key)
                    if value:
                        refs.append(str(value))
                supports = beam.get("supports") or []
                if isinstance(supports, list):
                    refs.extend(str(item) for item in supports if item)
        return sorted(set(refs))

    @staticmethod
    def _support_id(support_zone: str, support_refs: List[str]) -> str:
        if not support_refs:
            return f"SUPPORT::{support_zone}"
        if support_zone == "RIGHT_SUPPORT":
            return support_refs[-1]
        return support_refs[0]
