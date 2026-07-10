"""Build EngineeringDecision objects from resolved intent groups."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.engineering_intent_resolution.intent_priority_engine import IntentPriorityEngine
from src.engineering_intent_resolution.resolution_collector import MODEL_VERSION, PHASE


class DecisionBuilder:
    """Create one engineering detailing decision per decision group."""

    def __init__(self, priority_engine: IntentPriorityEngine) -> None:
        self._priority = priority_engine
        self._sequence = 0

    def set_sequence(self, start: int) -> None:
        self._sequence = int(start)

    def build_all(
        self,
        decision_contexts: List[dict[str, Any]],
        graphs: List[dict[str, Any]],
        overlaps_by_group: Dict[str, List[dict[str, Any]]],
        conflicts_by_group: Dict[str, List[dict[str, Any]]],
        merges_by_group: Dict[str, List[dict[str, Any]]],
        suppressed_by_group: Dict[str, Set[str]],
        existing_decision_keys: Set[str],
    ) -> dict[str, Any]:
        graph_by_key = {str(item.get("decision_group_key")): item for item in graphs}
        decisions: List[dict[str, Any]] = []
        registry_entries: List[dict[str, Any]] = []
        traces: List[dict[str, Any]] = []

        for context in decision_contexts:
            group_key = str(context.get("decision_group_key"))
            decision_key = f"DECISION::{group_key}"
            if decision_key in existing_decision_keys:
                continue
            decision = self.build_one(
                context,
                graph_by_key.get(group_key) or {},
                overlaps_by_group.get(group_key) or [],
                conflicts_by_group.get(group_key) or [],
                merges_by_group.get(group_key) or [],
                suppressed_by_group.get(group_key) or set(),
            )
            decisions.append(decision)
            registry_entries.append(self._registry_entry(decision))
            traces.append(self._trace(decision, context))

        return {
            "decisions": decisions,
            "registry_entries": registry_entries,
            "traces": traces,
        }

    def build_one(
        self,
        context: dict[str, Any],
        graph: dict[str, Any],
        overlaps: List[dict[str, Any]],
        conflicts: List[dict[str, Any]],
        merges: List[dict[str, Any]],
        suppressed_ids: Set[str],
    ) -> dict[str, Any]:
        self._sequence += 1
        decision_id = f"DECISION::{self._sequence:06d}"
        intents = list(context.get("intents") or [])
        by_id = {str(item.get("intent_id")): item for item in intents if item.get("intent_id")}

        active = [item for item in intents if str(item.get("intent_id")) not in suppressed_ids]
        ordered_active = self._priority.sort_intents(active)

        primary = None
        supporting: List[dict[str, Any]] = []
        if merges:
            primary_merge = sorted(merges, key=lambda item: str(item.get("merge_id")))[0]
            primary_id = str(primary_merge.get("primary_intent_id") or "")
            primary = by_id.get(primary_id) or (ordered_active[0] if ordered_active else None)
            merge_member_ids = {
                str(intent_id)
                for intent_id in (primary_merge.get("member_intent_ids") or [])
            }
            supporting = [
                by_id[intent_id]
                for intent_id in (primary_merge.get("member_intent_ids") or [])
                if intent_id in by_id and intent_id != primary_id
            ]
            # Retain all other active intents as supporting (never drop engineering knowledge).
            for item in ordered_active:
                item_id = str(item.get("intent_id") or "")
                if not item_id or item_id == primary_id or item_id in merge_member_ids:
                    continue
                supporting.append(item)
            resolution_rule = str(primary_merge.get("resolution_rule") or "K.1.1.RESOLVE.MERGE")
            decision_category = str(primary_merge.get("result_category") or "MERGED_DECISION")
        elif ordered_active:
            primary = ordered_active[0]
            supporting = ordered_active[1:]
            resolution_rule = "K.1.1.RESOLVE.PRIORITY"
            decision_category = str(primary.get("intent_type") or "UNKNOWN")
        else:
            # All suppressed — still emit a conservative decision from highest original intent.
            ordered_all = self._priority.sort_intents(intents)
            primary = ordered_all[0] if ordered_all else {}
            supporting = []
            resolution_rule = "K.1.1.RESOLVE.CONSERVATIVE_FALLBACK"
            decision_category = str(primary.get("intent_type") or "UNKNOWN")

        suppressed = [
            by_id[intent_id]
            for intent_id in sorted(suppressed_ids)
            if intent_id in by_id
        ]

        primary_id = str((primary or {}).get("intent_id") or "")
        supporting_ids = [str(item.get("intent_id")) for item in supporting if item.get("intent_id")]
        suppressed_intent_ids = [str(item.get("intent_id")) for item in suppressed if item.get("intent_id")]

        confidence = self._confidence(primary, supporting, suppressed, conflicts)
        justification = self._justification(primary, supporting, suppressed, merges, conflicts)
        evidence = {
            "decision_group_key": context.get("decision_group_key"),
            "graph_id": graph.get("graph_id"),
            "primary_intent_id": primary_id,
            "supporting_intent_ids": supporting_ids,
            "suppressed_intent_ids": suppressed_intent_ids,
            "overlap_count": len(overlaps),
            "conflict_count": len(conflicts),
            "merge_count": len(merges),
            "calculation_context_id": context.get("calculation_context_id"),
            "concrete_grade": context.get("concrete_grade"),
            "steel_grade": context.get("steel_grade"),
            "development_length_mm": context.get("development_length_mm"),
            "engineering_justification": justification,
        }

        production_eligible = bool(primary_id) and str((primary or {}).get("intent_type") or "") != "UNKNOWN"

        return {
            "decision_id": decision_id,
            "decision_key": f"DECISION::{context.get('decision_group_key')}",
            "beam_id": context.get("beam_id"),
            "support_id": context.get("support_id"),
            "support_zone": context.get("support_zone"),
            "engineering_object_id": context.get("engineering_object_id"),
            "source_bar_id": context.get("source_bar_id"),
            "primary_intent": {
                "intent_id": primary_id,
                "intent_key": (primary or {}).get("intent_key"),
                "intent_type": (primary or {}).get("intent_type"),
            },
            "supporting_intents": [
                {
                    "intent_id": item.get("intent_id"),
                    "intent_key": item.get("intent_key"),
                    "intent_type": item.get("intent_type"),
                }
                for item in supporting
            ],
            "suppressed_intents": [
                {
                    "intent_id": item.get("intent_id"),
                    "intent_key": item.get("intent_key"),
                    "intent_type": item.get("intent_type"),
                    "suppression_reason": "RESOLVED_BY_PRIORITY_OR_CONFLICT",
                    "retained": True,
                }
                for item in suppressed
            ],
            "conflict_list": [item.get("conflict_id") for item in conflicts],
            "conflicts": conflicts,
            "merges": merges,
            "overlaps": overlaps,
            "resolution_rule": resolution_rule,
            "decision_category": decision_category,
            "engineering_justification": justification,
            "evidence": evidence,
            "decision_confidence": confidence,
            "lifecycle": "RESOLVED",
            "production_eligibility": "ELIGIBLE" if production_eligible else "HOLD",
            "graph_id": graph.get("graph_id"),
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "intent_count": len(intents),
            "active_intent_count": len(active),
            "suppressed_intent_count": len(suppressed),
        }

    def rebuild_from_registry(
        self,
        existing_entries: List[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        intents_by_id = {
            str(item.get("intent_id")): item
            for item in (snapshot.get("intent_objects") or [])
            if item.get("intent_id")
        }
        decisions = []
        traces = []
        for entry in existing_entries:
            primary_id = str((entry.get("primary_intent") or {}).get("intent_id") or entry.get("primary_intent_id") or "")
            decision = {
                "decision_id": entry.get("decision_id"),
                "decision_key": entry.get("decision_key"),
                "beam_id": entry.get("beam_id"),
                "support_id": entry.get("support_id"),
                "support_zone": entry.get("support_zone"),
                "engineering_object_id": entry.get("engineering_object_id"),
                "source_bar_id": entry.get("source_bar_id"),
                "primary_intent": entry.get("primary_intent")
                or {
                    "intent_id": primary_id,
                    "intent_type": entry.get("primary_intent_type"),
                },
                "supporting_intents": entry.get("supporting_intents") or [],
                "suppressed_intents": entry.get("suppressed_intents") or [],
                "conflict_list": entry.get("conflict_list") or [],
                "conflicts": entry.get("conflicts") or [],
                "merges": entry.get("merges") or [],
                "overlaps": entry.get("overlaps") or [],
                "resolution_rule": entry.get("resolution_rule"),
                "decision_category": entry.get("decision_category"),
                "engineering_justification": entry.get("engineering_justification"),
                "evidence": entry.get("evidence") or {},
                "decision_confidence": entry.get("decision_confidence", 100.0),
                "lifecycle": entry.get("lifecycle", "RESOLVED"),
                "production_eligibility": entry.get("production_eligibility", "ELIGIBLE"),
                "graph_id": entry.get("graph_id"),
                "phase": PHASE,
                "model_version": MODEL_VERSION,
                "intent_count": entry.get("intent_count", 0),
                "active_intent_count": entry.get("active_intent_count", 0),
                "suppressed_intent_count": entry.get("suppressed_intent_count", 0),
            }
            decisions.append(decision)
            traces.append(
                {
                    "decision_id": decision.get("decision_id"),
                    "decision_key": decision.get("decision_key"),
                    "lineage": [
                        "Drawing",
                        "Engineering Object",
                        "Recovered Object",
                        "Engineering Intent",
                        "Intent Resolution",
                        "Engineering Decision",
                    ],
                    "source_bar_id": decision.get("source_bar_id"),
                    "engineering_object_id": decision.get("engineering_object_id"),
                    "primary_intent_id": (decision.get("primary_intent") or {}).get("intent_id"),
                    "beam_id": decision.get("beam_id"),
                    "support_id": decision.get("support_id"),
                    "intent_ids": sorted(intents_by_id.keys()),
                }
            )
        return {
            "decisions": decisions,
            "registry_entries": existing_entries,
            "traces": traces,
        }

    @staticmethod
    def _registry_entry(decision: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision_id": decision.get("decision_id"),
            "decision_key": decision.get("decision_key"),
            "beam_id": decision.get("beam_id"),
            "support_id": decision.get("support_id"),
            "support_zone": decision.get("support_zone"),
            "engineering_object_id": decision.get("engineering_object_id"),
            "source_bar_id": decision.get("source_bar_id"),
            "primary_intent": decision.get("primary_intent"),
            "supporting_intents": decision.get("supporting_intents"),
            "suppressed_intents": decision.get("suppressed_intents"),
            "conflict_list": decision.get("conflict_list"),
            "resolution_rule": decision.get("resolution_rule"),
            "decision_category": decision.get("decision_category"),
            "engineering_justification": decision.get("engineering_justification"),
            "evidence": decision.get("evidence"),
            "decision_confidence": decision.get("decision_confidence"),
            "lifecycle": decision.get("lifecycle"),
            "production_eligibility": decision.get("production_eligibility"),
            "graph_id": decision.get("graph_id"),
            "intent_count": decision.get("intent_count"),
            "active_intent_count": decision.get("active_intent_count"),
            "suppressed_intent_count": decision.get("suppressed_intent_count"),
            "decision_status": "SUCCESS",
        }

    @staticmethod
    def _trace(decision: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision_id": decision.get("decision_id"),
            "decision_key": decision.get("decision_key"),
            "lineage": [
                "Drawing",
                "Engineering Object",
                "Recovered Object",
                "Engineering Intent",
                "Intent Resolution",
                "Engineering Decision",
                "Calculation",
                "Steel",
                "BBS",
                "Excel",
                "QA",
                "Production Snapshot",
            ],
            "source_bar_id": decision.get("source_bar_id"),
            "engineering_object_id": decision.get("engineering_object_id"),
            "primary_intent_id": (decision.get("primary_intent") or {}).get("intent_id"),
            "supporting_intent_ids": [
                item.get("intent_id") for item in (decision.get("supporting_intents") or [])
            ],
            "suppressed_intent_ids": [
                item.get("intent_id") for item in (decision.get("suppressed_intents") or [])
            ],
            "beam_id": decision.get("beam_id"),
            "support_id": decision.get("support_id"),
            "support_zone": decision.get("support_zone"),
            "graph_id": decision.get("graph_id"),
            "resolution_rule": decision.get("resolution_rule"),
            "intent_ids": list(context.get("intent_ids") or []),
            "evidence": decision.get("evidence"),
        }

    @staticmethod
    def _confidence(
        primary: dict[str, Any] | None,
        supporting: List[dict[str, Any]],
        suppressed: List[dict[str, Any]],
        conflicts: List[dict[str, Any]],
    ) -> float:
        base = 100.0
        if not primary:
            return 0.0
        if conflicts:
            base -= min(20.0, 5.0 * len(conflicts))
        if suppressed:
            base -= min(10.0, 2.0 * len(suppressed))
        if supporting:
            base = min(100.0, base + min(5.0, 1.0 * len(supporting)))
        return round(max(0.0, min(100.0, base)), 2)

    @staticmethod
    def _justification(
        primary: dict[str, Any] | None,
        supporting: List[dict[str, Any]],
        suppressed: List[dict[str, Any]],
        merges: List[dict[str, Any]],
        conflicts: List[dict[str, Any]],
    ) -> str:
        primary_type = (primary or {}).get("intent_type") or "UNKNOWN"
        parts = [
            f"Primary detailing decision selects {primary_type}.",
        ]
        if merges:
            parts.append(
                "Compatible intents merged into "
                + ", ".join(str(item.get("result_category")) for item in merges)
                + "."
            )
        if supporting:
            types = ", ".join(str(item.get("intent_type")) for item in supporting)
            parts.append(f"Supporting intents retained: {types}.")
        if suppressed:
            types = ", ".join(str(item.get("intent_type")) for item in suppressed)
            parts.append(f"Suppressed intents retained for audit: {types}.")
        if conflicts:
            parts.append(f"Resolved conflicts: {len(conflicts)}.")
        return " ".join(parts)
