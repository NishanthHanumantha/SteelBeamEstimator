"""Core intent resolution pipeline for a collected snapshot."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.engineering_intent_resolution.decision_builder import DecisionBuilder
from src.engineering_intent_resolution.decision_context import DecisionContextBuilder
from src.engineering_intent_resolution.decision_validator import DecisionValidator
from src.engineering_intent_resolution.intent_conflict_detector import IntentConflictDetector
from src.engineering_intent_resolution.intent_graph_builder import IntentGraphBuilder
from src.engineering_intent_resolution.intent_merger import IntentMerger
from src.engineering_intent_resolution.intent_overlap_detector import IntentOverlapDetector
from src.engineering_intent_resolution.intent_priority_engine import IntentPriorityEngine


class IntentResolutionEngine:
    """Resolve overlapping intents into deterministic engineering decisions."""

    def __init__(self, priority_engine: IntentPriorityEngine) -> None:
        self._priority = priority_engine
        self._context_builder = DecisionContextBuilder()
        self._graph_builder = IntentGraphBuilder(priority_engine)
        self._overlap_detector = IntentOverlapDetector()
        self._conflict_detector = IntentConflictDetector(priority_engine)
        self._merger = IntentMerger(priority_engine)
        self._decision_builder = DecisionBuilder(priority_engine)
        self._decision_validator = DecisionValidator()

    def resolve(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        existing_keys = set(snapshot.get("existing_decision_keys") or set())
        existing_entries = list(snapshot.get("existing_decision_entries") or [])

        decision_contexts = self._context_builder.build_groups(snapshot)
        if not decision_contexts and existing_entries:
            rebuilt = self._decision_builder.rebuild_from_registry(existing_entries, snapshot)
            return {
                "decision_contexts": [],
                "graphs": [],
                "overlaps": [],
                "conflicts": [],
                "merges": [],
                "decisions": rebuilt.get("decisions") or [],
                "registry_entries": rebuilt.get("registry_entries") or [],
                "traces": rebuilt.get("traces") or [],
                "decision_validations": self._decision_validator.validate_all(
                    rebuilt.get("decisions") or []
                ),
                "idempotent": True,
            }

        graphs = self._graph_builder.build_all(decision_contexts)
        overlaps_by_group: Dict[str, List[dict[str, Any]]] = {}
        conflicts_by_group: Dict[str, List[dict[str, Any]]] = {}
        merges_by_group: Dict[str, List[dict[str, Any]]] = {}
        suppressed_by_group: Dict[str, Set[str]] = {}

        all_overlaps: List[dict[str, Any]] = []
        all_conflicts: List[dict[str, Any]] = []
        all_merges: List[dict[str, Any]] = []

        for context in decision_contexts:
            group_key = str(context.get("decision_group_key"))
            overlaps = self._overlap_detector.detect(context)
            conflicts = self._conflict_detector.detect(context, overlaps)
            suppressed = IntentConflictDetector.suppressed_ids(
                conflicts,
                list(context.get("intents") or []),
                self._priority,
            )
            merges = self._merger.merge(context, suppressed, conflicts)

            overlaps_by_group[group_key] = overlaps
            conflicts_by_group[group_key] = conflicts
            merges_by_group[group_key] = merges
            suppressed_by_group[group_key] = suppressed
            all_overlaps.extend(overlaps)
            all_conflicts.extend(conflicts)
            all_merges.extend(merges)

        self._decision_builder.set_sequence(int((snapshot.get("id_counters") or {}).get("decision") or 0))
        built = self._decision_builder.build_all(
            decision_contexts,
            graphs,
            overlaps_by_group,
            conflicts_by_group,
            merges_by_group,
            suppressed_by_group,
            existing_keys,
        )

        decisions = list(built.get("decisions") or [])
        registry_entries = list(existing_entries) + list(built.get("registry_entries") or [])
        traces = list(built.get("traces") or [])

        if not decisions and existing_entries:
            rebuilt = self._decision_builder.rebuild_from_registry(existing_entries, snapshot)
            decisions = rebuilt.get("decisions") or []
            registry_entries = rebuilt.get("registry_entries") or []
            traces = rebuilt.get("traces") or []
            # Rebuild graphs/conflicts/merges from current intents for idempotent exports.
            if decision_contexts:
                pass
            else:
                graphs = []
                all_overlaps = []
                all_conflicts = []
                all_merges = []

        decision_validations = self._decision_validator.validate_all(decisions)
        return {
            "decision_contexts": decision_contexts,
            "graphs": graphs,
            "overlaps": sorted(all_overlaps, key=lambda item: str(item.get("overlap_type")) + str(item.get("decision_group_key"))),
            "conflicts": sorted(all_conflicts, key=lambda item: str(item.get("conflict_id"))),
            "merges": sorted(all_merges, key=lambda item: str(item.get("merge_id"))),
            "decisions": decisions,
            "registry_entries": registry_entries,
            "traces": traces,
            "decision_validations": decision_validations,
            "idempotent": bool(existing_entries) and not built.get("decisions"),
        }
